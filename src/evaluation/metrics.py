"""Regression metrics used consistently across both algorithms (Pure NumPy Implementation)."""

from collections.abc import Sequence
import numpy as np


def mean_absolute_percentage_error_percent(
    y_true: Sequence[float],
    y_pred: Sequence[float],
) -> float:
    """Return MAPE in percent and reject undefined zero-valued actuals."""
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    if actual.shape != predicted.shape:
        raise ValueError("y_true and y_pred must have the same shape")
    mask = actual != 0
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def calculate_regression_metrics(
    y_true: Sequence[float],
    y_pred: Sequence[float],
) -> dict[str, float]:
    """Calculate MAE, RMSE, MAPE (percent), and R² using pure NumPy."""
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    if actual.shape != predicted.shape:
        raise ValueError("y_true and y_pred must have the same shape")

    residuals = actual - predicted
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mape = mean_absolute_percentage_error_percent(actual, predicted)

    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    return {
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "r2": r2,
    }
