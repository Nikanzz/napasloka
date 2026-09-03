"""Algorithm-neutral model construction and timed fitting."""

from dataclasses import dataclass
from typing import Any

from ml_pipeline.evaluation.timing import PerformanceTimer
from ml_pipeline.modeling.lightgbm_model import create_lightgbm_regressor
from ml_pipeline.modeling.xgboost_model import create_xgboost_regressor


@dataclass(frozen=True)
class TrainingResult:
    """A fitted estimator and its measured wall-clock training duration."""

    model: Any
    training_time_seconds: float


def create_estimator(algorithm: str, parameters: dict[str, Any] | None = None) -> Any:
    """Create one of the two research estimators."""

    factories = {
        "xgboost": create_xgboost_regressor,
        "lightgbm": create_lightgbm_regressor,
    }
    try:
        return factories[algorithm](parameters)
    except KeyError as exc:
        raise ValueError(f"Unsupported algorithm: {algorithm}") from exc


def train_model(model: Any, x_train: Any, y_train: Any) -> TrainingResult:
    """Fit an estimator and measure time using the shared timer."""

    with PerformanceTimer() as timer:
        model.fit(x_train, y_train)
    assert timer.elapsed_seconds is not None
    return TrainingResult(model=model, training_time_seconds=timer.elapsed_seconds)
