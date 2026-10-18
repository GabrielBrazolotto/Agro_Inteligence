"""Bateria serial: python -m scripts.evaluate_chat --live [--max-cases 18]."""
import argparse
import json
from agro_ai.config import get_settings
from agro_ai.evaluation.runner import run
from agro_ai.diagnostics import configure_logging


def main():
    configure_logging()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Autoriza geração, embeddings e juiz Gemini, consumindo cota.')
    parser.add_argument('--interval',type=float,default=15)
    parser.add_argument('--max-calls',type=int,default=80)
    parser.add_argument('--max-cases',type=int,default=18)
    args=parser.parse_args()
    if args.interval<0 or args.interval>60 or not 1<=args.max_cases<=18 or args.max_calls<1:
        parser.error('Intervalo de 0 a 60s, 1 a 18 casos e orçamento positivo são necessários.')
    path,report=run(get_settings(),args.live,args.interval,args.max_calls,args.max_cases)
    print(json.dumps({'report':str(path),'summary':report['summary']},ensure_ascii=False))


if __name__=='__main__':
    main()
