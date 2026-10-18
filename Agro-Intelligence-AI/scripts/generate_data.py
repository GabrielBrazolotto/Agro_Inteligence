"""Gerar CSVs com backup automático: python -m scripts.generate_data."""
import argparse
import json
from pathlib import Path

from agro_ai.config import ROOT
from agro_ai.synthetic import SEED, generate, write_dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/seeds')
    args = parser.parse_args()
    backup, manifest = write_dataset(generate(args.seed), args.output, args.seed)
    print(json.dumps({'backup': str(backup), **manifest}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
