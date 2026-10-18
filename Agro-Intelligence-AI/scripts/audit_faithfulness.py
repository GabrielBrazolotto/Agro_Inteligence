"""Audit saved Faithfulness judgments locally, without any API calls."""
import argparse
import json
from pathlib import Path
from agro_ai.evaluation.faithfulness_audit import write_audit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',nargs='+',required=True)
    parser.add_argument('--reports',nargs='+',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if len(args.cases)!=len(args.reports):
        parser.error('Provide one report per case, in matching order.')
    path,results=write_audit(args.reports,args.cases,args.output)
    print(json.dumps({'report':str(path),'actual_api_calls':0,'cases':[
        {'id':r['case_id'],'metric':r['derived_assessment']['faithfulness'],
         'issues':r['derived_assessment'].get('faithfulness_validation',{}).get('issues',[])}
        for r in results]},ensure_ascii=True))


if __name__=='__main__':
    main()
