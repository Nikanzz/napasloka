"""Model interpretation and Explainable AI (XAI): Gain Feature Importance and TreeSHAP."""

import numpy as np
import pandas as pd
import shap


def gain_feature_importance(model, feature_names, normalize=True):
    """Calculate gain feature importance, sorted in descending order."""
    if hasattr(model, "get_booster"):
        raw = model.get_booster().get_score(importance_type="total_gain")
        values = np.array(
            [float(raw.get(name, raw.get(f"f{index}", 0.0))) for index, name in enumerate(feature_names)],
            dtype=float,
        )
    elif hasattr(model, "booster_"):
        values = np.array(
            [float(value) for value in model.booster_.feature_importance(importance_type="gain")],
            dtype=float,
        )
    elif hasattr(model, "feature_importances_"):
        values = np.array(model.feature_importances_, dtype=float)
    else:
        raise TypeError("Model does not expose supported gain importance")

    if normalize and values.sum() > 0:
        values = values / values.sum()

    df = pd.DataFrame({"feature": feature_names, "importance": values})
    return df.sort_values(by="importance", ascending=False).reset_index(drop=True)


def calculate_tree_shap(model, features):
    """Calculate TreeSHAP values for tree-based models."""
    explainer = shap.TreeExplainer(model)
    return explainer.shap_values(features)


def mean_absolute_shap(shap_values, feature_names):
    """Aggregate global feature importance as mean absolute SHAP."""
    mean_abs_shap = np.abs(shap_values).mean(axis=0)

    df_importance = pd.DataFrame({
        "feature": feature_names,
        "mean_absolute_shap": mean_abs_shap,
    })

    return df_importance.sort_values(by="mean_absolute_shap", ascending=False).reset_index(drop=True)
