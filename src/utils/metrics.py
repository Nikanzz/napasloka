from collections.abc import Sequence
from dataclasses import dataclass, field
from time import perf_counter
import numpy as np


@dataclass
class PerformanceTimer:
    elapsed_seconds: float | None = field(default=None, init=False)
    _started_at: float | None = field(default=None, init=False, repr=False)

    def __enter__(self) -> "PerformanceTimer":
        self._started_at = perf_counter()
        return self

    def __exit__(self, *_: object) -> None:
        if self._started_at is None:
            raise RuntimeError("Timer was not started")
        self.elapsed_seconds = perf_counter() - self._started_at


def mean_absolute_percentage_error_percent(
    y_true: Sequence[float],
    y_pred: Sequence[float],
) -> float:
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
