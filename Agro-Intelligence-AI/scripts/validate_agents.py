"""Três tarefas compostas reais: python -m scripts.validate_agents [--live]."""
import argparse
import json

from agro_ai.config import ROOT,get_settings
from agro_ai.agents.tools import SystemTools
from agro_ai.agents.orchestrator import AgentOrchestrator
from agro_ai.gemini import GeminiGateway
from agro_ai.rag import DocumentIndex

TASKS=[
 'Quais rupturas de estoque afetam pedidos pendentes e qual o impacto comercial nas margens?',
 'Compare excesso de estoque, faturamento e descontos; consulte a política comercial.',
 'Preveja o risco de backorder com estoque=10; prazo=8; transito=0; previsao_3m=100; '
 'vendas_1m=20; vendas_3m=60; estoque_minimo=15 e avalie o impacto na carteira e nas margens.',
]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Autoriza Gemini e embeddings reais, consumindo cota.')
    args=parser.parse_args()
    settings=get_settings()
    evidence=[]
    for number,question in enumerate(TASKS,1):
        runner=AgentOrchestrator(settings,GeminiGateway,DocumentIndex,use_llm=args.live)
        try:
            history=[{'role':'user','content':question}]
            prepared=runner.prepare(history)
            answer=''.join(runner.stream_answer(prepared,history))
            assert prepared.agents==['estoque','comercial']
            assert any(row.get('depends_on') for row in prepared.state.trace)
            critical={'duckdb_estoque_pedidos','duckdb_comercial','duckdb_impacto_pares'}
            assert all(row['status']=='ok' for row in prepared.state.trace if row['tool'] in critical)
            record={'task':number,'question':question,'agents':prepared.agents,
                    'tools':prepared.state.trace,'answer':answer,
                    'results':prepared.state.results,'analyses':prepared.state.analyses,
                    'mode':'live' if args.live else 'local_no_llm'}
            evidence.append(record)
            print(json.dumps({'task':number,'agents':prepared.agents,'tools':prepared.state.trace},ensure_ascii=False),flush=True)
        finally:
            runner.close()
    path=ROOT/'reports/agents'
    path.mkdir(parents=True,exist_ok=True)
    name='live_tasks.json' if args.live else 'local_tasks.json'
    (path/name).write_text(json.dumps(evidence,ensure_ascii=False,indent=2,default=str),encoding='utf-8')


if __name__=='__main__':
    main()
