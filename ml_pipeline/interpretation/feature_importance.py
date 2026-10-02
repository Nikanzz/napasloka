"""Gain-based feature importance baseline.

Gain importance is a model-native baseline interpretation. It is not a
validation of SHAP values and must not be presented as one.
"""

from typing import Any

import numpy as np
import pandas as pd


def gain_feature_importance(
    model: Any,
    feature_names: list[str],
    *,
    normalize: bool = True,
) -> pd.DataFrame:
    """Return gain importance in a common two-column representation, sorted descending."""

    if hasattr(model, "get_booster"):
        raw = model.get_booster().get_score(importance_type="total_gain")
        values = np.array([float(raw.get(name, raw.get(f"f{index}", 0.0))) for index, name in enumerate(feature_names)], dtype=float)
    elif hasattr(model, "booster_"):
        values = np.array([float(value) for value in model.booster_.feature_importance(importance_type="gain")], dtype=float)
    elif hasattr(model, "feature_importances_"):
        values = np.array(model.feature_importances_, dtype=float)
    else:
        raise TypeError("Model does not expose supported gain importance")

    if normalize and values.sum() > 0:
        values = values / values.sum()

    df = pd.DataFrame({"feature": feature_names, "importance": values})
    return df.sort_values(by="importance", ascending=False).reset_index(drop=True)
