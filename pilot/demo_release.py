"""Require a matching passed frozen evaluation before serving demo estimates."""

from pilot.demo_artifacts import read_json, verify_artifact
from pilot.evaluate import sha256


def require_qualified_demo(bundle, evaluation):
    if not (evaluation / "manifest.json").exists():
        raise ValueError("This candidate has no final demo evaluation; prediction serving is unavailable")
    model = verify_artifact(bundle)
    result = verify_artifact(evaluation)
    if result.get("kind") != "demo_test" or result.get("bundle_manifest_sha256") != sha256(bundle / "manifest.json") or result.get("split_id") != model["split_id"]:
        raise ValueError("Final evaluation does not belong to this exact frozen predictor")
    metrics = read_json(evaluation / "metrics.json")
    if not result.get("passed") or not metrics.get("passed"):
        failed = [check["check"] for check in metrics["checks"] if not check["passed"]]
        raise ValueError("Candidate failed final demo qualification; predictions are unavailable. Failed checks: " + "; ".join(failed))
    return metrics
