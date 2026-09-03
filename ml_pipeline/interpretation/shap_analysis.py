"""Primary TreeSHAP interpretation interface.

Future implementation will calculate local TreeSHAP values and aggregate
global importance as mean absolute SHAP. SHAP describes model behavior and
must never be interpreted as evidence of a causal relationship. SHAP is not
executed during Phase 0.
"""

from typing import Any

import pandas as pd


def calculate_tree_shap(model: Any, features: pd.DataFrame) -> Any:
    """Calculate TreeSHAP values after the research execution phase begins."""

    raise NotImplementedError("SHAP analysis is intentionally disabled in Phase 0")


def mean_absolute_shap(shap_values: Any, feature_names: list[str]) -> pd.DataFrame:
    """Aggregate global importance as mean absolute SHAP in a future phase."""

    raise NotImplementedError("SHAP aggregation is intentionally disabled in Phase 0")
