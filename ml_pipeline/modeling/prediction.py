"""Timed prediction interface shared across research algorithms."""

from dataclasses import dataclass
from typing import Any

import numpy as np

from ml_pipeline.evaluation.timing import PerformanceTimer


@dataclass(frozen=True)
class PredictionResult:
    """Predictions and measured wall-clock inference duration."""

    values: np.ndarray
    prediction_time_seconds: float


def predict(model: Any, x_test: Any) -> PredictionResult:
    """Generate predictions and time the same operation for either estimator."""

    with PerformanceTimer() as timer:
        values = np.asarray(model.predict(x_test))
    assert timer.elapsed_seconds is not None
    return PredictionResult(values=values, prediction_time_seconds=timer.elapsed_seconds)
