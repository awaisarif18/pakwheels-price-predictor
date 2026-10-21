"""Freeze support, error criteria, and a candidate using development data only."""

import argparse
from pathlib import Path

from pilot.paths import PROJECT_ROOT
from pilot.qualification import qualify_demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=PROJECT_ROOT / "data/processed/modeling_combined_002_v2")
    parser.add_argument("--evaluation-dir", type=Path, default=PROJECT_ROOT / "data/processed/modeling_combined_002_eval_v2")
    parser.add_argument("--evidence-dir", type=Path, default=PROJECT_ROOT / "reports/pilot/m3_modeling_002_combined_ablation_v1")
    parser.add_argument("--baseline-dir", type=Path, default=PROJECT_ROOT / "reports/pilot/m3_modeling_002_reviewed_v1")
    parser.add_argument("--policy", type=Path, default=PROJECT_ROOT / "configs/demo_qualification_v1.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports/pilot/demo_qualification_v1")
    args = parser.parse_args()
    result = qualify_demo(args.dataset_dir, args.evaluation_dir, args.evidence_dir, args.baseline_dir, args.output_dir, args.policy)
    print(f"Frozen {result['candidate_id']}: {result['status']}")


if __name__ == "__main__":
    main()
