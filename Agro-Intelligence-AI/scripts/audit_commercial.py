"""Auditoria reproduzível de ruptura/margem: python -m scripts.audit_commercial [--live]."""
import argparse
import json

import duckdb

from agro_ai.config import ROOT,get_settings
from agro_ai.database import commercial_snapshot
from agro_ai.agents.tools import SystemTools
from agro_ai.agents.orchestrator import AgentOrchestrator
from agro_ai.gemini import GeminiGateway
from agro_ai.rag import DocumentIndex
from agro_ai.ml.schema import EXAMPLE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Usa Gemini/RAG reais e consome cota.')
    args=parser.parse_args()
    settings=get_settings()
    tools=SystemTools(settings.database)
    stock=tools.stock_and_orders('ruptura')
    strict=tools.rupture_impact()
    snapshot=commercial_snapshot(settings.database)
    with duckdb.connect(str(settings.database),read_only=True) as con:
        unique=con.execute('SELECT COUNT(*)=COUNT(DISTINCT (produto_id,centro_id)) FROM estoque').fetchone()[0]
        invalid=con.execute("""SELECT COUNT(*) FROM vendas WHERE status='faturada' AND
            (receita_liquida IS NULL OR custo_total IS NULL OR margem_valor IS NULL
            OR margem_valor<>receita_liquida-custo_total) LIMIT 1""").fetchone()[0]
        independent=con.execute("""SELECT SUM(v.receita_liquida) FROM vendas v WHERE status='pendente'
            AND EXISTS(SELECT 1 FROM estoque e WHERE e.produto_id=v.produto_id
            AND e.centro_id=v.centro_id AND e.disponivel=0) LIMIT 1""").fetchone()[0]
    assert unique and invalid==0
    assert independent==stock['totais']['carteira_em_ruptura']==strict['totais']['carteira_pendente']
    assert sum(row['receita_faturada'] for row in snapshot['por_regiao'])==snapshot['totais']['receita_faturada']
    report={'mode':'live' if args.live else 'local_no_llm','stock':stock,'strict_impact':strict,
            'regions':snapshot['por_regiao'],'stock_pairs_unique':unique,
            'invalid_financial_rows':invalid,'independent_strict_reconciliation':independent,
            'ml_contract':{'no_inputs':tools.backorder('Preveja risco de backorder')['status'],
                           'six_inputs':tools.backorder(EXAMPLE.rsplit(';',1)[0])['status'],
                           'seven_inputs':tools.backorder(EXAMPLE)},'tasks':[]}
    questions=[
      'Quais rupturas de estoque afetam pedidos pendentes e qual o impacto comercial nas margens?',
      'Quais regiões possuem maior faturamento e qual é a margem média de cada uma?']
    for question in questions:
        runner=AgentOrchestrator(settings,GeminiGateway,DocumentIndex,use_llm=args.live)
        try:
            history=[{'role':'user','content':question}]
            prepared=runner.prepare(history)
            answer=''.join(runner.stream_answer(prepared,history))
            assert not any(row['tool']=='scikit_learn_backorder' for row in prepared.state.trace)
            report['tasks'].append({'question':question,'agents':prepared.agents,
                'tools':prepared.state.trace,'results':prepared.state.results,
                'analyses':prepared.state.analyses,'answer':answer})
        finally:
            runner.close()
    path=ROOT/'reports/audit'
    path.mkdir(parents=True,exist_ok=True)
    output=path/('commercial_live.json' if args.live else 'commercial_local.json')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps({'report':str(output),'stock_totals':stock['totais'],'strict_impact':strict,
                      'regions':snapshot['por_regiao'],
                      'task_tools':[task['tools'] for task in report['tasks']]},ensure_ascii=False,indent=2,default=str))


if __name__=='__main__':
    main()
