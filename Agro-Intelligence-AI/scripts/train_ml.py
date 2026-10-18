"""Treino público reproduzível: python -m scripts.train_ml [--download]."""
import argparse
import json
from pathlib import Path

from agro_ai.ml.schema import RAW_DIR, SOURCE_URL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--archive', type=Path, default=RAW_DIR/'Dataset.zip')
    parser.add_argument('--max-rows', type=int, default=200000,
                        help='Amostra uniforme máxima; 0 usa todo o CSV Training.')
    args = parser.parse_args()
    if args.max_rows < 0:
        parser.error('--max-rows deve ser não negativo')
    if args.download and not args.archive.exists():
        import requests
        response = requests.get(SOURCE_URL, timeout=180)
        response.raise_for_status()
        args.archive.parent.mkdir(parents=True, exist_ok=True)
        args.archive.write_bytes(response.content)
    from agro_ai.ml.training import train
    report = train(args.archive, max_rows=args.max_rows)
    print(json.dumps({'used_rows': report['used_rows'], 'splits':report['splits'],
                      'threshold':report['threshold'], 'test_metrics':report['test_metrics']}, indent=2))


if __name__ == '__main__':
    main()
