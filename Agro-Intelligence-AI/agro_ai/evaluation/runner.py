"""Execução serial, limites de chamadas, checkpoint e relatórios auditáveis."""
import hashlib
import json
import time
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from google.genai.errors import APIError
import httpx

from agro_ai.config import ROOT
from agro_ai.chatflow import ChatTurn
from agro_ai.gemini import GeminiGateway
from agro_ai.rag import DocumentIndex
from agro_ai.observability import chat_request,complete_chat,error_metadata
from agro_ai.evaluation.reference import check_finances
from agro_ai.evaluation.judge import GeminiJudge


class CallLimit(Exception):
    pass


class Limiter:
    def __init__(self,interval=15,max_calls=80):
        self.interval=interval
        self.max_calls=max_calls
        self.calls=0
        self.last=None

    def wait(self):
        if self.calls>=self.max_calls:
            raise CallLimit()
        if self.last is not None:
            delay=self.interval-(time.monotonic()-self.last)
            if delay>0:
                time.sleep(delay)
        self.last=time.monotonic()
        self.calls+=1


def evidence_from_turn(turn):
    # Nunca inclui golden, SQL-oráculo, análises Gemini ou documentos não recuperados.
    evidence=[]
    for agent,content in turn.evidence.items():
        items=content.items() if isinstance(content,dict) and agent!='ml' else [('inference',content)]
        for tool,value in items:
            if isinstance(value,dict) and value.get('unavailable'):
                continue
            evidence.append({'id':f'e{len(evidence)+1}','origin':agent+'.'+tool,
                             'content':json.loads(json.dumps(value,ensure_ascii=False,default=str))})
    return evidence


def failure(error):
    info=error_metadata(error)
    result={'status':'api_error' if isinstance(error,(APIError,httpx.TransportError)) or
            info.get('error_category') in ('api','timeout','connection','daily_limit','cooldown') else
            'call_budget_exhausted' if isinstance(error,CallLimit) else 'evaluation_error',**info}
    if isinstance(error,APIError) and error.code==400:
        import re
        message=error.message if isinstance(error.message,str) else ''
        allowed={'additionalproperties','maxitems','minitems','responsejsonschema','responseschema','$defs','$ref','title'}
        fields=re.findall(r'Unknown name [\"\']([^\"\']+)',message,re.I)
        result['unknown_schema_fields']=[field for field in fields if field.replace('_','').lower() in allowed]
        result['schema_rejected']='schema' in message.lower() and 'unknown name' in message.lower()
    if isinstance(error,ValueError) and error.args and error.args[0] in ('invalid_quote','invalid_evidence_reference'):
        result['reason']=error.args[0]
    return result


def absent_metrics(reason):
    return {name:{'status':'not_executed','score':None,'reason':reason}
            for name in ('faithfulness','answer_relevancy')}


def execute_case(case,settings,judge,turn_factory):
    started=time.perf_counter()
    row={'id':case['id'],'category':case['category'],'question':case['question'],
         'expected_behavior':case['expected_behavior'],'expected_tools':case['expected_tools'],'references':case['references'],
         'generation_status':'not_executed','answer':None,'evidence':[],
         'metrics':absent_metrics('no_answer'),'api_failures':[],'deterministic':[]}
    turn=turn_factory()
    try:
        history=[{'role':'user','content':case['question']}]
        with chat_request(case['question'],[]) as root:
            turn.prepare(history)
            answer=''.join(turn.stream())
            row['generation_status']=complete_chat(answer,turn.tools,turn.answer_mode)
            row['answer']=answer
            row['trace_id']=root.trace_id
        row['tools']=turn.tools
        row['evidence']=evidence_from_turn(turn)
        row['api_failures']=[{'stage':item['tool'],'http_code':item.get('http'),'category':item.get('category')}
            for item in turn.tools if item.get('status')=='failed' and item.get('category') in ('api','timeout','connection','daily_limit','cooldown')]
        row['generation_latency_ms']=round((time.perf_counter()-started)*1000,3)
        row['deterministic']=check_finances(settings.database,case['checks'],answer)
        used={item['tool'] for item in turn.tools if item['status'] in ('ok','consultado','needs_input')}
        row['expected_tools_missing']=sorted(set(case['expected_tools'])-used)
        if any(item.get('http_code')==429 for item in row['api_failures']):
            row['metrics']=absent_metrics('generation_rate_limit')
        else:
            judging=time.perf_counter()
            try:
                row['metrics']=judge.evaluate(case['question'],answer,row['evidence'])
            except Exception as error:
                row['evaluation_failure']=failure(error)
                row['metrics']=absent_metrics(row['evaluation_failure']['status'])
            row['evaluation_latency_ms']=round((time.perf_counter()-judging)*1000,3)
    except Exception as error:
        row['generation_status']='failed'
        row['generation_failure']=failure(error)
        row['answer']=None  # Não avaliar resposta parcial que o Streamlit descartaria.
        row['tools']=turn.tools
    finally:
        try:
            turn.close()
        except Exception:
            pass
    row['total_latency_ms']=round((time.perf_counter()-started)*1000,3)
    return row


def summarize(rows):
    summary={'attempted_questions':sum(r['generation_status']!='not_executed' for r in rows),
             'answers_received':sum(r.get('answer') is not None for r in rows),
             'questions_evaluated':sum(r['metrics']['answer_relevancy']['status']=='evaluated' for r in rows),
             'api_failed_questions':sum(bool(r.get('api_failures')) or
                 any(r.get(k,{}).get('status')=='api_error' for k in ('generation_failure','evaluation_failure')) for r in rows),
             'cost':None}
    counts=[sum(r['metrics'][name]['status']=='evaluated' for name in ('faithfulness','answer_relevancy')) for r in rows]
    resolved=[sum(r['metrics'][name]['status'] in ('evaluated','not_applicable') for name in ('faithfulness','answer_relevancy')) for r in rows]
    summary.update(questions_with_any_metric=sum(c>0 for c in counts),
                   questions_fully_evaluated=sum(c==2 for c in resolved),
                   questions_partially_evaluated=sum(c==1 for c in resolved))
    for name in ('faithfulness','answer_relevancy'):
        scores=[r['metrics'][name]['score'] for r in rows if r['metrics'][name]['status']=='evaluated']
        summary[name]={'evaluated':len(scores),'mean':sum(scores)/len(scores) if scores else None,
                       'below_threshold':sum(s<.8 for s in scores),'threshold':.8}
    summary['deterministic']={s:sum(c['status']==s for r in rows for c in r.get('deterministic',[])) for s in ('passed','failed')}
    return summary


def write_report(path,report):
    path=Path(path)
    path.mkdir(parents=True,exist_ok=True)
    report['summary']=summarize(report['results'])
    summary=report['summary']
    report['analysis']={
        'quality_conclusion':'insufficient_judged_answers' if not summary['questions_evaluated'] else 'review_verdicts_and_deterministic_checks',
        'operational_failures_separate_from_quality':True,
        'financial_checks':summary['deterministic'],
        'improvements':[
            'Verificar limites Gemini antes de repetir casos com 429; manter concorrência 1 e intervalo de pelo menos 15s.',
            'Revisar manualmente afirmações e vereditos e calibrar o limiar 0,8 com exemplos humanos.',
            'Conferir roteamento e associação de valores a regiões/meses se o oráculo financeiro falhar.',
            'Avaliar esclarecimento/recusa para casos ambíguos e fora de escopo antes de alterar o roteador.',
            'Considerar juiz independente do gerador para reduzir viés correlacionado.',
        ]}
    (path/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['# Avaliação automática — Etapa 2','',f"Execução: {report['run_id']}",
           '',json.dumps(report['summary'],ensure_ascii=False,indent=2),'',
           '| Caso | Geração | Faithfulness | Answer Relevancy | SQL |',
           '|---|---|---|---|---|']
    for row in report['results']:
        def metric(name):
            m=row['metrics'][name]
            return f"{m['score']:.3f}" if m['score'] is not None else m['status']
        lines.append(f"| {row['id']} | {row['generation_status']} | {metric('faithfulness')} | {metric('answer_relevancy')} | "+
                     ', '.join(c['check']+':'+c['status'] for c in row.get('deterministic',[]))+' |')
    lines+=['','## Análise e melhorias','',
      f"- Perguntas com falha de API: {report['summary']['api_failed_questions']}; respostas recebidas: {report['summary']['answers_received']}; perguntas avaliadas pelo juiz: {report['summary']['questions_evaluated']}.",
      '- Falhas de API e avaliações não executadas não recebem zero nem entram na média.',
      '- Conferir evidências e vereditos por caso no JSON; scores abaixo de 0,8 indicam revisão, não diagnóstico absoluto.',
      '- Se houver 429, interromper a bateria e retomar após verificar limites; não ampliar concorrência.',
      '- Valores SQL ausentes/incorretos exigem revisar formatação, roteamento e agregações; juiz LLM não substitui o oráculo.',
      '- Casos ambíguos/fora do escopo podem revelar consultas desnecessárias: avaliar roteador de esclarecimento/recusa.',
      '- Juiz e gerador compartilham família de modelo: validar amostra humana e considerar juiz independente.',
      '- Não há estimativa de custo nem promessa de desempenho de ML com esta bateria sintética.','',
      '## Evidências por caso','']
    for row in report['results']:
        lines += [f"### {row['id']}",'',row['question'],'',
            f"Latência total: {row.get('total_latency_ms')} ms; falhas: "+json.dumps(row.get('api_failures',[]),ensure_ascii=False),
            '', 'Resposta:', '', row.get('answer') or '(não recebida)', '',
            'Avaliação: '+json.dumps(row['metrics'],ensure_ascii=False), '',
            'Falhas operacionais: '+json.dumps({k:row.get(k) for k in ('generation_failure','evaluation_failure','skip_reason')},ensure_ascii=False),'',
            'Comportamento esperado: '+row.get('expected_behavior','')+'; referências: '+json.dumps(row.get('references',[]),ensure_ascii=False),'',
            'Verificações independentes: '+json.dumps(row.get('deterministic',[]),ensure_ascii=False,default=str),'',
            'Ferramentas: '+json.dumps(row.get('tools',[]),ensure_ascii=False), '',
            'Evidências efetivamente recuperadas:', '', '```json',
            json.dumps(row.get('evidence',[]),ensure_ascii=False,indent=2,default=str),'```','']
    (path/'results.md').write_text('\n'.join(lines),encoding='utf-8')


def run(settings,live=False,interval=15,max_calls=80,max_cases=18,output=None):
    cases=json.loads((ROOT/'data/evaluation/golden.json').read_text(encoding='utf-8'))[:max_cases]
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path=output or ROOT/'reports/evaluation'/run_id
    report={'run_id':run_id,'mode':'live' if live else 'not_executed',
            'golden_sha256':hashlib.sha256((ROOT/'data/evaluation/golden.json').read_bytes()).hexdigest(),
            'concurrency':1,'min_interval_seconds':interval,'max_calls':max_calls,
            'generator_model':settings.model,'agent_model':settings.agent_model or settings.model,
            'judge_model':settings.judge_model or settings.agent_model or settings.model,
            'metric_implementation':'claim_verdict_judge_v1','case_definitions':cases,'results':[]}
    limiter=Limiter(interval,max_calls)
    class Gateway(GeminiGateway):
        def __init__(self,settings):
            super().__init__(settings)
            client=self.client
            def limited(function):
                def call(*args,**kwargs):
                    limiter.wait()
                    return function(*args,**kwargs)
                return call
            # Contabilizar cada tentativa real, inclusive o retry 503 do adaptador.
            self.client=SimpleNamespace(close=client.close,models=SimpleNamespace(
                generate_content_stream=limited(client.models.generate_content_stream),
                embed_content=limited(client.models.embed_content)))
    judge=GeminiJudge(settings,limiter) if live and settings.api_key else None
    stopped=None if judge else 'live_opt_in_or_key_missing'
    try:
        for index,case in enumerate(cases):
            if stopped:
                row={'id':case['id'],'category':case['category'],'question':case['question'],
                     'expected_behavior':case['expected_behavior'],'expected_tools':case['expected_tools'],'references':case['references'],
                     'generation_status':'not_executed','skip_reason':stopped,'metrics':absent_metrics(stopped)}
            else:
                row=execute_case(case,settings,judge,lambda:ChatTurn(settings,Gateway,DocumentIndex))
                rate_limited=any(e.get('http_code')==429 for e in row.get('api_failures',[])) or any(
                    row.get(k,{}).get('http_code')==429 for k in ('generation_failure','evaluation_failure'))
                if rate_limited:
                    stopped='rate_limit_circuit_open'
                elif row.get('generation_failure') or row.get('evaluation_failure'):
                    stopped='api_or_evaluation_failure'
                elif index<2 and (any(row['metrics'][m]['status']!='evaluated' for m in ('faithfulness','answer_relevancy')) or row.get('api_failures')):
                    stopped='sample_not_successful'
            report['results'].append(row)
            report['scheduled_calls']=limiter.calls
            write_report(path,report)
            print(json.dumps({'case':case['id'],'generation':row['generation_status'],
                'metrics':{name:row['metrics'][name] for name in ('faithfulness','answer_relevancy')},
                'stop_reason':stopped},ensure_ascii=False),flush=True)
    finally:
        if judge:
            judge.close()
    return path,report
