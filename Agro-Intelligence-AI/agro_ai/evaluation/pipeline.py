"""Two-phase, cache-driven evaluation queue. Live execution requires explicit opt-in."""
from datetime import datetime,timezone
import json
from pathlib import Path
import time
from uuid import uuid4

from agro_ai.config import ROOT
from agro_ai.agents.orchestrator import plan_agents
from agro_ai.ml.inference import is_prediction_request
from agro_ai.evaluation.batches import golden,consolidate,execute_batch
from agro_ai.evaluation.cache import METRICS,reference_state
from agro_ai.evaluation.runner import Limiter
from agro_ai.evaluation.budget import ModelBudget,BudgetLedger,atomic_json,budget_path,exclusive_run


def model_roles(settings):
    return {'main':settings.model,'agent':settings.agent_model or settings.model,
            'judge':settings.judge_model or settings.agent_model or settings.model,
            'embedding':settings.embedding_model}


def policies_for(settings,rpm=4,tpm=100000,rpd=20,overrides=None):
    policies={model:{'rpm':rpm,'tpm':tpm,'rpd':rpd} for model in model_roles(settings).values()}
    if overrides is not None:
        if not isinstance(overrides,dict):
            raise ValueError('quota_overrides_must_be_object')
        if set(overrides)-set(policies):
            raise ValueError('quota_override_model_not_configured')
        for model,values in overrides.items():
            if not isinstance(values,dict):
                raise ValueError('quota_model_policy_must_be_object')
            if set(values)-{'rpm','tpm','rpd'}:
                raise ValueError('invalid_quota_fields')
            policies[model].update(values)
    if any(type(v) is not int or v<1 for row in policies.values() for v in row.values()):
        raise ValueError('quota_limits_must_be_positive_integers')
    return policies


def queue_plan(settings,cache,policies,reserve=5,phase='all',budget_dir=None,
               total_daily_limit=None,total_reserve=0,case_ids=None):
    if phase not in ('all','generate','judge'):
        raise ValueError('invalid_phase')
    state=reference_state(settings);cases=golden();roles=model_roles(settings)
    if case_ids is not None and (not case_ids or len(set(case_ids))!=len(case_ids)
            or set(case_ids)-{case['id'] for case in cases}):
        raise ValueError('invalid_case_selection')
    status=consolidate(cache,cases,state)
    pending=[];by_model={model:0 for model in policies};skipped=[]
    for case,row in zip(cases,status['cases']):
        if case_ids is not None and case['id'] not in case_ids:
            continue
        response=cache.response(case,state)
        missing=[name for name in METRICS if not response or not cache.metric(response,name)]
        if not missing:
            continue
        estimate={model:0 for model in policies}
        generation=response is None
        if phase=='judge' and generation:
            skipped.append({'id':case['id'],'reason':'stored_response_missing'});continue
        if phase=='generate' and not generation:
            skipped.append({'id':case['id'],'reason':'stored_response_reused'});continue
        if generation:
            agents=plan_agents(case['question'])
            local=is_prediction_request(case['question']) and agents!=['estoque','comercial']
            if not local:
                estimate[roles['main']]+=1
                estimate[roles['agent']]+=len(agents)
                if 'comercial' in agents:
                    estimate[roles['embedding']]+=1
        if phase!='generate':
            estimate[roles['judge']]+=1  # Both missing metrics are requested in one judgment.
        for model,count in estimate.items():
            by_model[model]+=count
        pending.append({'id':case['id'],'needs_generation':generation,'pending_metrics':missing,
            'stored_response_key':response['key'] if response else None,
            'stored_response_status':response.get('original_generation_status') if response else None,
            'historical_tool_failures':[t for t in response.get('tools',[]) if t['status']=='failed'] if response else [],
            'incomplete_response_rejected':bool(row['rejected_cached_responses']),
            'estimated_calls_by_model':estimate,'estimated_calls':sum(estimate.values())})
    directory=Path(budget_dir or ROOT/'data/runtime/evaluation_pipeline')
    path=budget_path(directory,settings)
    recorded=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'models':{}}
    now=time.time();remaining={}
    total_used=sum(e.get('daily_requests',0) for e in recorded['models'].values() if e.get('reset_at',0)>now)
    for model,limits in policies.items():
        entry=recorded['models'].get(model,{})
        used=entry.get('daily_requests',0) if entry.get('reset_at',0)>now else 0
        remaining[model]={'recorded_daily_requests':used,'local_rpd':limits['rpd'],
            'demo_reserve':reserve,'remaining_evaluation_requests':max(0,limits['rpd']-reserve-used),
            'persisted_block_until':entry.get('blocked_until'),
            'blocked_now':entry.get('blocked_until',0)>now}
    return {'mode':'dry-run','phase':phase,'automatic_execution':False,'concurrency':1,'pending_cases':pending,
        'selected_cases':case_ids,
        'skipped_cases':skipped,'judge_calls_required':sum(1 for row in pending if phase!='generate'),
        'budget_by_model':remaining,'global_budget':{'daily_limit':total_daily_limit,'demo_reserve':total_reserve,
            'recorded_daily_requests':total_used,'remaining_evaluation_requests':
                max(0,total_daily_limit-total_reserve-total_used) if total_daily_limit is not None else None},
        'preserved_complete_cases':[r['id'] for r in status['cases'] if r['status']=='evaluated'],
        'estimated_calls':sum(by_model.values()),'estimated_calls_by_model':by_model,
        'estimate_note':'Planning only: excludes retries and possible document reindexing; local ML generation uses no Gemini. Tokens/cost not estimated as actual usage.',
        'models':roles,'local_limits':policies,'demo_reserve_per_model':reserve,
        'quota_note':'Local caps, not verified provider quotas. Agent and judge using the same model share one budget.',
        'consolidated':status}


def write_consolidated(path,settings,cache,run):
    value=consolidate(cache,golden(),reference_state(settings))
    atomic_json(path/'consolidated.json',{'run':run,**value})
    lines=['# Avaliação consolidada — Etapa 2','',
           '| Caso | Status atual | Faithfulness | Answer Relevancy |',
           '|---|---|---|---|']
    for row in value['cases']:
        def score(name):
            metric=row['metrics'][name]
            return f"{metric['score']:.3f}" if metric.get('score') is not None else metric['status']
        lines.append(f"| {row['id']} | {row['status']} | {score('faithfulness')} | {score('answer_relevancy')} |")
    lines+=['','Históricos e notas baixas válidas foram preservados. Respostas incompletas são inelegíveis, sem reescrever suas notas antigas.',
        'Falhas operacionais, métricas inválidas e não executadas não recebem zero.',
        '',f"Parada: {run.get('stop_reason') or 'nenhuma'}; chamadas deste processo: {run.get('actual_api_calls',0)}.",
        'Tokens observados estão no ledger das chamadas. Reservas de orçamento não são consumo real; custo não foi inventado.']
    (path/'consolidated.md').write_text('\n'.join(lines),encoding='utf-8')


def usage_summary(records):
    result={}
    for row in records:
        value=result.setdefault(row['model'],{'requests':0,'failed':0,'known_total_tokens':0,'requests_without_total_usage':0})
        value['requests']+=1
        value['failed']+=row['status']=='failed'
        tokens=(row.get('usage') or {}).get('total')
        if type(tokens) is int:
            value['known_total_tokens']+=tokens
        else:
            value['requests_without_total_usage']+=1
    return result


def run_pipeline(settings,cache,policies,reserve=5,interval=15,max_calls=100,
                 phase='all',output=None,budget_dir=None,max_output_tokens=8192,
                 total_daily_limit=None,total_reserve=0,case_ids=None):
    if phase not in ('all','generate','judge') or reserve<0 or interval<0 or max_calls<1:
        raise ValueError('invalid_pipeline_options')
    directory=Path(budget_dir or ROOT/'data/runtime/evaluation_pipeline')
    with exclusive_run(directory/'pipeline.lock'):
        planned=queue_plan(settings,cache,policies,reserve,phase,directory,total_daily_limit,total_reserve,case_ids)
        path=Path(output or ROOT/'reports/evaluation'/(
            datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-pipeline-'+uuid4().hex[:6]))
        if path.exists():
            raise ValueError('report_directory_already_exists')
        path.mkdir(parents=True)
        budget=ModelBudget(budget_path(directory,settings),policies,reserve,max_calls,
                           max(interval,settings.request_interval_seconds),
                           total_daily_limit=total_daily_limit,total_reserve=total_reserve)
        run={'mode':'live','phase':phase,'concurrency':1,'planned_cases':[p['id'] for p in planned['pending_cases']],
             'local_limits':policies,'demo_reserve_per_model':reserve,'steps':[],
             'actual_api_calls':0,'stop_reason':None}
        run.update(total_daily_limit=total_daily_limit,total_demo_reserve=total_reserve)
        atomic_json(path/'plan.json',planned)
        def checkpoint(records):
            run['actual_api_calls']=len(records)
            run['usage_by_model']=usage_summary(records)
            run['cost']=None
            atomic_json(path/'calls.json',records)
            atomic_json(path/'progress.json',run)
        ledger=BudgetLedger(Limiter(0,max_calls),budget,checkpoint,max_output_tokens)
        checkpoint([])
        write_consolidated(path,settings,cache,run)
        try:
            for stage in (['generate','judge'] if phase=='all' else [phase]):
                for case in golden():
                    if case_ids is not None and case['id'] not in case_ids:
                        continue
                    response=cache.response(case,reference_state(settings))
                    if response and all(cache.metric(response,name) for name in METRICS):
                        continue
                    if stage=='generate' and response:
                        continue
                    if stage=='judge' and not response:
                        continue
                    run['current']={'case':case['id'],'phase':stage}
                    checkpoint(ledger.records)
                    step_path=path/(stage+'-'+case['id'])
                    _,report=execute_batch(settings,cache,[case['id']],phase=stage,
                        interval=0,max_calls=max_calls,output=step_path,ledger_factory=lambda _:ledger)
                    run['steps'].append({'case':case['id'],'phase':stage,'report':str(step_path/'results.json')})
                    # An invalid LLM verdict is recorded once; never retry it in a loop.
                    run['stop_reason']=budget.block_reason or report.get('stop_reason')
                    checkpoint(ledger.records)
                    write_consolidated(path,settings,cache,run)
                    if run['stop_reason']:
                        return path,run
        except KeyboardInterrupt:
            run['stop_reason']='interrupted_by_user'
        except Exception:
            # Preserve checkpoints without serializing exception bodies or credentials.
            run['stop_reason']='local_execution_failure'
            raise
        finally:
            checkpoint(ledger.records)
            write_consolidated(path,settings,cache,run)
        return path,run
