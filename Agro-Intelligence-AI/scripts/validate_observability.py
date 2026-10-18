"""Validação opt-in de cinco traces; nunca imprime payloads ou credenciais."""
import argparse
import json
import time

from agro_ai.config import ROOT,get_settings
from agro_ai.agents.orchestrator import AgentOrchestrator
from agro_ai.gemini import GeminiGateway
from agro_ai.rag import DocumentIndex
from agro_ai.observability import chat_request,observation,get_telemetry,telemetry_settings,check_authentication,complete_chat
from scripts.validate_agents import TASKS

QUESTIONS=[
    'Quais regiões possuem maior faturamento e qual a margem regional?',
    'Quais posições de estoque estão em ruptura?',
    'Qual é a política de descontos?',
    TASKS[0],TASKS[2],
]


def verify_trace(client,trace_id,expected):
    """Readback v5 sem campos de input/output. Flush não é prova de ingestão."""
    response=client.api.observations.get_many(
        trace_id=trace_id,fields='core,basic,time',limit=100,
        request_options={'timeout_in_seconds':3,'max_retries':0})
    rows=response.data
    ids={row.id for row in rows}
    names={row.name for row in rows}
    roots=[row for row in rows if row.name=='agro.chat.request' and not row.parent_observation_id]
    complete=bool(len(roots)==1 and expected<=names and all(
        row.trace_id==trace_id and row.end_time is not None and
        ((row.parent_observation_id is None and row.id==roots[0].id) or
         row.parent_observation_id in ids) for row in rows))
    return {'complete':complete,'observations':len(rows),'names':sorted(names)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Autoriza cinco perguntas Gemini/RAG e envio ao Langfuse; consome cota.')
    args=parser.parse_args()
    config=telemetry_settings()
    report={'requested_questions':5,'executed_questions':0,'created_traces':0,
            'server_confirmed_traces':0,'ui_visually_confirmed':False,'results':[]}
    if not args.live:
        report['skip_reason']='live_opt_in_required'
    elif not config.enabled or not config.configured:
        report['skip_reason']='langfuse_disabled_or_credentials_absent'
    elif not get_settings().api_key:
        report['skip_reason']='gemini_key_absent'
    else:
        telemetry=get_telemetry()
        report['authentication']=check_authentication(telemetry.client)
        if not report['authentication']['ok']:
            report['skip_reason']='langfuse_auth_unavailable'
        else:
            pending=[]
            for number,question in enumerate(QUESTIONS,1):
                runner=AgentOrchestrator(get_settings(),GeminiGateway,DocumentIndex)
                record={'question_number':number,'status':'failed'}
                try:
                    history=[{'role':'user','content':question}]
                    with chat_request(question,[]) as root:
                        prepared=runner.prepare(history)
                        answer=''.join(runner.stream_answer(prepared,history))
                        status=complete_chat(answer,prepared.state.trace,prepared.state.answer_mode)
                        record.update(status=status,agents=prepared.agents)
                    expected={'agro.chat.request','agro.chat.question','agro.chat.response',
                              'agro.orchestration.prepare','agro.orchestration.response','agro.agent.tool',
                              'agro.gemini.generate'}|{'agro.agent.'+agent for agent in prepared.agents}
                    expected|=({'agro.duckdb.commercial_snapshot'} if 'comercial' in prepared.agents else set())
                    if 'estoque' in prepared.agents:
                        expected.add('agro.duckdb.stock_and_orders')
                    if number==3:
                        expected|={'agro.chroma.retrieve','agro.gemini.embeddings'}
                    if number==5:
                        expected.add('agro.ml.predict_backorder')
                    if root.trace_id:
                        record['trace_id']=root.trace_id
                        pending.append((record,expected))
                except Exception:
                    # Exceção/payload do provedor não entra no relatório.
                    record['status']='failed'
                finally:
                    runner.close()
                report['results'].append(record)
                report['executed_questions']+=1
            report['created_traces']=len(pending)
            report['flush_completed']=telemetry.flush(wait=True,timeout=5)
            for attempt in range(4):
                if attempt:
                    time.sleep(5)
                for record,expected in pending:
                    if record.get('complete'):
                        continue
                    try:
                        record.update(verify_trace(telemetry.client,record['trace_id'],expected))
                    except Exception:
                        record['readback_status']='unavailable'
                if all(record.get('complete') for record,_ in pending):
                    break
            report['server_confirmed_traces']=sum(bool(record.get('complete')) for record,_ in pending)
    path=ROOT/'reports/observability'
    path.mkdir(parents=True,exist_ok=True)
    (path/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
