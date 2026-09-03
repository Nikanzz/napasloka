"""Resolve feature names from the single schema in ``configs/features.yaml``."""

from dataclasses import dataclass

from ml_pipeline.utils.config import load_yaml_config


POLLUTANT_COLUMNS = {
    "co": "carbon_monoxide",
    "co2": "carbon_dioxide",
    "carbon_monoxide": "carbon_monoxide",
    "carbon_dioxide": "carbon_dioxide",
}


@dataclass(frozen=True)
class ScenarioDefinition:
    """Resolved feature contract for one scenario and pollutant."""

    name: str
    pollutant_column: str
    feature_names: tuple[str, ...]
    forecast_horizon_hours: int


def _lag_name(variable: str, hours: int) -> str:
    return f"{variable}_lag_{hours}h"


def resolve_scenario(pollutant: str, scenario: str) -> ScenarioDefinition:
    """Resolve a concrete scenario without duplicating feature definitions."""

    try:
        pollutant_column = POLLUTANT_COLUMNS[pollutant.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported pollutant: {pollutant}") from exc

    config = load_yaml_config("features.yaml")
    scenarios = config.get("scenarios", {})
    if scenario not in scenarios:
        raise ValueError(f"Unsupported scenario: {scenario}")

    scenario_config = scenarios[scenario]
    lag_hours = tuple(int(value) for value in config["lag_hours"])
    variables: list[str] = []
    if scenario_config.get("include_pollutant_lags"):
        variables.append(pollutant_column)
    if scenario_config.get("include_meteorological_lags"):
        variables.extend(config["meteorological_variables"])

    feature_names = tuple(
        _lag_name(variable, lag) for variable in variables for lag in lag_hours
    )
    return ScenarioDefinition(
        name=scenario,
        pollutant_column=pollutant_column,
        feature_names=feature_names,
        forecast_horizon_hours=int(config["forecast_horizon_hours"]),
    )


def get_feature_names(pollutant: str, scenario: str) -> list[str]:
    """Return ordered concrete feature names for an experiment."""

    return list(resolve_scenario(pollutant, scenario).feature_names)
