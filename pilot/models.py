"""Small candidate estimators. Every fitted object belongs to one training fold."""

from collections import defaultdict
from statistics import median

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from pilot.features import FEATURE_SETS, NUMERICAL_FIELDS


class ComparableMedian:
    """Training medians with fixed support and progressively broader fallbacks."""

    levels = (("make", "model", "year"), ("make", "model"), ("make",), ())

    def __init__(self, min_group_size: int):
        self.min_group_size = min_group_size

    def fit(self, inputs: pd.DataFrame, targets):
        if len(inputs) != len(targets) or not len(inputs):
            raise ValueError("Median baseline needs aligned, nonempty training data")
        self.medians_ = []
        for fields in self.levels:
            groups = defaultdict(list)
            for row, target in zip(inputs.to_dict("records"), targets):
                groups[tuple(row[field] for field in fields)].append(float(target))
            self.medians_.append({
                key: median(values) for key, values in groups.items()
                if not fields or len(values) >= self.min_group_size
            })
        return self

    def predict(self, inputs: pd.DataFrame) -> np.ndarray:
        predictions = []
        for row in inputs.to_dict("records"):
            for fields, medians in zip(self.levels, self.medians_):
                key = tuple(row[field] for field in fields)
                if key in medians:
                    predictions.append(medians[key])
                    break
        return np.asarray(predictions, dtype=float)


def selected_columns(feature_set: str, columns=None) -> tuple[str, ...]:
    """Validate an ordered subset without changing the saved feature contract."""
    allowed = FEATURE_SETS[feature_set]
    if columns is None:
        return allowed
    if not isinstance(columns, (list, tuple)) or not columns or any(not isinstance(item, str) for item in columns):
        raise ValueError("Feature columns must be a nonempty ordered list")
    columns = tuple(columns)
    if len(set(columns)) != len(columns) or any(item not in allowed for item in columns):
        raise ValueError("Feature columns must be unique fields from the feature contract")
    if columns != tuple(item for item in allowed if item in columns):
        raise ValueError("Feature columns must retain contract order")
    return columns


def input_frame(rows, feature_set: str, *, columns=None) -> pd.DataFrame:
    """Select only contract fields and express numeric nulls as NaN for libraries."""
    frame = pd.DataFrame(rows, columns=list(selected_columns(feature_set, columns)))
    for field in frame:
        if field in NUMERICAL_FIELDS:
            frame[field] = pd.to_numeric(frame[field]).astype(float)
        else:
            frame[field] = frame[field].astype(object)
    return frame


def build_candidate(name: str, feature_set: str, parameters: dict, seed: int, *, columns=None):
    """Return a fresh unfitted candidate, never a reused/pre-fitted transformer."""
    columns = selected_columns(feature_set, columns)
    numerical = [field for field in columns if field in NUMERICAL_FIELDS]
    categorical = [field for field in columns if field not in NUMERICAL_FIELDS]
    if name == "median":
        return ComparableMedian(**parameters)
    if name == "catboost":
        return CatBoostRegressor(
            **parameters, cat_features=categorical, random_seed=seed,
            thread_count=1, allow_writing_files=False, verbose=False,
            task_type="CPU", nan_mode="Min",
        )
    numeric_steps = [("impute", SimpleImputer(strategy="median", keep_empty_features=True))]
    if name == "ridge":
        numeric_steps.append(("scale", StandardScaler()))
        estimator = Ridge(**parameters)
    elif name == "random_forest":
        estimator = RandomForestRegressor(**parameters, random_state=seed, n_jobs=1)
    else:
        raise ValueError(f"Unknown candidate: {name}")
    preprocessing = ColumnTransformer([
        ("numeric", Pipeline(numeric_steps), numerical),
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
    ])
    return Pipeline([("preprocess", preprocessing), ("model", estimator)])


def preprocessing_policy(name: str) -> dict:
    """Record the fixed conventions alongside the experiment parameters."""
    if name == "median":
        return {"levels": [list(level) for level in ComparableMedian.levels],
                "fit": "training-only medians; final global fallback always available"}
    if name == "catboost":
        return {"categorical": "contract strings; native categorical handling",
                "numeric": "float with NaN; nan_mode=Min", "scaling": "none",
                "thread_count": 1, "task_type": "CPU", "allow_writing_files": False}
    return {"categorical": "training-only one-hot; unknown categories all zero",
            "numeric": "training-only median imputation; all-missing training column uses 0",
            "scaling": "training-only StandardScaler" if name == "ridge" else "none",
            "threads": 1}
