"""Create leakage-safe lag features after preprocessing and integration."""

import pandas as pd

from src.features.scenarios import resolve_scenario
from src.utils.config import load_yaml_config


def create_lag_features(frame, pollutant, scenario, drop_incomplete_rows=True):
    """Create configured lags, grouped by location when that column is present."""
    definition = resolve_scenario(pollutant, scenario)
    config = load_yaml_config("features.yaml")
    lags = [int(value) for value in config["lag_hours"]]
    variables = [definition.pollutant_column]
    if config["scenarios"][scenario]["include_meteorological_lags"]:
        variables.extend(config["meteorological_variables"])

    missing = sorted(set(variables).difference(frame.columns))
    if missing:
        raise ValueError(f"Missing columns required for lag features: {missing}")

    result = frame.copy()
    grouped = result.groupby("location", sort=False) if "location" in result else None
    for variable in variables:
        for lag in lags:
            source = grouped[variable] if grouped is not None else result[variable]
            result[f"{variable}_lag_{lag}h"] = source.shift(lag)

    if drop_incomplete_rows:
        result = result.dropna(subset=list(definition.feature_names)).reset_index(drop=True)
    return result
