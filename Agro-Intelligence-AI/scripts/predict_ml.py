"""Inferência local: python -m scripts.predict_ml --example ou --input atributos.json."""
import argparse
import json
from pathlib import Path

from agro_ai.config import ROOT
from agro_ai.ml.inference import predict_risk


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--example',action='store_true')
    group.add_argument('--input',type=Path)
    args=parser.parse_args()
    values=(json.loads((ROOT/'reports/ml/example.json').read_text(encoding='utf-8'))['features']
            if args.example else json.loads(args.input.read_text(encoding='utf-8')))
    print(json.dumps(predict_risk(values),indent=2,ensure_ascii=False))


if __name__=='__main__':
    main()
