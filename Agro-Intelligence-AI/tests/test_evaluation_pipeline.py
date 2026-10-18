from dataclasses import replace
from datetime import datetime,timezone
import json
from types import SimpleNamespace
import pytest
from google.genai import types
from google.genai.errors import ClientError

from agro_ai.config import get_settings
from agro_ai.diagnostics import ChatFailure
from agro_ai.evaluation.cache import EvaluationCache,reference_state
from agro_ai.evaluation.batches import golden
from agro_ai.evaluation.budget import ModelBudget,BudgetLedger,budget_path,exclusive_run
from agro_ai.evaluation.pipeline import policies_for,queue_plan,run_pipeline
from agro_ai.evaluation.runner import Limiter


def fake_clock():
    value=[datetime(2026,10,18,12,tzinfo=timezone.utc).timestamp()]
    return value,lambda:value[0],lambda seconds:value.__setitem__(0,value[0]+seconds)


def budget(tmp_path,**kwargs):
    value,clock,sleep=fake_clock()
    caps={'model':{'rpm':2,'tpm':100,'rpd':10}}
    return ModelBudget(tmp_path/'budget.json',caps,clock=clock,sleep=sleep,**kwargs),value


def test_persistent_rpm_tpm_and_demo_reserve(tmp_path):
    guard,now=budget(tmp_path,reserve=8,interval=0)
    first=guard.acquire('model',60)
    guard.finish('model',first,{'status':'success','usage':{'total':60}})
    initial=now[0]
    guard.acquire('model',60)
    assert now[0]>=initial+60
    restarted=ModelBudget(guard.path,guard.policies,reserve=8,clock=guard.clock,sleep=guard.sleep)
    with pytest.raises(ChatFailure):
        restarted.acquire('model',1)
    assert restarted.block_reason=='daily_demo_reserve_reached'
    now[0]+=86400
    reset=ModelBudget(guard.path,guard.policies,reserve=8,interval=0,clock=guard.clock,sleep=guard.sleep)
    reset.acquire('model',1)


def test_rpm_wait_and_unknown_usage_remains_reserved(tmp_path):
    guard,now=budget(tmp_path,reserve=0,interval=0)
    start=now[0]
    for _ in range(3):
        ticket=guard.acquire('model',10)
        guard.finish('model',ticket,{'status':'failed','usage':None})
    assert now[0]>=start+60
    assert guard.read()['models']['model']['daily_requests']==3
    assert guard.read()['models']['model']['requests'][0]['budget_tokens']==10


def test_retry_after_stops_immediately_and_survives_restart(tmp_path):
    guard,now=budget(tmp_path,reserve=0,interval=0)
    ticket=guard.acquire('model',10)
    error=ClientError(429,{'error':{'message':'SECRET','details':[
        {'@type':'google.rpc.RetryInfo','retryDelay':'120s'}]}})
    guard.finish('model',ticket,{'status':'failed'},error)
    state=guard.read()
    assert state['models']['model']['blocked_until']>=now[0]+120
    assert 'SECRET' not in json.dumps(state)
    new=ModelBudget(guard.path,guard.policies,reserve=0,clock=guard.clock,sleep=guard.sleep)
    with pytest.raises(ChatFailure): new.acquire('model',1)
    assert new.session_calls==0


def test_oversize_and_session_limit_do_not_dispatch(tmp_path):
    guard,_=budget(tmp_path,reserve=0,interval=0,max_calls=1)
    with pytest.raises(ChatFailure): guard.acquire('model',101)
    assert guard.session_calls==0
    guard,_=budget(tmp_path/'second',reserve=0,interval=0,max_calls=1)
    guard.acquire('model',1)
    with pytest.raises(ChatFailure): guard.acquire('model',1)
    assert guard.session_calls==1


def test_policy_ids_do_not_change_models_and_share_agent_judge():
    settings=replace(get_settings(),model='main',agent_model='lite',judge_model='lite',embedding_model='embed')
    caps=policies_for(settings)
    assert len(caps)==3
    assert policies_for(settings,overrides={'lite':{'rpd':60}})['lite']['rpd']==60
    with pytest.raises(ValueError): policies_for(settings,overrides={'unvalidated-new-model':{'rpd':50}})
    with pytest.raises(ValueError): policies_for(settings,rpm=0)


def test_dry_plan_uses_actual_cache_without_sdk_or_writes(monkeypatch):
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kw:pytest.fail('no network'))
    settings=get_settings();cache=EvaluationCache()
    plan=queue_plan(settings,cache,policies_for(settings))
    from agro_ai.evaluation.batches import consolidate
    current=consolidate(cache,golden(),reference_state(settings))['cases']
    assert plan['preserved_complete_cases']==[r['id'] for r in current if r['status']=='evaluated']
    assert [r['id'] for r in plan['pending_cases']]==[r['id'] for r in current if r['status']!='evaluated']
    assert set(plan['preserved_complete_cases']).isdisjoint(r['id'] for r in plan['pending_cases'])


def test_generation_then_judgment_then_zero_call_resume(tmp_path,monkeypatch):
    import agro_ai.evaluation.pipeline as module
    import agro_ai.evaluation.batches as batches
    cases=[{**golden()[1],'checks':[]},{**golden()[2],'checks':[]}]
    monkeypatch.setattr(module,'golden',lambda:cases)
    monkeypatch.setattr(batches,'golden',lambda:cases)
    actions=[]
    class Turn:
        tools=[];answer_mode='ml_local';evidence={'stock':{'total':60}}
        def __init__(self,*args): pass
        def prepare(self,history): actions.append('generate')
        def stream(self): yield '60 posições.'
        def close(self): pass
    def generate(**kwargs):
        actions.append('judge');payload=json.loads(kwargs['contents'])
        return SimpleNamespace(text=json.dumps({'claims':[
            {'claim_id':u['claim_id'],'factual':True,'supported':True,'snippet_ids':['s0001'],'reason':'total=60'}
            for u in payload['claim_units']], 'verdicts':[
            {'unit_id':u['unit_id'],'relevant':True,'reason':'contagem'} for u in payload['answer_units']],
            'explanation':'mock'}),usage_metadata=SimpleNamespace(total_token_count=30))
    monkeypatch.setattr(batches,'ChatTurn',Turn)
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kw:SimpleNamespace(
        close=lambda:None,models=SimpleNamespace(generate_content=generate)))
    settings=replace(get_settings(),request_interval_seconds=0)
    cache=EvaluationCache(tmp_path/'cache');caps=policies_for(settings,tpm=1000000,rpm=100)
    path,run=run_pipeline(settings,cache,caps,reserve=0,interval=0,output=tmp_path/'first',budget_dir=tmp_path/'budget')
    assert actions==['generate','generate','judge','judge']
    assert run['actual_api_calls']==2
    assert (path/'consolidated.md').exists() and (path/'calls.json').exists()
    _,again=run_pipeline(settings,cache,caps,reserve=0,interval=0,output=tmp_path/'second',budget_dir=tmp_path/'budget')
    assert again['actual_api_calls']==0 and len(actions)==4


def test_partial_cached_metric_judges_only_missing_and_handles_429(tmp_path,monkeypatch):
    import agro_ai.evaluation.pipeline as module
    import agro_ai.evaluation.batches as batches
    cases=[{**golden()[1],'checks':[]}]
    monkeypatch.setattr(module,'golden',lambda:cases);monkeypatch.setattr(batches,'golden',lambda:cases)
    settings=replace(get_settings(),request_interval_seconds=0)
    cache=EvaluationCache(tmp_path/'cache')
    response=cache.put_response(cases[0],{'answer':'60 posições.','evidence':[{'id':'e1','content':60}]},reference_state(settings),{})
    cache.put_metric(response,'answer_relevancy',{'answer_relevancy':{'status':'evaluated','score':1}}, {}, 'mock')
    calls=[]
    def generate(**kwargs):
        calls.append(json.loads(kwargs['contents']))
        raise ClientError(429,{'error':{'message':'SECRET'}})
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kw:SimpleNamespace(
        close=lambda:None,models=SimpleNamespace(generate_content=generate)))
    monkeypatch.setattr(batches,'ChatTurn',lambda *a:pytest.fail('no generation'))
    caps=policies_for(settings,tpm=1000000)
    path,run=run_pipeline(settings,cache,caps,reserve=0,interval=0,output=tmp_path/'first',budget_dir=tmp_path/'budget')
    assert len(calls)==1 and 'answer_units' not in calls[0]
    assert run['stop_reason']=='api_rate_limit_or_retry_after'
    assert cache.metric(response,'answer_relevancy')['metric']['score']==1
    assert cache.metric(response,'faithfulness') is None
    assert 'SECRET' not in (path/'calls.json').read_text(encoding='utf-8')
    _,again=run_pipeline(settings,cache,caps,reserve=0,interval=0,output=tmp_path/'second',budget_dir=tmp_path/'budget')
    assert len(calls)==1 and again['actual_api_calls']==0


def test_ledger_caps_output_and_records_only_real_usage(tmp_path):
    caps={'model':{'rpm':100,'tpm':100000,'rpd':100}}
    guard=ModelBudget(tmp_path/'budget.json',caps,reserve=0,interval=0)
    saved=[];seen=[]
    ledger=BudgetLedger(Limiter(0,10),guard,lambda records:saved.append(len(records)),max_output_tokens=512)
    def rpc(**kwargs):
        seen.append(kwargs['config'].max_output_tokens)
        return SimpleNamespace(usage_metadata=SimpleNamespace(total_token_count=20),text='{}')
    ledger.wrap(rpc,'model','judge')(config=types.GenerateContentConfig(),contents='test')
    assert seen==[512] and saved==[1,1]
    assert ledger.records[0]['usage']=={'total':20}


def test_lock_releases_after_error(tmp_path):
    path=tmp_path/'lock'
    with pytest.raises(RuntimeError):
        with exclusive_run(path):
            with pytest.raises(ValueError):
                with exclusive_run(path): pass
            raise RuntimeError()
    with exclusive_run(path): pass


def test_ctrl_c_preserves_first_response_and_resume_only_missing_generation(tmp_path,monkeypatch):
    import agro_ai.evaluation.pipeline as module
    import agro_ai.evaluation.batches as batches
    cases=[{**golden()[1],'checks':[]},{**golden()[2],'checks':[]}]
    monkeypatch.setattr(module,'golden',lambda:cases);monkeypatch.setattr(batches,'golden',lambda:cases)
    generated=[];interrupt=[True]
    class Turn:
        tools=[];answer_mode='ml_local';evidence={'stock':{'total':60}}
        def __init__(self,*args): pass
        def prepare(self,history):
            generated.append(history[-1]['content'])
        def stream(self):
            if len(generated)==2 and interrupt[0]:
                raise KeyboardInterrupt()
            yield '60 posições.'
        def close(self): pass
    monkeypatch.setattr(batches,'ChatTurn',Turn)
    monkeypatch.setattr(batches,'GeminiJudge',lambda *a:pytest.fail('generation must not judge'))
    settings=replace(get_settings(),request_interval_seconds=0)
    cache=EvaluationCache(tmp_path/'cache');caps=policies_for(settings)
    _,run=run_pipeline(settings,cache,caps,interval=0,phase='generate',output=tmp_path/'first',budget_dir=tmp_path/'budget')
    assert run['stop_reason']=='interrupted_by_user'
    assert cache.response(cases[0],reference_state(settings)) is not None
    assert cache.response(cases[1],reference_state(settings)) is None
    interrupt[0]=False
    _,again=run_pipeline(settings,cache,caps,interval=0,phase='generate',output=tmp_path/'second',budget_dir=tmp_path/'budget')
    assert len(generated)==3 and generated[-1]==cases[1]['question']
    assert again['actual_api_calls']==0


def test_dry_cli_does_not_create_sdk_or_progress(monkeypatch,capsys):
    import scripts.evaluation_pipeline as cli
    monkeypatch.setattr('sys.argv',['evaluation_pipeline','--dry-run'])
    monkeypatch.setattr(cli,'run_pipeline',lambda *a,**kw:pytest.fail('dry-run cannot execute'))
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kw:pytest.fail('no SDK'))
    cli.main()
    result=json.loads(capsys.readouterr().out)
    assert result['mode']=='dry-run'
    assert len(result['pending_cases'])+len(result['preserved_complete_cases'])==18


def test_twenty_one_total_is_not_per_model_overrun(tmp_path):
    caps={m:{'rpm':100,'tpm':1000000,'rpd':20} for m in ('main','lite','embedding')}
    guard=ModelBudget(tmp_path/'budget.json',caps,reserve=5,interval=0)
    for model,count in [('main',8),('lite',7),('embedding',6)]:
        for _ in range(count):
            ticket=guard.acquire(model,1)
            guard.finish(model,ticket,{'status':'failed','usage':None})
    assert guard.session_calls==21
    assert {m:e['daily_requests'] for m,e in guard.read()['models'].items()}=={'main':8,'lite':7,'embedding':6}
    for _ in range(7): guard.acquire('main',1)
    with pytest.raises(ChatFailure): guard.acquire('main',1)
    assert guard.read()['models']['main']['daily_requests']==15


def test_optional_global_daily_reserve_counts_other_models_and_restarts(tmp_path):
    caps={m:{'rpm':100,'tpm':1000000,'rpd':20} for m in ('main','lite','embedding')}
    guard=ModelBudget(tmp_path/'budget.json',caps,reserve=5,interval=0,total_daily_limit=20,total_reserve=5)
    for i in range(15): guard.acquire(('main','lite','embedding')[i%3],1)
    new=ModelBudget(guard.path,caps,reserve=5,interval=0,total_daily_limit=20,total_reserve=5)
    with pytest.raises(ChatFailure): new.acquire('main',1)
    assert new.block_reason=='total_daily_demo_reserve_reached'
    assert sum(e['daily_requests'] for e in new.read()['models'].values())==15


def test_each_dispatch_debited_and_checkpointed_including_failures_and_retry(tmp_path):
    caps={m:{'rpm':100,'tpm':1000000,'rpd':20} for m in ('main','embedding')}
    guard=ModelBudget(tmp_path/'budget.json',caps,reserve=5,interval=0)
    saved=[];attempts=[]
    ledger=BudgetLedger(Limiter(0,100),guard,lambda records:saved.append(len(records)),512)
    def rpc(**kwargs):
        model=kwargs['model'];attempts.append(model)
        assert guard.read()['models'][model]['daily_requests']==attempts.count(model)
        assert saved[-1]==len(attempts)  # Checkpoint exists before function is invoked.
        assert ledger.records[-1]['budget_admission']['debited_before_dispatch']
        if len(attempts)==1: raise ClientError(503,{'error':{'message':'SECRET'}})
        return SimpleNamespace(usage_metadata=None,text='{}')
    wrapped=ledger.wrap(rpc,'main','judge')
    with pytest.raises(ClientError): wrapped(model='main',contents='a',config=types.GenerateContentConfig())
    wrapped(model='main',contents='a',config=types.GenerateContentConfig())
    ledger.wrap(rpc,'embedding','embedding')(model='embedding',contents=['a'],config=types.EmbedContentConfig())
    assert guard.read()['models']['main']['daily_requests']==2
    assert guard.read()['models']['embedding']['daily_requests']==1
    assert len({r['budget_admission']['id'] for r in ledger.records})==3
    with pytest.raises(ChatFailure):
        wrapped(model='wrong-model',contents='a',config=types.GenerateContentConfig())
    assert len(attempts)==3


def test_judge_dry_run_selects_only_stored_cases(monkeypatch,tmp_path):
    import agro_ai.evaluation.pipeline as module
    cases=[{**golden()[1],'checks':[]},{**golden()[2],'checks':[]}]
    monkeypatch.setattr(module,'golden',lambda:cases)
    settings=get_settings();cache=EvaluationCache(tmp_path/'cache')
    cache.put_response(cases[0],{'answer':'60 posições.','evidence':[{'id':'e1','content':60}]},reference_state(settings),{})
    plan=queue_plan(settings,cache,policies_for(settings),phase='judge',budget_dir=tmp_path/'budget')
    assert [c['id'] for c in plan['pending_cases']]==['G02']
    assert plan['estimated_calls']==plan['judge_calls_required']==1
    assert plan['skipped_cases']==[{'id':'G03','reason':'stored_response_missing'}]
    assert not plan['pending_cases'][0]['needs_generation']
