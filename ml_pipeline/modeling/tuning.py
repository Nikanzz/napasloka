"""Training-set-only Hyperparameter Tuning with TimeSeriesSplit."""

from typing import Any

from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, TimeSeriesSplit

from ml_pipeline.utils.config import load_yaml_config


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
    """Fit hyperparameter search only to explicitly supplied training data."""

    search = build_search_cv(estimator, algorithm)
    search.fit(x_train, y_train)
    return search
