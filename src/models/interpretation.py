"""Model interpretation and Explainable AI (XAI): Gain Feature Importance and TreeSHAP."""

import importlib.machinery
import sys
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd


# ==============================================================================
# Windows SAC (Smart App Control) Protection & Matplotlib Isolation for SHAP
# ==============================================================================

class MockModule(MagicMock):
    __path__ = []
    __version__ = "3.9.0"


class MatplotlibMockImporter:
    """Mock importer to catch all matplotlib submodule imports dynamically."""

    def find_spec(self, fullname, path, target=None):
        if fullname == "matplotlib" or fullname.startswith("matplotlib."):

            class MockLoader:

                def create_module(self, spec):
                    return MockModule(name=fullname)

                def exec_module(self, module):
                    pass

            return importlib.machinery.ModuleSpec(fullname, MockLoader())
        return None


if not any(isinstance(hook, MatplotlibMockImporter) for hook in sys.meta_path):
    sys.meta_path.insert(0, MatplotlibMockImporter())

# Prevent Windows Smart App Control (SAC) from blocking unused Cython BLAS extensions
if "sklearn.cluster" not in sys.modules:
    m_cluster = ModuleType("sklearn.cluster")
    m_cluster.KMeans = object
    sys.modules["sklearn.cluster"] = m_cluster

if "sklearn.impute" not in sys.modules:
    m_impute = ModuleType("sklearn.impute")
    m_impute.SimpleImputer = object
    sys.modules["sklearn.impute"] = m_impute

if "shap.explainers.other._maple" not in sys.modules:
    m_maple = ModuleType("shap.explainers.other._maple")
    m_maple.Maple = object
    m_maple.TreeMaple = object
    sys.modules["shap.explainers.other._maple"] = m_maple

if "shap.explainers._kernel" not in sys.modules:
    m_kernel = ModuleType("shap.explainers._kernel")
    m_kernel.KernelExplainer = object
    sys.modules["shap.explainers._kernel"] = m_kernel

if "shap.explainers._linear" not in sys.modules:
    m_linear = ModuleType("shap.explainers._linear")
    m_linear.LinearExplainer = object
    sys.modules["shap.explainers._linear"] = m_linear

import shap


# ==============================================================================
# Feature Importance & SHAP Analysis Functions
# ==============================================================================

def gain_feature_importance(
    model: Any,
    feature_names: list[str],
    *,
    normalize: bool = True,
) -> pd.DataFrame:
    """Return gain importance in a common two-column representation, sorted descending."""
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


def calculate_tree_shap(model: Any, features: pd.DataFrame) -> Any:
    """Calculate TreeSHAP values for the given tree-based model."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(features)
    return shap_values


def mean_absolute_shap(shap_values: Any, feature_names: list[str]) -> pd.DataFrame:
    """Aggregate global importance as mean absolute SHAP."""
    mean_abs_shap = np.abs(shap_values).mean(axis=0)

    df_importance = pd.DataFrame({
        "feature": feature_names,
        "mean_absolute_shap": mean_abs_shap,
    })

    df_importance = df_importance.sort_values(by="mean_absolute_shap", ascending=False).reset_index(drop=True)
    return df_importance
