"""Deterministic preprocessing that does not impute, scale, or remove outliers."""

import pandas as pd


def standardize_datetime(
    frame: pd.DataFrame,
    *,
    timezone: str = "Asia/Jakarta",
    datetime_column: str = "datetime",
) -> pd.DataFrame:
    """Parse timestamps, localize naive values, and convert aware values."""

    if datetime_column not in frame:
        raise ValueError(f"Missing datetime column: {datetime_column}")
    result = frame.copy()
    parsed = pd.to_datetime(result[datetime_column], errors="raise")
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(timezone, ambiguous="raise", nonexistent="raise")
    else:
        parsed = parsed.dt.tz_convert(timezone)
    result[datetime_column] = parsed
    return result


def sort_chronologically(
    frame: pd.DataFrame,
    *,
    datetime_column: str = "datetime",
) -> pd.DataFrame:
    """Sort by location and time without modifying source data in place."""

    columns = [datetime_column]
    if "location" in frame:
        columns.insert(0, "location")
    return frame.sort_values(columns, kind="stable").reset_index(drop=True)


def preprocess_frame(frame: pd.DataFrame, *, timezone: str = "Asia/Jakarta") -> pd.DataFrame:
    """Apply only timezone standardization and chronological ordering."""

    return sort_chronologically(standardize_datetime(frame, timezone=timezone))


def chronological_train_test_split(
    frame: pd.DataFrame,
    *,
    test_fraction: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split an already chronological frame without shuffling."""

    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    split_index = int(len(frame) * (1 - test_fraction))
    if split_index == 0 or split_index == len(frame):
        raise ValueError("Dataset is too small for the requested split")
    return frame.iloc[:split_index].copy(), frame.iloc[split_index:].copy()
