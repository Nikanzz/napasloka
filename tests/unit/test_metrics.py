"""Regression metric helper smoke test without scientific fixtures."""

import pytest

from ml_pipeline.evaluation.metrics import calculate_regression_metrics


def test_regression_metrics_are_callable() -> None:
    metrics = calculate_regression_metrics([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert set(metrics) == {"mae", "rmse", "mape", "r2"}
    assert metrics == pytest.approx({"mae": 0.0, "rmse": 0.0, "mape": 0.0, "r2": 1.0})
