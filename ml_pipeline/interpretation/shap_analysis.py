"""Primary TreeSHAP interpretation interface with Windows SAC DLL protection."""

from typing import Any
import sys
from types import ModuleType
from unittest.mock import MagicMock

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

import importlib.machinery
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
import pandas as pd
import numpy as np


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
        "mean_absolute_shap": mean_abs_shap
    })

    df_importance = df_importance.sort_values(by="mean_absolute_shap", ascending=False).reset_index(drop=True)
    return df_importance
