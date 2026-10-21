"""Adopted inputs for the next predictor, separate from historical experiments."""

from dataclasses import replace
import json

from pilot.evaluate import load_evaluation_data
from pilot.features import FEATURE_SETS, MISSING_CATEGORY, NUMERICAL_FIELDS, prepare_input
from pilot.models import build_candidate, input_frame
from pilot.paths import PROJECT_ROOT

DEFAULT_CONTRACT = PROJECT_ROOT / "configs/predictor_inputs_v1.json"
PREDICTOR_COLUMNS = tuple(field for field in FEATURE_SETS["F2"] if field not in {"fuel", "body_type"})


def _checked_contract(contract):
    """Refuse silently changing this adopted version's fields or semantics."""
    expected = {
        "contract_schema_version": 1, "contract_id": "cars_reduced_v1", "base_feature_set": "F2",
        "columns": list(PREDICTOR_COLUMNS),
        "numerical": [field for field in PREDICTOR_COLUMNS if field in NUMERICAL_FIELDS],
        "categorical": [field for field in PREDICTOR_COLUMNS if field not in NUMERICAL_FIELDS],
        "excluded_inputs": ["fuel", "body_type", "registration_year", "registration_gap"],
        "missing_category": MISSING_CATEGORY, "missing_numerical": None,
        "target": "price_pkr", "target_unit": "PKR", "model_year_policy": "direct; no derived age",
        "prediction_support": "not_declared",
    }
    if not isinstance(contract, dict) or any(key not in contract or contract[key] != value for key, value in expected.items()):
        raise ValueError("Predictor input contract differs from the adopted cars_reduced_v1 contract")
    return contract


def load_predictor_contract(path=DEFAULT_CONTRACT):
    """Load a declaration that can later be saved alongside the fitted predictor."""
    return _checked_contract(json.loads(path.read_text(encoding="utf-8")))


def prepare_predictor_input(row, catalogue, scope, *, contract=None):
    """Normalize one source row or form with only the adopted fields visible."""
    contract = load_predictor_contract() if contract is None else _checked_contract(contract)
    selected = {field: row.get(field) for field in contract["columns"]}
    prepared = prepare_input(selected, "F2", catalogue, scope)
    return {field: prepared[field] for field in contract["columns"]}


def predictor_frame(inputs, *, contract=None):
    """Frame prepared development inputs or prepared forms without renormalizing."""
    contract = load_predictor_contract() if contract is None else _checked_contract(contract)
    return input_frame(inputs, "F2", columns=contract["columns"])


def build_predictor_candidate(name, parameters, seed, *, contract=None):
    """Build either shortlisted model with the adopted preprocessing inputs."""
    contract = load_predictor_contract() if contract is None else _checked_contract(contract)
    if name not in {"catboost", "random_forest"}:
        raise ValueError("Next predictor candidates are CatBoost and Random Forest")
    return build_candidate(name, "F2", parameters, seed, columns=contract["columns"])


def load_predictor_development(dataset_dir, evaluation_dir, *, contract=None):
    """Preserve verified development membership; expose only adopted inputs."""
    contract = load_predictor_contract() if contract is None else _checked_contract(contract)
    data = load_evaluation_data(dataset_dir, evaluation_dir, "F2")
    return replace(data, inputs=tuple({field: row[field] for field in contract["columns"]} for row in data.inputs))
