"""Load the saved local predictor for one JSON form or documented-case checks."""

import argparse
import json
from pathlib import Path

from pilot.demo_artifacts import read_json
from pilot.demo_release import require_qualified_demo
from pilot.paths import PROJECT_ROOT
from pilot.predictor import SavedPredictor, check_examples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=PROJECT_ROOT / "models/pilot/cars_demo_v1")
    parser.add_argument("--evaluation-dir", type=Path, default=PROJECT_ROOT / "reports/pilot/demo_test_v1")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--input-json", type=Path)
    action.add_argument("--check-examples", action="store_true")
    args = parser.parse_args()
    try:
        if not args.check_examples:
            require_qualified_demo(args.model_dir, args.evaluation_dir)
        result = {"verified_examples": check_examples(args.model_dir)} if args.check_examples else SavedPredictor(args.model_dir).predict(read_json(args.input_json))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
