"""XGBoost regression estimator factory."""

from typing import Any


def create_xgboost_regressor(parameters: dict[str, Any] | None = None) -> Any:
    """Create an XGBRegressor; parameters come from config or tuning output."""

    from xgboost import XGBRegressor

    return XGBRegressor(**(parameters or {}))
