"""Offline audit of saved judgments; never repairs verdicts or writes metric cache."""
from datetime import datetime,timezone
import json
from pathlib import Path
from uuid import uuid4

from agro_ai.config import ROOT
from agro_ai.evaluation.cache import digest,file_digest
from agro_ai.evaluation.faithfulness import IndexedFaithfulness,score_indexed_faithfulness,claim_units,evidence_snippets
from agro_ai.evaluation.budget import atomic_json


def audit_report(source,case_id):
    source=Path(source)
    report=json.loads(source.read_text(encoding='utf-8'))
    rows=[row for row in report.get('results',[]) if row.get('id')==case_id]
    if len(rows)!=1:
        raise ValueError('source_case_missing_or_ambiguous')
    row=rows[0];assessment=row.get('current_assessment',{})
    raw=assessment.get('rejected_faithfulness_judgment')
    if not raw:
        raise ValueError('saved_rejected_faithfulness_judgment_missing')
    faith_raw={'claims':raw['claims'],'explanation':raw['explanation']}
    judgment=IndexedFaithfulness.model_validate(faith_raw)
    derived=score_indexed_faithfulness(judgment,row['answer'],row['evidence'])
    payload={'question':row['question'],'claim_units':claim_units(row['answer']),
             'evidence_snippets':evidence_snippets(row['evidence'])}
    if 'verdicts' in raw:
        from agro_ai.evaluation.judge import answer_units
        payload['answer_units']=answer_units(row['answer'])
    matches=[call for call in report.get('calls',[]) if call.get('case_id')==case_id
        and isinstance(call.get('raw_judgment'),dict)
        and call['raw_judgment'].get('claims')==raw['claims']
        and call['raw_judgment'].get('explanation')==raw['explanation']]
    return {'case_id':case_id,'mode':'offline_revalidation','actual_api_calls':0,
        'source_report':str(source.resolve()),'source_sha256':file_digest(source),
        'response_key':row.get('response_key'),'historical_metric':row['metrics']['faithfulness'],
        'preserved_answer_relevancy':row['metrics']['answer_relevancy'],
        'original_answer':row['answer'],'original_evidence':row['evidence'],
        'saved_raw_judgment':raw,'matching_raw_ledger_entries':len(matches),
        'reconstructed_payload':payload,'reconstructed_payload_sha256':digest(payload),
        'payload_note':'Reconstructed deterministically from saved answer/evidence; original HTTP request body was not captured.',
        'derived_assessment':derived,
        'offline_metric_valid':derived['faithfulness']['status'] in ('evaluated','not_applicable'),
        'verdict_modified':False,'metric_cache_modified':False}


def write_audit(sources,case_ids,output=None):
    if len(sources)!=len(case_ids):
        raise ValueError('one_source_report_per_case_required')
    results=[audit_report(source,case_id) for source,case_id in zip(sources,case_ids)]
    path=Path(output or ROOT/'reports/evaluation'/(
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-faithfulness-audit-'+uuid4().hex[:6]))
    if path.exists():
        raise ValueError('audit_output_already_exists')
    path.mkdir(parents=True)
    atomic_json(path/'results.json',{'mode':'offline','actual_api_calls':0,'results':results})
    lines=['# Auditoria offline de Faithfulness','',
           'Nenhum veredito foi corrigido, nenhuma chamada foi feita e nenhuma métrica em cache foi alterada.','']
    for result in results:
        metric=result['derived_assessment']['faithfulness']
        lines.extend([f"## {result['case_id']}",'',f"Fonte: `{result['source_report']}`.",
            f"SHA-256: `{result['source_sha256']}`.",
            f"Resultado offline: `{metric['status']}`, score: `{metric.get('score')}`.",''])
        for issue in result['derived_assessment'].get('faithfulness_validation',{}).get('issues',[]):
            lines.extend([f"- `{issue['claim_id']}`: {', '.join(issue['reasons'])}.",
                          f"  Trecho original: {issue['quote']}"])
        lines.append('')
    (path/'results.md').write_text('\n'.join(lines),encoding='utf-8')
    return path,results
