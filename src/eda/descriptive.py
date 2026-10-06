"""Descriptive statistics for documented exploratory analysis."""

import pandas as pd


def describe_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    """Return standard descriptive statistics for numeric columns."""

    return frame.select_dtypes(include="number").describe().transpose()
