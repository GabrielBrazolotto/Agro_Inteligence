"""Auditoria somente de leitura de traces existentes; sem geração Gemini."""
import json
from agro_ai.config import ROOT
from agro_ai.observability import get_telemetry,safe_metadata,check_authentication


def main():
    client=get_telemetry().client
    report={'authentication':check_authentication(client),'traces':[]}
    if report['authentication']['ok']:
        source=json.loads((ROOT/'reports/observability/validation.json').read_text(encoding='utf-8'))
        for item in source.get('results',[]):
            trace_id=item.get('trace_id')
            if not trace_id:
                continue
            try:
                response=client.api.observations.get_many(trace_id=trace_id,fields='core,basic,time,usage,metadata',limit=100,
                    request_options={'timeout_in_seconds':5,'max_retries':0})
                rows=response.data
                ids={row.id for row in rows}
                report['traces'].append({'trace_id':trace_id,'question_number':item['question_number'],
                    'linked':all(not row.parent_observation_id or row.parent_observation_id in ids for row in rows),
                    'spans':[{'id':row.id,'parent':row.parent_observation_id,'name':row.name,
                        'start':row.start_time.isoformat(),'duration_ms':round((row.end_time-row.start_time).total_seconds()*1000,3) if row.end_time else None,
                        'level':row.level,'metadata':safe_metadata(row.metadata or {}),
                        'usage':{k:v for k,v in (row.usage_details or {}).items() if k in ('input','output','total','reasoning','cache_read') and type(v) is int},
                        'cost_reported':bool(row.cost_details)} for row in rows]})
            except Exception:
                report['traces'].append({'trace_id':trace_id,'readback':'unavailable'})
    path=ROOT/'reports/observability/audit.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
