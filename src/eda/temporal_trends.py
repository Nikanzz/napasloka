"""Time aggregation helpers for EDA plots and reports."""

import pandas as pd


def resample_temporal_mean(
    frame: pd.DataFrame,
    *,
    value_column: str,
    frequency: str = "D",
) -> pd.Series:
    """Aggregate one value column by time using arithmetic mean."""

    if "datetime" not in frame or value_column not in frame:
        raise ValueError("datetime and requested value columns must exist")
    indexed = frame.set_index("datetime")
    return indexed[value_column].resample(frequency).mean()
