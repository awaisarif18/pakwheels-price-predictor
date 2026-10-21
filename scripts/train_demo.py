"""Train and save the frozen development-qualified candidate."""

import argparse
from pathlib import Path

from pilot.paths import PROJECT_ROOT
from pilot.predictor import train_demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=PROJECT_ROOT / "data/processed/modeling_combined_002_v2")
    parser.add_argument("--evaluation-dir", type=Path, default=PROJECT_ROOT / "data/processed/modeling_combined_002_eval_v2")
    parser.add_argument("--qualification-dir", type=Path, default=PROJECT_ROOT / "reports/pilot/demo_qualification_v1")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "models/pilot/cars_demo_v1")
    args = parser.parse_args()
    result = train_demo(args.dataset_dir, args.evaluation_dir, args.qualification_dir, args.output_dir)
    print(f"Saved {result['candidate_id']} trained on {result['development_rows']} development rows")


if __name__ == "__main__":
    main()
