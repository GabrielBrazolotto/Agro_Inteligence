"""Economical sequential evaluation, explicit --live or --dry-run."""
import argparse
import json
from pathlib import Path

from agro_ai.config import ROOT,get_settings
from agro_ai.diagnostics import configure_logging
from agro_ai.evaluation.cache import EvaluationCache
from agro_ai.evaluation.pipeline import policies_for,queue_plan,run_pipeline


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--live',action='store_true')
    parser.add_argument('--phase',choices=['all','generate','judge'],default='all')
    parser.add_argument('--cases',nargs='+',help='Optional explicit golden case IDs; other cases are skipped')
    parser.add_argument('--cache-dir',type=Path,default=ROOT/'data/runtime/evaluation_cache')
    parser.add_argument('--quota-config',type=Path,help='Per-model JSON with rpm/tpm/rpd; configured model IDs only')
    parser.add_argument('--rpm',type=int,default=4)
    parser.add_argument('--tpm',type=int,default=100000)
    parser.add_argument('--daily-limit',type=int,default=20)
    parser.add_argument('--reserve-demo',type=int,default=5)
    parser.add_argument('--total-daily-limit',type=int,help='Optional combined daily cap across all models')
    parser.add_argument('--total-reserve-demo',type=int,default=0)
    parser.add_argument('--interval',type=float,default=15)
    parser.add_argument('--max-calls',type=int,default=100)
    parser.add_argument('--max-output-tokens',type=int,default=8192)
    args=parser.parse_args()
    if not 0<=args.reserve_demo or not 0<=args.interval<=60 or args.max_calls<1 or not 256<=args.max_output_tokens<=65536:
        parser.error('Invalid budget, interval or output limit.')
    if (args.total_daily_limit is not None and args.total_daily_limit<1) or args.total_reserve_demo<0:
        parser.error('Invalid total budget.')
    if args.total_reserve_demo and args.total_daily_limit is None:
        parser.error('--total-reserve-demo requires --total-daily-limit.')
    settings=get_settings();cache=EvaluationCache(args.cache_dir)
    try:
        overrides=json.loads(args.quota_config.read_text(encoding='utf-8')) if args.quota_config else None
        policies=policies_for(settings,args.rpm,args.tpm,args.daily_limit,overrides)
        if args.cases:
            from agro_ai.evaluation.batches import golden
            if len(set(args.cases))!=len(args.cases) or set(args.cases)-{c['id'] for c in golden()}:
                parser.error('Unknown or duplicate case IDs.')
    except (ValueError,TypeError,OSError):
        parser.error('Invalid quota configuration; use positive integer caps for configured models only.')
    if args.dry_run:
        print(json.dumps(queue_plan(settings,cache,policies,args.reserve_demo,args.phase,
            total_daily_limit=args.total_daily_limit,total_reserve=args.total_reserve_demo,
            case_ids=args.cases),ensure_ascii=False,indent=2))
        return
    if not settings.api_key:
        parser.error('GEMINI_API_KEY is not configured.')
    configure_logging()
    path,result=run_pipeline(settings,cache,policies,args.reserve_demo,args.interval,args.max_calls,
        args.phase,max_output_tokens=args.max_output_tokens,
        total_daily_limit=args.total_daily_limit,total_reserve=args.total_reserve_demo,case_ids=args.cases)
    print(json.dumps({'report':str(path),**result},ensure_ascii=False))


if __name__=='__main__':
    main()
