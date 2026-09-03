"""LightGBM regression estimator factory."""

from typing import Any


def create_lightgbm_regressor(parameters: dict[str, Any] | None = None) -> Any:
    """Create an LGBMRegressor; parameters come from config or tuning output."""

    from lightgbm import LGBMRegressor

    return LGBMRegressor(**(parameters or {}))
