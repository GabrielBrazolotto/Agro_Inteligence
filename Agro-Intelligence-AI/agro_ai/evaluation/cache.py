"""Cache persistente append-only: respostas/contextos e métricas válidas separadas."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path

from agro_ai.config import ROOT
from agro_ai.assistant import select_commercial_context
from agro_ai.database import commercial_snapshot
from agro_ai.ml.inference import parse_features
from agro_ai.rag import split_text
from agro_ai.evaluation.judge import Judgment,score_judgment
from agro_ai.evaluation.reference import check_finances
from agro_ai.evaluation.completeness import response_completeness

METRICS=('faithfulness','answer_relevancy')


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,default=str,separators=(',',':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference_state(settings):
    return {'database':file_digest(settings.database),
            'documents':{p.name:file_digest(p) for p in sorted(settings.documents.glob('*.md'))},
            'ml_artifact':file_digest(ROOT/'models/backorder/model.joblib'),
            'ml_metadata':file_digest(ROOT/'models/backorder/metadata.json')}


def valid_metric(metric):
    score=metric.get('score')
    return (metric.get('status')=='evaluated' and type(score) in (float,int)
            and math.isfinite(score) and 0<=score<=1) or (
            metric.get('status')=='not_applicable' and score is None)


class EvaluationCache:
    def __init__(self,directory=None):
        self.directory=Path(directory or ROOT/'data/runtime/evaluation_cache')

    def _put(self,path,payload):
        path.parent.mkdir(parents=True,exist_ok=True)
        envelope={'payload':payload,'content_sha256':digest(payload)}
        try:
            with path.open('x',encoding='utf-8') as stream:
                stream.write(json.dumps(envelope,ensure_ascii=False,indent=2,default=str))
        except FileExistsError:
            return self._read(path)  # Não sobrescrever nem mesmo uma métrica baixa válida.
        return payload

    def _read(self,path):
        envelope=json.loads(path.read_text(encoding='utf-8'))
        if digest(envelope['payload'])!=envelope['content_sha256']:
            raise ValueError('cache_integrity_error')
        return envelope['payload']

    def put_response(self,case,row,state,origin):
        identity={'case_id':case['id'],'question':case['question'],'answer':row['answer'],
                  'evidence':row.get('evidence',[]),'reference_state':state}
        key=digest(identity)
        payload={**identity,'key':key,'tools':row.get('tools',[]),
            'original_generation_status':row.get('original_generation_status',row.get('generation_status')),
            'historical_api_failures':row.get('historical_api_failures',row.get('api_failures',[])),
            'origin':origin,'created_at':datetime.now(timezone.utc).isoformat()}
        return self._put(self.directory/'responses'/case['id']/(key+'.json'),payload)

    def response(self,case,state):
        paths=sorted((self.directory/'responses'/case['id']).glob('*.json'))
        candidates=[self._read(path) for path in paths]
        candidates=[row for row in candidates if row['case_id']==case['id'] and row['question']==case['question'] and row['reference_state']==state]
        candidates=[row for row in candidates if response_completeness(case,row['answer'],row['evidence'])['status']!='failed']
        if not candidates:
            return None
        # Preferir a resposta que já possui mais métricas válidas; não repetir para elevar nota.
        return max(candidates,key=lambda row:(sum(self.metric(row,name) is not None for name in METRICS),row['created_at']))

    def metric(self,response,name):
        path=self.directory/'metrics'/response['key']/(name+'.json')
        if not path.exists():
            return None
        value=self._read(path)
        if value['response_key']!=response['key'] or not valid_metric(value['metric']):
            raise ValueError('invalid_cached_metric')
        return value

    def rejected_responses(self,case,state):
        rejected=[]
        for path in sorted((self.directory/'responses'/case['id']).glob('*.json')):
            row=self._read(path)
            if row['question']!=case['question'] or row['reference_state']!=state:
                continue
            result=response_completeness(case,row['answer'],row['evidence'])
            if result['status']=='failed':
                rejected.append({'response_key':row['key'],'origin':row['origin'],'completeness':result,
                    'historical_metrics':{name:self.metric(row,name)['metric'] for name in METRICS if self.metric(row,name)}})
        return rejected

    def put_metric(self,response,name,assessment,origin,protocol):
        metric=assessment[name]
        if not valid_metric(metric):
            return None
        payload={'response_key':response['key'],'metric':deepcopy(metric),'assessment':deepcopy(assessment),
                 'origin':origin,'protocol':protocol,'created_at':datetime.now(timezone.utc).isoformat()}
        return self._put(self.directory/'metrics'/response['key']/(name+'.json'),payload)

    def event(self,run_id,case_id,row):
        return self._put(self.directory/'events'/run_id/(case_id+'.json'),row)

    def latest_event(self,case_id):
        paths=sorted((self.directory/'events').glob('*/'+case_id+'.json'))
        return self._read(paths[-1]) if paths else None

    def import_legacy(self,path,cases,settings,state):
        """Importação explícita: fontes imutáveis, snapshots financeiros/ML validados."""
        path=Path(path)
        report=json.loads(path.read_text(encoding='utf-8'))
        origin={'report':str(path),'sha256':file_digest(path),'legacy_import':True}
        imported=[]
        for case in cases:
            row=next((r for r in report.get('results',[]) if r.get('id')==case['id'] and r.get('question')==case['question']),None)
            if not row or not row.get('answer') or not row.get('evidence') or row.get('generation_status') not in ('ok','degraded','fallback','reused'):
                continue
            if case['id']=='G01':
                actual=select_commercial_context(commercial_snapshot(settings.database),case['question'])
                indicators=[e['content'] for e in row['evidence'] if e['origin']=='comercial.indicadores']
                if len(indicators)!=1 or canonical(indicators[0])!=canonical(actual):
                    continue
                docs=[d for e in row['evidence'] if e['origin']=='comercial.documentos' for d in e['content']]
                if any(Path(d['source']).name!=d['source'] or
                       d['text'] not in split_text((settings.documents/d['source']).read_text(encoding='utf-8')) for d in docs):
                    continue
            elif case['id']=='G12':
                inference=next((e['content'] for e in row['evidence'] if e['origin']=='ml.inference'),{})
                metadata=json.loads((ROOT/'models/backorder/metadata.json').read_text(encoding='utf-8'))
                if inference.get('features')!=parse_features(case['question']) or inference.get('calibrated') is not False or metadata['artifact_sha256']!=state['ml_artifact']:
                    continue
            else:
                continue  # Sem snapshot histórico verificável, não importar respostas antigas genéricas.
            if any(check['status']!='passed' for check in check_finances(settings.database,case['checks'],row['answer'])):
                continue
            response=self.put_response(case,row,state,origin)
            metrics=row.get('metrics',{})
            if metrics.get('judgment'):
                checked=score_judgment(Judgment.model_validate(metrics['judgment']),row['answer'],row['evidence'])
                for name in METRICS:
                    old=metrics.get(name,{})
                    new=checked.get(name,{})
                    if valid_metric(old) and old.get('status')==new.get('status') and old.get('score')==new.get('score'):
                        self.put_metric(response,name,metrics,origin,'claim_verdict_judge_v1')
            imported.append({'case_id':case['id'],'response_key':response['key'],
                             'cached_metrics':[name for name in METRICS if self.metric(response,name)]})
        return imported
