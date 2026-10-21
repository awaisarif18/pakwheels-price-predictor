"""Run fixed individual removals or combined confirmation on development folds only."""

import argparse
from pathlib import Path

from pilot.ablation import run_ablation
from pilot.paths import PROJECT_ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=PROJECT_ROOT / "data/processed/modeling_combined_002_v2")
    parser.add_argument("--evaluation-dir", type=Path, default=PROJECT_ROOT / "data/processed/modeling_combined_002_eval_v2")
    parser.add_argument("--reference-dir", type=Path, default=PROJECT_ROOT / "reports/pilot/m3_modeling_002_reviewed_v1")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs/ablations_modeling_002.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports/pilot/m3_modeling_002_ablation_v1")
    args = parser.parse_args()
    manifest = run_ablation(args.dataset_dir, args.evaluation_dir, args.reference_dir, args.output_dir, args.config)
    print(f"Saved {manifest['experiment_id']} to {args.output_dir}")


if __name__ == "__main__":
    main()
