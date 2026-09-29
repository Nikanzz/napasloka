"""Primary TreeSHAP interpretation interface.

Future implementation will calculate local TreeSHAP values and aggregate
global importance as mean absolute SHAP. SHAP describes model behavior and
must never be interpreted as evidence of a causal relationship. SHAP is not
executed during Phase 0.
"""

from typing import Any

import sys
import importlib.machinery
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

# Mock matplotlib to prevent shap from importing it in headless environments
sys.meta_path.insert(0, MatplotlibMockImporter())

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
