"""Planejamento sem rede e execução opt-in de no máximo três casos por comando."""
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import time

from agro_ai.config import ROOT
from agro_ai.chatflow import ChatTurn
from agro_ai.gemini import GeminiGateway
from agro_ai.rag import DocumentIndex
from agro_ai.observability import chat_request,complete_chat
from agro_ai.evaluation.cache import EvaluationCache,METRICS,reference_state,valid_metric
from agro_ai.evaluation.resume import Ledger
from agro_ai.evaluation.judge import GeminiJudge
from agro_ai.evaluation.runner import Limiter,failure,absent_metrics,evidence_from_turn,write_report
from agro_ai.evaluation.reference import check_finances
from agro_ai.evaluation.completeness import response_completeness

BASELINE={'G01','G12'}


def golden():
    return json.loads((ROOT/'data/evaluation/golden.json').read_text(encoding='utf-8'))


def consolidate(cache,cases,state):
    rows=[]
    for case in cases:
        response=cache.response(case,state)
        rejected=cache.rejected_responses(case,state)
        metrics={name:(cache.metric(response,name)['metric'] if response and cache.metric(response,name)
                       else {'status':'not_executed','score':None}) for name in METRICS}
        completed=sum(valid_metric(metric) for metric in metrics.values())
        event=cache.latest_event(case['id'])
        if event and response and event.get('response_key')==response['key']:
            for name in METRICS:
                old=event.get('metrics',{}).get(name,{})
                if not cache.metric(response,name) and old.get('status') in ('invalid_judgment','not_executed'):
                    metrics[name]={**deepcopy(old),'score':None}
        infra=bool(event and (event.get('api_failures') or any(event.get(k,{}).get('status') in ('api_error','call_budget_exhausted')
                   for k in ('generation_failure','evaluation_failure'))))
        status=('evaluated' if completed==2 else 'partially_evaluated' if completed else
                'response_available' if response else 'infrastructure_failure' if infra else
                'response_incomplete' if rejected else
                'validation_failure' if event and event.get('generation_failure') else 'not_executed')
        rows.append({'id':case['id'],'status':status,'executed':bool(response or rejected or event and event.get('generation_attempted')),
                     'rejected_cached_responses':rejected,
                     'infrastructure_failure':infra,'metrics':metrics,'response_key':response['key'] if response else None,
                     'metric_origins':{name:cache.metric(response,name)['origin'] for name in METRICS
                                       if response and cache.metric(response,name)}})
    return {'cases':rows,'summary':{'total_cases':len(cases),
        **{status:sum(row['status']==status for row in rows) for status in
           ('evaluated','partially_evaluated','response_available','response_incomplete','infrastructure_failure','validation_failure','not_executed')},
        'executed':sum(row['executed'] for row in rows),
        'infrastructure_failure_without_response':sum(row['status']=='infrastructure_failure' for row in rows),
        'infrastructure_failure':sum(row['infrastructure_failure'] for row in rows),
        'cases_with_infrastructure_failure':sum(row['infrastructure_failure'] for row in rows)}}


def batches(ids,size):
    if size not in (2,3):
        raise ValueError('batch_size_must_be_2_or_3')
    result=[]
    while ids:
        count=2 if size==3 and len(ids)==4 else min(size,len(ids))
        result.append(ids[:count]);ids=ids[count:]
    return result


def plan(cache,cases,state,size=2):
    status=consolidate(cache,cases,state)
    remaining=[row['id'] for row in status['cases'] if row['id'] not in BASELINE and row['status']!='evaluated']
    return {'consolidated':status,'baseline_pending':[row['id'] for row in status['cases'] if row['id'] in BASELINE and row['status']!='evaluated'],
            'remaining_case_ids':remaining,'batches':batches(remaining,size),'automatic_execution':False}


def execute_batch(settings,cache,case_ids,judge_only=False,interval=15,max_calls=12,output=None,
                  phase='all',ledger_factory=None):
    if phase not in ('all','generate','judge'):
        raise ValueError('invalid_phase')
    judge_only=judge_only or phase=='judge'
    if not 1<=len(case_ids)<=3 or len(set(case_ids))!=len(case_ids):
        raise ValueError('select_1_to_3_distinct_cases')
    cases=golden()
    selected=[next(case for case in cases if case['id']==identifier) for identifier in case_ids]
    state=reference_state(settings)
    limiter=Limiter(max(interval,settings.request_interval_seconds),max_calls)
    ledger=ledger_factory(limiter) if ledger_factory else Ledger(limiter)
    judge=None
    def get_judge():
        nonlocal judge
        if judge is None:
            judge=GeminiJudge(settings,SimpleNamespace(wait=lambda:None))
            client=judge.client
            judge.client=SimpleNamespace(close=client.close,models=SimpleNamespace(
                generate_content=ledger.wrap(client.models.generate_content,judge.model,'judge')))
        return judge
    class Gateway(GeminiGateway):
        def __init__(self,settings):
            super().__init__(settings)
            client=self.client
            self.client=SimpleNamespace(close=client.close,models=SimpleNamespace(
                generate_content_stream=ledger.wrap(client.models.generate_content_stream,settings.model,'generation',True),
                embed_content=ledger.wrap(client.models.embed_content,settings.embedding_model,'embedding')))
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-batch-'+uuid4().hex[:6]
    path=Path(output or ROOT/'reports/evaluation'/run_id)
    if path.exists():
        raise ValueError('report_directory_already_exists')
    report={'run_id':run_id,'selected_cases':case_ids,'mode':'live','concurrency':1,'case_definitions':selected,
            'phase':phase,
            'reference_state':state,'max_calls':max_calls,'calls':ledger.records,'results':[],
            'generator_model':settings.model,'agent_model':settings.agent_model,'judge_model':settings.judge_model,
            'min_interval_seconds':limiter.interval,'historical_results_modified':False}
    stopped=None
    try:
        for case in selected:
            ledger.case_id=case['id']
            started=time.perf_counter()
            row={**case,'generation_status':'not_executed','answer':None,'evidence':[],
                 'tools':[],'api_failures':[],'metrics':absent_metrics('pending'),'generation_attempted':False,'reference_state':state}
            if stopped:
                row.update(skip_reason=stopped,metrics=absent_metrics(stopped))
            else:
                row['rejected_cached_responses']=cache.rejected_responses(case,state)
                response=cache.response(case,state)
                if response:
                    row.update(answer=response['answer'],evidence=response['evidence'],tools=response['tools'],
                               generation_status='reused',response_key=response['key'],response_origin=response['origin'],
                               historical_api_failures=response['historical_api_failures'])
                elif judge_only:
                    row.update(skip_reason='validated_response_missing',metrics=absent_metrics('validated_response_missing'))
                    stopped='validated_response_missing'
                else:
                    turn=ChatTurn(settings,Gateway,DocumentIndex)
                    row['generation_attempted']=True
                    try:
                        with chat_request(case['question'],[]) as root:
                            history=[{'role':'user','content':case['question']}]
                            turn.prepare(history)
                            answer=''.join(turn.stream())
                            row.update(answer=answer,evidence=evidence_from_turn(turn),tools=turn.tools,
                                generation_status=complete_chat(answer,turn.tools,turn.answer_mode),trace_id=root.trace_id)
                        row['api_failures']=[{'stage':item['tool'],'category':item.get('category'),'http_code':item.get('http')}
                            for item in turn.tools if item['status']=='failed' and item.get('category') in ('api','timeout','connection','daily_limit','cooldown')]
                        if reference_state(settings)!=state:
                            raise ValueError('reference_state_changed_during_generation')
                        response=cache.put_response(case,row,state,{'report':str(path/'results.json'),'fresh_generation':True})
                        row['response_key']=response['key']
                    except Exception as error:
                        row.update(generation_status='failed',answer=None,generation_failure=failure(error),tools=turn.tools)
                        stopped='generation_failure'
                    finally:
                        turn.close()
                    if row['api_failures']:
                        stopped='api_failure_or_limit'
                row['generation_latency_ms']=round((time.perf_counter()-started)*1000,3) if row['generation_attempted'] else None
                if response and row.get('answer') is not None:
                    row['deterministic']=check_finances(settings.database,case['checks'],row['answer'])
                    row['completeness']=response_completeness(case,row['answer'],row['evidence'])
                    row['metrics']={name:(deepcopy(cache.metric(response,name)['metric']) if cache.metric(response,name)
                                         else absent_metrics('pending')[name]) for name in METRICS}
                    row['reused_metrics']=[name for name in METRICS if cache.metric(response,name)]
                    pending=[name for name in METRICS if not cache.metric(response,name)]
                    row['requested_metrics']=pending
                    if row['completeness']['status']=='failed':
                        row['validation_failure']={'reason':'incomplete_response','details':row['completeness']}
                        row['metrics']=absent_metrics('incomplete_response')
                        row['requested_metrics']=[]
                        stopped='incomplete_response'
                    if pending and not stopped and phase!='generate':
                        evaluation_started=time.perf_counter()
                        try:
                            assessment=get_judge().evaluate_pending(case['question'],row['answer'],row['evidence'],pending)
                            row['current_assessment']=assessment
                            for name in pending:
                                row['metrics'][name]=assessment[name]
                                cache.put_metric(response,name,assessment,{'report':str(path/'results.json')},assessment['protocols'][name])
                        except Exception as error:
                            row['evaluation_failure']=failure(error)
                            for name in pending:
                                row['metrics'][name]={'status':'not_executed','score':None,'reason':row['evaluation_failure']['status']}
                            stopped='evaluation_failure'
                        row['evaluation_latency_ms']=round((time.perf_counter()-evaluation_started)*1000,3)
                    row['metric_origins']={name:cache.metric(response,name)['origin'] for name in METRICS if cache.metric(response,name)}
            row['total_latency_ms']=round((time.perf_counter()-started)*1000,3)
            cache.event(run_id,case['id'],row)
            report['results'].append(row)
            report.update(actual_api_calls=len(ledger.records),stop_reason=stopped)
            write_report(path,report)
            print(json.dumps({'case':case['id'],'requested_metrics':row.get('requested_metrics',[]),
                'metrics':row['metrics'],'actual_api_calls':len(ledger.records),'stop_reason':stopped},ensure_ascii=False),flush=True)
    finally:
        if judge:
            judge.close()
    consolidation=consolidate(cache,cases,state)
    (path/'consolidated.json').write_text(json.dumps(consolidation,ensure_ascii=False,indent=2),encoding='utf-8')
    return path,report
