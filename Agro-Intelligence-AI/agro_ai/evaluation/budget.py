"""Persistent admission budget for the sequential evaluator; no quota evasion."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from uuid import uuid4

from agro_ai.api_limits import limit_evidence, next_daily_reset
from agro_ai.diagnostics import ChatFailure
from agro_ai.evaluation.resume import Ledger


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.'+uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    temporary.replace(path)


@contextmanager
def exclusive_run(path):
    """OS lock automatically released on Ctrl+C/crash; no stale lock removal."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0,2)
        if handle.tell()==0:
            handle.write(b'0');handle.flush()
        handle.seek(0)
        try:
            if __import__('os').name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            raise ValueError('another_evaluation_pipeline_is_running') from None
        try:
            yield
        finally:
            handle.seek(0)
            if __import__('os').name=='nt':
                msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(handle.fileno(),fcntl.LOCK_UN)


class ModelBudget:
    def __init__(self,path,policies,reserve=5,max_calls=100,interval=15,
                 clock=time.time,sleep=time.sleep,total_daily_limit=None,total_reserve=0):
        self.path=Path(path);self.policies=policies;self.reserve=reserve
        self.max_calls=max_calls;self.interval=interval;self.clock=clock;self.sleep=sleep
        self.session_calls=0;self.block_reason=None
        if total_daily_limit is not None and (type(total_daily_limit) is not int or total_daily_limit<1):
            raise ValueError('invalid_total_daily_limit')
        if type(total_reserve) is not int or total_reserve<0:
            raise ValueError('invalid_total_reserve')
        self.total_daily_limit=total_daily_limit;self.total_reserve=total_reserve

    def read(self):
        return json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'models':{}}

    def stop(self,reason):
        self.block_reason=reason
        raise ChatFailure('evaluation','local_budget',None,reason)

    def acquire(self,model,estimated_tokens):
        if self.block_reason:
            self.stop(self.block_reason)
        policy=self.policies[model]
        if estimated_tokens>policy['tpm']:
            self.stop('request_exceeds_local_tpm')
        while True:
            state=self.read();now=self.clock()
            entry=state['models'].setdefault(model,{'requests':[]})
            if entry.get('blocked_until',0)>now:
                self.stop('retry_after_or_daily_block')
            reset=entry.get('reset_at',0)
            if reset<=now:
                entry.update(daily_requests=0,reset_at=next_daily_reset(datetime.fromtimestamp(now,timezone.utc)).timestamp())
            if self.session_calls>=self.max_calls:
                self.stop('session_request_budget_exhausted')
            if entry['daily_requests']>=max(0,policy['rpd']-self.reserve):
                self.stop('daily_demo_reserve_reached')
            total_used=sum(e.get('daily_requests',0) for e in state['models'].values() if e.get('reset_at',0)>now)
            if self.total_daily_limit is not None and total_used>=max(0,self.total_daily_limit-self.total_reserve):
                self.stop('total_daily_demo_reserve_reached')
            recent=[r for r in entry['requests'] if r['at']>now-60]
            entry['requests']=recent
            remaining=policy['tpm']-sum(r['budget_tokens'] for r in recent)
            last=max([r['at'] for e in state['models'].values() for r in e.get('requests',[])],default=-1e12)
            delay=max(0,self.interval-(now-last))
            if len(recent)>=policy['rpm'] or estimated_tokens>remaining:
                delay=max(delay,min(r['at']+60-now for r in recent)+.01)
            if delay>0:
                self.sleep(min(delay,60));continue
            identifier=uuid4().hex
            recent.append({'id':identifier,'at':now,'budget_tokens':estimated_tokens,'usage':None,'status':'reserved'})
            entry['daily_requests']+=1
            atomic_json(self.path,state)  # Debit before dispatch, including interrupted/failed RPCs.
            self.session_calls+=1
            return identifier

    def finish(self,model,identifier,record,error=None):
        state=self.read();entry=state['models'][model]
        item=next(r for r in entry['requests'] if r['id']==identifier)
        item.update(status=record.get('status','failed'),usage=record.get('usage'))
        actual=(record.get('usage') or {}).get('total')
        if type(actual) is int and actual>=0:
            item['budget_tokens']=actual
        if error is not None:
            signal=limit_evidence(error)
            code=getattr(error,'code',None)
            if code==429 or signal['retry_after_seconds'] is not None:
                now=self.clock()
                entry['blocked_until']=(next_daily_reset(datetime.fromtimestamp(now,timezone.utc)).timestamp()
                    if signal['daily_limit'] and code==429 else now+max(signal['retry_after_seconds'] or 0,60 if code==429 else 0))
                self.block_reason='api_rate_limit_or_retry_after'
        atomic_json(self.path,state)


class BudgetLedger(Ledger):
    def __init__(self,limiter,budget,checkpoint,max_output_tokens=8192):
        super().__init__(limiter)
        self.budget=budget;self.checkpoint=checkpoint;self.max_output_tokens=max_output_tokens
        self.admission=None

    def start(self,model,kind):
        record,started=super().start(model,kind)
        if self.admission is None or self.admission['model']!=model:
            self.budget.stop('missing_budget_admission')
        record['budget_admission']={**self.admission,'debited_before_dispatch':True}
        self.checkpoint(self.records)  # Durable ledger entry before invoking the SDK.
        return record,started

    def wrap(self,function,model,kind,stream=False):
        def parameters(kwargs):
            kwargs=dict(kwargs)
            if kind!='embedding':
                config=kwargs['config'].model_copy(deep=True)
                config.max_output_tokens=min(config.max_output_tokens or self.max_output_tokens,self.max_output_tokens)
                kwargs['config']=config
            # Conservative local reservation, not reported as API usage/cost.
            serialized=json.dumps({k:(v.model_dump(mode='json',exclude_none=True) if hasattr(v,'model_dump') else v)
                for k,v in kwargs.items()},ensure_ascii=False,default=str)
            estimate=len(serialized.encode('utf-8'))+1024+(self.max_output_tokens if kind!='embedding' else 0)
            return kwargs,estimate
        wrapped=super().wrap(function,model,kind,stream)
        def dispatch(args,kwargs):
            if kwargs.get('model',model)!=model:
                self.budget.stop('request_model_differs_from_budget')
            kwargs,estimate=parameters(kwargs)
            ticket=self.budget.acquire(model,estimate)
            self.admission={'id':ticket,'model':model,'estimated_budget_tokens':estimate}
            return kwargs,ticket,len(self.records)
        if stream:
            def streamed(*args,**kwargs):
                kwargs,ticket,index=dispatch(args,kwargs);error=None
                try:
                    yield from wrapped(*args,**kwargs)
                except BaseException as caught:
                    error=caught;raise
                finally:
                    record=self.records[index] if len(self.records)>index else {'status':'not_dispatched'}
                    self.budget.finish(model,ticket,record,error);self.checkpoint(self.records)
            return streamed
        def call(*args,**kwargs):
            kwargs,ticket,index=dispatch(args,kwargs);error=None
            try:
                return wrapped(*args,**kwargs)
            except BaseException as caught:
                error=caught;raise
            finally:
                record=self.records[index] if len(self.records)>index else {'status':'not_dispatched'}
                self.budget.finish(model,ticket,record,error);self.checkpoint(self.records)
        return call


def budget_path(directory,settings):
    namespace=hashlib.sha256(settings.api_key.encode()).hexdigest()[:20]
    return Path(directory)/('budget-'+namespace+'.json')
