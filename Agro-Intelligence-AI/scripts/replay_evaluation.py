"""Revalidar respostas de juiz já recebidas; zero chamadas remotas."""
import argparse
import json
from agro_ai.evaluation.resume import replay_saved_judgments


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report_directory')
    args=parser.parse_args()
    report=replay_saved_judgments(args.report_directory)
    print(json.dumps({'report':report['derived_report_directory'],'summary':report['summary'],'additional_api_calls':0},ensure_ascii=False))


if __name__=='__main__':
    main()
