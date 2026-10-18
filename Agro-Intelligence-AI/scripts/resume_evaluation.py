"""Retomar somente dois casos, sem liberar os demais 16."""
import argparse
import json
from pathlib import Path
from agro_ai.config import ROOT,get_settings
from agro_ai.diagnostics import configure_logging
from agro_ai.evaluation.resume import run_two


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',required=True)
    parser.add_argument('--cases',nargs=2,default=['G01','G02'])
    parser.add_argument('--reuse-from',type=Path,default=ROOT/'reports/evaluation/20261017T130820Z/results.json')
    parser.add_argument('--interval',type=float,default=15)
    parser.add_argument('--max-calls',type=int,default=6)
    args=parser.parse_args()
    if not 0<=args.interval<=60 or not 1<=args.max_calls<=10:
        parser.error('Intervalo 0–60s; orçamento 1–10 chamadas.')
    configure_logging()
    path,report=run_two(get_settings(),args.reuse_from,args.cases,args.interval,args.max_calls)
    print(json.dumps({'report':str(path),'actual_api_calls':report['actual_api_calls'],
        'reused_answers':report['reused_answers'],'new_generation_cases':report['new_generation_cases'],
        'summary':report['summary']},ensure_ascii=False))


if __name__=='__main__':
    main()
