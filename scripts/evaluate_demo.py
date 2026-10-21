"""Score the frozen predictor once on its reserved test and record usage."""

import argparse
from pathlib import Path

from pilot.demo_evaluation import evaluate_demo
from pilot.paths import PROJECT_ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=PROJECT_ROOT / "data/processed/modeling_combined_002_v2")
    parser.add_argument("--evaluation-dir", type=Path, default=PROJECT_ROOT / "data/processed/modeling_combined_002_eval_v2")
    parser.add_argument("--model-dir", type=Path, default=PROJECT_ROOT / "models/pilot/cars_demo_v1")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports/pilot/demo_test_v1")
    args = parser.parse_args()
    result = evaluate_demo(args.dataset_dir, args.evaluation_dir, args.model_dir, args.output_dir)
    print(f"Frozen test scored. Gate passed: {result['passed']}")


if __name__ == "__main__":
    main()
