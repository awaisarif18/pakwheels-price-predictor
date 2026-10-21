"""Trusted local CatBoost bundle, bounded inputs, and save/load verification."""

import math
from importlib.metadata import version

import numpy as np
from catboost import CatBoostRegressor

from pilot.demo_artifacts import (
    finish_artifact, input_hashes, output_path, read_json, save_json, verify_artifact, verify_inputs,
)
from pilot.evaluate import sha256
from pilot.features import MISSING_CATEGORY
from pilot.predictor_inputs import (
    build_predictor_candidate, load_predictor_contract, load_predictor_development,
    predictor_frame, prepare_predictor_input,
)
from pilot.support import family_name, support_reason

RUNTIME_CODE = ("pilot/predictor.py", "pilot/predictor_inputs.py", "pilot/features.py", "pilot/identity.py",
                "pilot/evidence.py", "pilot/support.py", "pilot/models.py")


def form_values(prepared):
    return {key: None if value == MISSING_CATEGORY else value for key, value in prepared.items()}


class SavedPredictor:
    def __init__(self, root):
        self.manifest = verify_artifact(root)
        if self.manifest.get("kind") != "demo_predictor" or self.manifest.get("model") != "catboost":
            raise ValueError("Use a trusted locally produced CatBoost demo bundle")
        from pilot.paths import PROJECT_ROOT
        for name in RUNTIME_CODE:
            if sha256(PROJECT_ROOT / name) != self.manifest["code_sha256"][name]:
                raise ValueError("Predictor implementation changed; verify and version the artifact")
        if read_json(root / "environment.json")["catboost"] != version("catboost"):
            raise ValueError("Predictor requires the recorded CatBoost version")
        self.contract = load_predictor_contract(root / "contract.json")
        self.catalogue, self.scope = read_json(root / "catalogue.json"), read_json(root / "scope.json")
        self.support = read_json(root / "support.json")
        self.model = CatBoostRegressor()
        self.model.load_model(str(root / "model.cbm"))
        if self.model.feature_names_ != self.contract["columns"]:
            raise ValueError("Saved model inputs differ from the adopted contract")

    def predict(self, form):
        prepared = prepare_predictor_input(form, self.catalogue, self.scope, contract=self.contract)
        reason = support_reason(prepared, self.support)
        if reason:
            raise ValueError(reason)
        estimate = float(self.model.predict(predictor_frame([prepared], contract=self.contract))[0])
        if not math.isfinite(estimate) or estimate <= 0:
            raise ValueError("Predictor did not produce a valid positive asking-price estimate")
        return {"price_pkr": round(estimate), "candidate_id": self.manifest["candidate_id"],
                "unit": "PKR", "price_kind": "advertised_asking_price", "qualification": "pilot"}


def check_examples(root):
    predictor = SavedPredictor(root)
    examples = read_json(root / "examples.json")
    for example in examples:
        actual = predictor.predict(example["input"])["price_pkr"]
        if actual != example["expected_price_pkr"]:
            raise ValueError("Saved predictor did not reproduce its documented cases")
    return len(examples)


def train_demo(dataset, evaluation, qualification, output):
    output = output_path(output, (dataset, evaluation, qualification))
    frozen = verify_artifact(qualification)
    verify_inputs(frozen)
    if frozen.get("status") != "qualified_development":
        raise ValueError("Candidate must pass development qualification before training")
    policy = read_json(qualification / "candidate.json")
    contract = load_predictor_contract(qualification / "contract.json")
    data = load_predictor_development(dataset, evaluation, contract=contract)
    if frozen["input_sha256"].get(str((dataset / "manifest.json").resolve())) != sha256(dataset / "manifest.json") or frozen[
        "input_sha256"].get(str((evaluation / "manifest.json").resolve())) != sha256(evaluation / "manifest.json"):
        raise ValueError("Training must use the frozen dataset and evaluation")
    sources = [path for root in (dataset, evaluation, qualification) for path in root.iterdir() if path.is_file()]
    fingerprints = input_hashes(sources)
    model = build_predictor_candidate(policy["model"], policy["parameters"], policy["seed"], contract=contract)
    model.fit(predictor_frame(data.inputs, contract=contract), np.asarray(data.targets, dtype=float))
    support = read_json(qualification / "support.json")
    examples, families = [], set()
    for prepared in data.inputs:
        family = family_name(prepared)
        if family not in families and support_reason(prepared, support) is None:
            estimate = float(model.predict(predictor_frame([prepared], contract=contract))[0])
            examples.append({"input": form_values(prepared), "expected_price_pkr": round(estimate)})
            families.add(family)
    verify_inputs({"input_sha256": fingerprints})
    output.mkdir(parents=True)
    model.save_model(str(output / "model.cbm"))
    for name in ("candidate.json", "contract.json", "catalogue.json", "scope.json", "support.json", "development_metrics.json"):
        (output / name).write_bytes((qualification / name).read_bytes())
    save_json(output / "environment.json", {name: version(name) for name in ("catboost", "numpy", "pandas", "scikit-learn")})
    save_json(output / "examples.json", examples)
    save_json(output / "example_input.json", examples[0]["input"])
    manifest = finish_artifact(output, {"kind": "demo_predictor", "candidate_id": policy["candidate_id"], "model": policy["model"],
                              "dataset_id": frozen["dataset_id"], "split_id": frozen["split_id"],
                              "development_rows": len(data.targets), "test_status": "reserved_at_training",
                              "data_period": "October 2026 collection snapshots"}, fingerprints, RUNTIME_CODE)
    check_examples(output)
    return manifest
