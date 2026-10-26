"""Estimator factories, timed fitting, tuning, and prediction for XGBoost and LightGBM."""

import time
import numpy as np
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, TimeSeriesSplit

from src.utils.config import load_yaml_config


# ==============================================================================
# Model Factories
# ==============================================================================

def create_xgboost_regressor(parameters=None):
    """Create an XGBRegressor with specified or default parameters."""
    from xgboost import XGBRegressor

    return XGBRegressor(**(parameters or {}))


def create_lightgbm_regressor(parameters=None):
    """Create an LGBMRegressor with specified or default parameters."""
    from lightgbm import LGBMRegressor

    params = {"verbose": -1, "importance_type": "gain"}
    if parameters:
        params.update(parameters)
    return LGBMRegressor(**params)


def create_estimator(algorithm, parameters=None):
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

class TrainingResult:
    """Fitted estimator and measured training duration in seconds."""

    def __init__(self, model, training_time_seconds):
        self.model = model
        self.training_time_seconds = training_time_seconds

    def __getitem__(self, item):
        return getattr(self, item)


def train_model(model, x_train, y_train):
    """Fit an estimator and measure elapsed training time."""
    start = time.time()
    model.fit(x_train, y_train)
    elapsed = time.time() - start
    return TrainingResult(model, elapsed)


class PredictionResult:
    """Predictions array and measured inference duration in seconds."""

    def __init__(self, values, prediction_time_seconds):
        self.values = values
        self.prediction_time_seconds = prediction_time_seconds

    def __getitem__(self, item):
        return getattr(self, item)


def predict(model, x_test):
    """Generate predictions and measure elapsed inference time."""
    start = time.time()
    values = np.asarray(model.predict(x_test))
    elapsed = time.time() - start
    return PredictionResult(values, elapsed)


# ==============================================================================
# Hyperparameter Tuning with TimeSeriesSplit
# ==============================================================================

def build_search_cv(estimator, algorithm):
    """Build a search object from config, supporting randomized and grid search."""
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


def tune_on_training_set(estimator, algorithm, x_train, y_train):
    """Fit a cross-validated search on the training set only."""
    search = build_search_cv(estimator, algorithm)
    search.fit(x_train, y_train)
    return search
