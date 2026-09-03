"""Training-set-only Grid Search with TimeSeriesSplit.

Tuning is disabled in Phase 0. Search spaces must be finalized after the
proposal seminar before this module is invoked.
"""

from typing import Any

from sklearn.model_selection import GridSearchCV, TimeSeriesSplit

from ml_pipeline.utils.config import load_yaml_config


def build_grid_search(estimator: Any, algorithm: str) -> GridSearchCV:
    """Build a search object from config, refusing disabled or empty searches."""

    config = load_yaml_config("tuning.yaml")
    if not config.get("enabled", False):
        raise RuntimeError("Hyperparameter tuning is disabled in configs/tuning.yaml")
    parameter_grid = config.get("search_spaces", {}).get(algorithm, {})
    if not parameter_grid:
        raise ValueError(f"Search space has not been finalized for {algorithm}")
    n_splits = config.get("cross_validation", {}).get("n_splits")
    if not isinstance(n_splits, int) or n_splits < 2:
        raise ValueError("TimeSeriesSplit n_splits must be finalized before tuning")
    return GridSearchCV(
        estimator=estimator,
        param_grid=parameter_grid,
        cv=TimeSeriesSplit(n_splits=n_splits),
        scoring="neg_mean_absolute_error",
        refit=True,
    )


def tune_on_training_set(
    estimator: Any,
    algorithm: str,
    x_train: Any,
    y_train: Any,
) -> GridSearchCV:
    """Fit Grid Search only to explicitly supplied training data."""

    search = build_grid_search(estimator, algorithm)
    search.fit(x_train, y_train)
    return search
