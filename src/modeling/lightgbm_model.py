"""LightGBM regression estimator factory."""

from typing import Any


def create_lightgbm_regressor(parameters: dict[str, Any] | None = None) -> Any:
    """Create an LGBMRegressor; parameters come from config or tuning output."""

    from lightgbm import LGBMRegressor

    params = {"verbose": -1, "importance_type": "gain"}
    if parameters:
        params.update(parameters)
    return LGBMRegressor(**params)
