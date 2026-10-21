"""Small immutable artifact and provenance helpers for the local demo."""

import json
from datetime import datetime, timezone
from pathlib import Path

from pilot.evaluate import sha256
from pilot.paths import PROJECT_ROOT


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def verify_artifact(root):
    manifest = read_json(root / "manifest.json")
    for name, expected in manifest["output_sha256"].items():
        if sha256(root / name) != expected:
            raise ValueError(f"Artifact checksum mismatch: {root.name}/{name}")
    return manifest


def verify_inputs(manifest):
    for name, expected in manifest["input_sha256"].items():
        if sha256(Path(name)) != expected:
            raise ValueError(f"Frozen input changed: {name}")


def output_path(output, sources):
    output = output.resolve()
    if output.exists():
        raise ValueError("Output already exists; use a new artifact version")
    if output.is_relative_to(PROJECT_ROOT / "data/raw") or any(
        output.is_relative_to(path.resolve()) or path.resolve().is_relative_to(output) for path in sources
    ):
        raise ValueError("Output must be separate from raw data and input artifacts")
    return output


def input_hashes(paths):
    return {str(path.resolve()): sha256(path) for path in paths}


def finish_artifact(output, details, fingerprints, code_files):
    manifest = {**details, "created_at": datetime.now(timezone.utc).isoformat(), "input_sha256": fingerprints,
                "code_sha256": {name: sha256(PROJECT_ROOT / name) for name in code_files},
                "output_sha256": {path.name: sha256(path) for path in output.iterdir() if path.is_file()}}
    save_json(output / "manifest.json", manifest)
    return manifest


def usage_path(split_id, usage_dir=None):
    root = PROJECT_ROOT / "data/manifests/test_usage" if usage_dir is None else usage_dir
    return root / f"{split_id}.json"
