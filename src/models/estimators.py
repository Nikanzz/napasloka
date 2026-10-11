"""Estimator factories, timed fitting, tuning, and prediction for XGBoost and LightGBM."""

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, TimeSeriesSplit

from src.utils.config import load_yaml_config
from src.utils.timing import PerformanceTimer


# ==============================================================================
# Model Factories
# ==============================================================================

def create_xgboost_regressor(parameters: dict[str, Any] | None = None) -> Any:
    """Create an XGBRegressor; parameters come from config or tuning output."""
    from xgboost import XGBRegressor

    return XGBRegressor(**(parameters or {}))


def create_lightgbm_regressor(parameters: dict[str, Any] | None = None) -> Any:
    """Create an LGBMRegressor; parameters come from config or tuning output."""
    from lightgbm import LGBMRegressor

    params = {"verbose": -1, "importance_type": "gain"}
    if parameters:
        params.update(parameters)
    return LGBMRegressor(**params)


def create_estimator(algorithm: str, parameters: dict[str, Any] | None = None) -> Any:
    """Create one of the two research estimators ('xgboost' or 'lightgbm')."""
    factories = {
        "xgboost": create_xgboost_regressor,
        "lightgbm": create_lightgbm_regressor,
    }
    try:
        return factories[algorithm](parameters)
    except KeyError as exc:
        raise ValueError(f"Unsupported algorithm: {algorithm}") from exc


# ==============================================================================
# Timed Fitting and Prediction
# ==============================================================================

@dataclass(frozen=True)
class TrainingResult:
    """A fitted estimator and its measured wall-clock training duration."""

    model: Any
    training_time_seconds: float


def train_model(model: Any, x_train: Any, y_train: Any) -> TrainingResult:
    """Fit an estimator and measure time using the shared timer."""
    with PerformanceTimer() as timer:
        model.fit(x_train, y_train)
    assert timer.elapsed_seconds is not None
    return TrainingResult(model=model, training_time_seconds=timer.elapsed_seconds)


@dataclass(frozen=True)
class PredictionResult:
    """Predictions and measured wall-clock inference duration."""

    values: np.ndarray
    prediction_time_seconds: float


def predict(model: Any, x_test: Any) -> PredictionResult:
    """Generate predictions and time the inference operation."""
    with PerformanceTimer() as timer:
        values = np.asarray(model.predict(x_test))
    assert timer.elapsed_seconds is not None
    return PredictionResult(values=values, prediction_time_seconds=timer.elapsed_seconds)


# ==============================================================================
# Hyperparameter Tuning with TimeSeriesSplit
# ==============================================================================

def build_search_cv(estimator: Any, algorithm: str) -> GridSearchCV | RandomizedSearchCV:
    """Build a search object from config, supporting both randomized and grid search."""
    config = load_yaml_config("tuning.yaml")
    if not config.get("enabled", False):
        raise RuntimeError("Hyperparameter tuning is disabled in configs/tuning.yaml")

    search_spaces = config.get("search_spaces", {}).get(algorithm, {})
    if not search_spaces:
        raise ValueError(f"Search space has not been finalized for {algorithm}")

    cv_config = config.get("cross_validation", {})
    n_splits = cv_config.get("n_splits")
    if not isinstance(n_splits, int) or n_splits < 2:
        raise ValueError("TimeSeriesSplit n_splits must be finalized before tuning")

    max_train_size = cv_config.get("max_train_size")
    if max_train_size is not None:
        max_train_size = int(max_train_size)
    cv = TimeSeriesSplit(n_splits=n_splits, max_train_size=max_train_size)
    scoring = config.get("scoring", "neg_mean_absolute_error")
    strategy = config.get("strategy", "randomized_search")
    n_jobs = int(config.get("n_jobs", -1))

    if strategy == "randomized_search":
        n_iter = int(config.get("n_iter", 10))
        random_state = config.get("random_state", 42)
        return RandomizedSearchCV(
            estimator=estimator,
            param_distributions=search_spaces,
            n_iter=n_iter,
            cv=cv,
            scoring=scoring,
            random_state=random_state,
            refit=True,
            n_jobs=n_jobs,
        )
    elif strategy == "grid_search":
        return GridSearchCV(
            estimator=estimator,
            param_grid=search_spaces,
            cv=cv,
            scoring=scoring,
            refit=True,
            n_jobs=n_jobs,
        )
    else:
        raise ValueError(f"Unsupported tuning strategy: {strategy}")


def tune_on_training_set(
    estimator: Any,
    algorithm: str,
    x_train: Any,
    y_train: Any,
) -> GridSearchCV | RandomizedSearchCV:
    """Fit a cross-validated search on the training set only."""
    search = build_search_cv(estimator, algorithm)
    search.fit(x_train, y_train)
    return search
