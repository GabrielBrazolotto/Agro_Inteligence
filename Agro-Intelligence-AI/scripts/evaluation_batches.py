"""Planejar sem rede, ou executar explicitamente um único lote de até 3 casos."""
import argparse
import json
from pathlib import Path
from agro_ai.config import ROOT,get_settings
from agro_ai.diagnostics import configure_logging
from agro_ai.evaluation.cache import EvaluationCache,reference_state
from agro_ai.evaluation.batches import golden,plan,execute_batch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','run'])
    parser.add_argument('--cache-dir',type=Path,default=ROOT/'data/runtime/evaluation_cache')
    parser.add_argument('--import-report',type=Path)
    parser.add_argument('--cases',nargs='+')
    parser.add_argument('--next',action='store_true')
    parser.add_argument('--batch-size',type=int,choices=[2,3],default=2)
    parser.add_argument('--judge-only',action='store_true')
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--interval',type=float,default=15)
    parser.add_argument('--max-calls',type=int,default=12)
    args=parser.parse_args()
    if not 0<=args.interval<=60 or not 1<=args.max_calls<=20:
        parser.error('Intervalo de 0 a 60 segundos; orçamento de 1 a 20 chamadas.')
    if args.action=='run' and (not args.live or bool(args.cases)==args.next):
        parser.error('run requer --live e exatamente uma escolha: --cases ou --next.')
    if args.cases and (len(args.cases)>3 or len(set(args.cases))!=len(args.cases)):
        parser.error('No máximo três casos distintos por comando.')
    configure_logging()
    settings=get_settings();cache=EvaluationCache(args.cache_dir);cases=golden();state=reference_state(settings)
    if args.cases and set(args.cases)-{case['id'] for case in cases}:
        parser.error('Caso inexistente no golden dataset.')
    if args.import_report:
        print(json.dumps({'imported':cache.import_legacy(args.import_report,cases,settings,state)},ensure_ascii=False))
    planned=plan(cache,cases,state,args.batch_size)
    if args.action=='plan':
        path=ROOT/'reports/evaluation/remaining_plan.json'
        path.write_text(json.dumps(planned,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(planned,ensure_ascii=False))
        return
    selected=args.cases or (planned['batches'][0] if planned['batches'] else [])
    if not selected:
        print(json.dumps({'status':'nothing_pending','actual_api_calls':0}))
        return
    path,report=execute_batch(settings,cache,selected,args.judge_only,args.interval,args.max_calls)
    print(json.dumps({'report':str(path),'summary':report['summary'],'actual_api_calls':report['actual_api_calls']},ensure_ascii=False))


if __name__=='__main__':
    main()
