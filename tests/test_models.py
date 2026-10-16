"""Protect training-only preprocessing, comparable fallbacks, and input behavior."""

import unittest

import numpy as np

from pilot.metrics import regression_metrics
from pilot.models import ComparableMedian, build_candidate, input_frame


def vehicle(**changes):
    return {"make": "Honda", "model": "City", "year": 2020, "mileage_km": 0,
            "listing_city": "Lahore", "variant": "1.3", "fuel": "Petrol",
            "transmission": "Manual", "engine_cc": None, "assembly": "Local",
            "body_type": "Sedan", **changes}


class ModelTests(unittest.TestCase):
    def test_median_support_fallbacks_use_only_training_and_reset_on_refit(self):
        frame = input_frame([
            vehicle(), vehicle(), vehicle(year=2021),
            vehicle(model="Civic"), vehicle(make="Suzuki", model="Alto"),
        ], "F0")
        model = ComparableMedian(min_group_size=2).fit(frame, [100, 200, 900, 2000, 3000])
        validation = input_frame([
            vehicle(), vehicle(year=2015), vehicle(model="Civic"),
            vehicle(make="Suzuki", model="Alto"), vehicle(make="Toyota", model="Corolla"),
        ], "F0")
        # Exact family/year, family, make, then global fallbacks.
        np.testing.assert_array_equal(model.predict(validation), [150, 200, 550, 900, 900])
        model.fit(frame.iloc[:1], [50])
        np.testing.assert_array_equal(model.predict(validation), [50] * 5)

    def test_ridge_learns_imputation_scale_and_vocabulary_from_training_only(self):
        training = input_frame([vehicle(engine_cc=1000), vehicle(engine_cc=2000, mileage_km=100)], "F2")
        validation = input_frame([vehicle(listing_city="Unseen", engine_cc=None, mileage_km=10_000)], "F2")
        model = build_candidate("ridge", "F2", {"alpha": 10, "solver": "svd"}, 42)
        model.fit(training, [100000, 200000])
        numeric = model.named_steps["preprocess"].named_transformers_["numeric"]
        encoder = model.named_steps["preprocess"].named_transformers_["categorical"]
        np.testing.assert_array_equal(numeric.named_steps["impute"].statistics_, [2020, 50, 1500])
        np.testing.assert_array_equal(numeric.named_steps["scale"].mean_, [2020, 50, 1500])
        before = [values.copy() for values in encoder.categories_]
        self.assertTrue(np.isfinite(model.predict(validation)).all())
        for values, original in zip(encoder.categories_, before):
            np.testing.assert_array_equal(values, original)
            self.assertNotIn("Unseen", values)
        self.assertEqual(training.loc[0, "mileage_km"], 0)
        self.assertTrue(np.isnan(validation.loc[0, "engine_cc"]))

    def test_tree_candidates_accept_unknown_categories_and_missing_displacement(self):
        training = input_frame([vehicle(year=2015 + index, mileage_km=index * 1000) for index in range(8)], "F2")
        validation = input_frame([vehicle(listing_city="Unseen", variant="New trim")], "F2")
        configurations = {
            "random_forest": {"n_estimators": 5, "min_samples_leaf": 2},
            "catboost": {"iterations": 5, "depth": 2, "learning_rate": 0.1, "loss_function": "RMSE"},
        }
        for name, parameters in configurations.items():
            with self.subTest(candidate=name):
                first = build_candidate(name, "F2", parameters, 42).fit(training, np.arange(8) * 100000 + 1000000)
                second = build_candidate(name, "F2", parameters, 42).fit(training, np.arange(8) * 100000 + 1000000)
                self.assertTrue(np.isfinite(first.predict(validation)).all())
                np.testing.assert_allclose(first.predict(validation), second.predict(validation), rtol=0, atol=0)

    def test_metrics_use_pkr_and_keep_invalid_prediction_sign_visible(self):
        result = regression_metrics([100, 200], [80, 250])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["mae_pkr"], 35)
        self.assertEqual(result["median_ape_pct"], 22.5)
        self.assertEqual(regression_metrics([100], [-20])["nonpositive_predictions"], 1)
        for actual, predicted in [([], []), ([0], [10]), ([100], [np.nan]), ([100], [100, 200])]:
            with self.assertRaises(ValueError):
                regression_metrics(actual, predicted)


if __name__ == "__main__":
    unittest.main()
