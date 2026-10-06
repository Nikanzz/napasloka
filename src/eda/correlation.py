"""Correlation helpers for exploratory—not causal—analysis."""

import pandas as pd


def numeric_correlation(frame: pd.DataFrame, *, method: str = "pearson") -> pd.DataFrame:
    """Return a numeric-column correlation matrix."""

    return frame.select_dtypes(include="number").corr(method=method)
