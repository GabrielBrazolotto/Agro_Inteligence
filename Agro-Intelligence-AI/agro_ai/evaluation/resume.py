"""Retomada estritamente limitada a dois casos, com reuso validado e ledger real."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
from types import SimpleNamespace

from agro_ai.config import ROOT
from agro_ai.assistant import select_commercial_context
from agro_ai.database import commercial_snapshot
from agro_ai.chatflow import ChatTurn
from agro_ai.gemini import GeminiGateway
from agro_ai.rag import DocumentIndex,split_text
from agro_ai.evaluation.judge import GeminiJudge,Judgment,score_judgment
from agro_ai.evaluation.reference import check_finances
from agro_ai.evaluation.runner import Limiter,execute_case,failure,absent_metrics,write_report


def usage(response):
    metadata=getattr(response,'usage_metadata',None)
    return {name:value for name,attribute in {'input':'prompt_token_count','output':'candidates_token_count',
        'total':'total_token_count','reasoning':'thoughts_token_count'}.items()
        if type(value:=getattr(metadata,attribute,None)) is int and value>=0}


class Ledger:
    def __init__(self,limiter):
        self.limiter=limiter
        self.records=[]
        self.case_id=None

    def start(self,model,kind):
        self.limiter.wait()
        record={'case_id':self.case_id,'model':model,'kind':kind,'status':'started','usage':None}
        self.records.append(record)
        return record,time.perf_counter()

    def wrap(self,function,model,kind,stream=False):
        if stream:
            def streamed(*args,**kwargs):
                record,started=self.start(model,kind)
                try:
                    for chunk in function(*args,**kwargs):
                        tokens=usage(chunk)
                        if tokens:
                            record['usage']=tokens  # Snapshot cumulativo, não somar chunks.
                        yield chunk
                    record['status']='success'
                except Exception as error:
                    record.update(status='failed',failure=failure(error))
                    raise
                finally:
                    record['latency_ms']=round((time.perf_counter()-started)*1000,3)
            return streamed
        def call(*args,**kwargs):
            record,started=self.start(model,kind)
            try:
                result=function(*args,**kwargs)
                record.update(status='success',usage=usage(result) or None)
                if kind=='judge':
                    # Saída do juiz sobre dados sintéticos, para auditar parsing sem nova chamada.
                    try:
                        record['raw_judgment']=json.loads(result.text)
                    except (ValueError,TypeError,AttributeError):
                        record['judgment_json_valid']=False
                return result
            except Exception as error:
                record.update(status='failed',failure=failure(error))
                raise
            finally:
                record['latency_ms']=round((time.perf_counter()-started)*1000,3)
        return call


def reusable_answer(source,case,settings):
    """Não gerar contextos substitutos: conferir os snapshots originais e preservá-los."""
    rows=json.loads(Path(source).read_text(encoding='utf-8')).get('results',[])
    row=next((r for r in rows if r.get('id')==case['id'] and r.get('question')==case['question']),None)
    if not row or row.get('generation_status') not in ('ok','degraded','fallback') or not row.get('answer') or not row.get('evidence'):
        return None
    if case['category']!='faturamento':
        return None  # Outros tipos precisam de validação específica antes de habilitar cache.
    snapshot=select_commercial_context(commercial_snapshot(settings.database),case['question'])
    canonical=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False,default=str)
    indicators=[e['content'] for e in row['evidence'] if e.get('origin')=='comercial.indicadores']
    if len(indicators)!=1 or canonical(indicators[0])!=canonical(snapshot):
        return None
    for evidence in row['evidence']:
        if evidence.get('origin')=='comercial.documentos':
            for doc in evidence['content']:
                name=doc['source']
                if Path(name).name!=name:
                    return None
                path=settings.documents/name
                if not path.is_file():
                    return None
                chunks=split_text(path.read_text(encoding='utf-8'))
                index=doc['chunk']-1
                if index<0 or index>=len(chunks) or chunks[index]!=doc['text']:
                    return None
    checks=check_finances(settings.database,case['checks'],row['answer'])
    if any(check['status']!='passed' for check in checks):
        return None
    result=deepcopy(row)
    result.update(original_generation_status=row['generation_status'],generation_status='reused',
        reused_from=str(source),historical_api_failures=row.get('api_failures',[]),api_failures=[],
        historical_generation_latency_ms=row.get('generation_latency_ms'),generation_latency_ms=None,
        deterministic=checks,metrics=absent_metrics('judge_pending'),tools_executed_current=[])
    result.pop('evaluation_failure',None)
    result.pop('generation_failure',None)
    return result


def run_two(settings,source,case_ids=('G01','G02'),interval=15,max_calls=6,output=None):
    if len(case_ids)!=2 or len(set(case_ids))!=2:
        raise ValueError('Selecionar exatamente dois casos distintos.')
    golden=json.loads((ROOT/'data/evaluation/golden.json').read_text(encoding='utf-8'))
    cases=[next(case for case in golden if case['id']==identifier) for identifier in case_ids]
    limiter=Limiter(max(interval,settings.request_interval_seconds),max_calls)
    ledger=Ledger(limiter)
    class Gateway(GeminiGateway):
        def __init__(self,settings):
            super().__init__(settings)
            client=self.client
            self.client=SimpleNamespace(close=client.close,models=SimpleNamespace(
                generate_content_stream=ledger.wrap(client.models.generate_content_stream,settings.model,'generation',True),
                embed_content=ledger.wrap(client.models.embed_content,settings.embedding_model,'embedding')))
    judge=GeminiJudge(settings,SimpleNamespace(wait=lambda:None))
    client=judge.client
    judge.client=SimpleNamespace(close=client.close,models=SimpleNamespace(
        generate_content=ledger.wrap(client.models.generate_content,judge.model,'judge')))
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-two-cases'
    path=Path(output or ROOT/'reports/evaluation'/run_id)
    report={'run_id':run_id,'mode':'live','selected_cases':list(case_ids),'maximum_cases':2,
        'golden_sha256':hashlib.sha256((ROOT/'data/evaluation/golden.json').read_bytes()).hexdigest(),
        'case_definitions':cases,'source_report':str(source),'concurrency':1,
        'source_report_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        'min_interval_seconds':limiter.interval,'max_calls':max_calls,
        'generator_model':settings.model,'agent_model':settings.agent_model or settings.model,
        'judge_model':judge.model,'metric_implementation':'claim_verdict_judge_v1','results':[],'calls':ledger.records}
    stopped=None
    try:
        for case in cases:
            ledger.case_id=case['id']
            started=time.perf_counter()
            if stopped:
                row={'id':case['id'],'question':case['question'],'generation_status':'not_executed',
                     'skip_reason':stopped,'metrics':absent_metrics(stopped)}
            else:
                row=reusable_answer(source,case,settings)
                if row:
                    try:
                        row['metrics']=judge.evaluate(case['question'],row['answer'],row['evidence'])
                    except Exception as error:
                        row['evaluation_failure']=failure(error)
                        row['metrics']=absent_metrics(row['evaluation_failure']['status'])
                    row['evaluation_latency_ms']=round((time.perf_counter()-started)*1000,3)
                    row['total_latency_ms']=row['evaluation_latency_ms']
                else:
                    row=execute_case(case,settings,judge,lambda:ChatTurn(settings,Gateway,DocumentIndex))
                    row['tools_executed_current']=row.get('tools',[])
                failed_api=bool(row.get('api_failures')) or any(
                    row.get(key,{}).get('status') in ('api_error','call_budget_exhausted') for key in ('generation_failure','evaluation_failure'))
                if failed_api:
                    stopped='api_failure_or_limit'
                elif row.get('generation_failure'):
                    stopped='generation_error'
            report['results'].append(row)
            report.update(actual_api_calls=len(ledger.records),scheduled_calls=limiter.calls,
                reused_answers=sum(r['generation_status']=='reused' for r in report['results']),
                new_generation_cases=sum(r['generation_status'] not in ('reused','not_executed') for r in report['results']))
            write_report(path,report)
            print(json.dumps({'case':case['id'],'generation':row['generation_status'],
                'faithfulness':row['metrics']['faithfulness'],'answer_relevancy':row['metrics']['answer_relevancy'],
                'actual_api_calls':len(ledger.records),'stop_reason':stopped},ensure_ascii=False),flush=True)
    finally:
        judge.close()
    return path,report


def replay_saved_judgments(path,output=None):
    """Revalidar vereditos recebidos, sem refazer respostas ou contatar o juiz."""
    path=Path(path)
    source=path
    path=Path(output or source.parent/(source.name+'-revalidated-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    if path.exists():
        raise ValueError('report_directory_already_exists')
    report=json.loads((source/'results.json').read_text(encoding='utf-8'))
    report['parent_report']=str(source/'results.json')
    report['derived_report_directory']=str(path)
    for row in report['results']:
        records=[record for record in report['calls'] if record['case_id']==row['id'] and
                 record['kind']=='judge' and 'raw_judgment' in record]
        if not records or not row.get('answer'):
            continue
        record=records[-1]
        started=time.perf_counter()
        try:
            metrics=score_judgment(Judgment.model_validate(record['raw_judgment']),row['answer'],row['evidence'])
        except Exception as error:
            row['evaluation_failure']=failure(error)
            continue
        metrics.update(usage=record['usage'],cost=None,judge_model=record['model'])
        row['metrics']=metrics
        if row.get('evaluation_failure'):
            row['original_validation_failure']=row.pop('evaluation_failure')
        row['evaluation_revalidated_offline']=True
        row['offline_validation_ms']=round((time.perf_counter()-started)*1000,3)
    write_report(path,report)
    return report
