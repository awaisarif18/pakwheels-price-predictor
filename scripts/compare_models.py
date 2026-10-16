"""Compare M3 candidates offline. This command exposes no test-set option."""

import argparse
from pathlib import Path

from pilot.comparison import run_comparison
from pilot.paths import PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path,
                        default=PROJECT_ROOT / "data/processed/pilot_batch_001_v2")
    parser.add_argument("--evaluation-dir", type=Path,
                        default=PROJECT_ROOT / "data/processed/pilot_batch_001_eval_v1")
    parser.add_argument("--config", type=Path,
                        default=PROJECT_ROOT / "configs/experiments.json")
    parser.add_argument("--output-dir", type=Path,
                        default=PROJECT_ROOT / "reports/pilot/m3_batch_001_v1")
    args = parser.parse_args()
    manifest = run_comparison(args.dataset_dir, args.evaluation_dir, args.output_dir, args.config)
    print(f"Saved {manifest['experiment_id']} to {args.output_dir}")


if __name__ == "__main__":
    main()
