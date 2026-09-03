"""Regression metrics used consistently across both algorithms."""

from collections.abc import Sequence

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def mean_absolute_percentage_error_percent(
    y_true: Sequence[float],
    y_pred: Sequence[float],
) -> float:
    """Return MAPE in percent and reject undefined zero-valued actuals."""

    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    if actual.shape != predicted.shape:
        raise ValueError("y_true and y_pred must have the same shape")
    if (actual == 0).any():
        raise ValueError("MAPE is undefined when an actual value is zero")
    return float(np.mean(np.abs((actual - predicted) / actual)) * 100)


def calculate_regression_metrics(
    y_true: Sequence[float],
    y_pred: Sequence[float],
) -> dict[str, float]:
    """Calculate MAE, RMSE, MAPE (percent), and R²."""

    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape": mean_absolute_percentage_error_percent(y_true, y_pred),
        "r2": float(r2_score(y_true, y_pred)),
    }
