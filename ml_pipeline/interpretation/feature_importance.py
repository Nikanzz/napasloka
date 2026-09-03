"""Gain-based feature importance baseline.

Gain importance is a model-native baseline interpretation. It is not a
validation of SHAP values and must not be presented as one.
"""

from typing import Any

import pandas as pd


def gain_feature_importance(model: Any, feature_names: list[str]) -> pd.DataFrame:
    """Return gain importance in a common two-column representation."""

    if hasattr(model, "get_booster"):
        raw = model.get_booster().get_score(importance_type="gain")
        values = [float(raw.get(name, raw.get(f"f{index}", 0.0))) for index, name in enumerate(feature_names)]
    elif hasattr(model, "booster_"):
        values = [float(value) for value in model.booster_.feature_importance(importance_type="gain")]
    else:
        raise TypeError("Model does not expose supported gain importance")
    return pd.DataFrame({"feature": feature_names, "gain_importance": values})
