from src.utils.config import load_yaml_config

class ScenarioDefinition:
    """Resolved feature contract for one scenario and pollutant."""

    def __init__(self, name, pollutant_column, variables, lag_hours, feature_names, forecast_horizon_hours):
        self.name = name
        self.pollutant_column = pollutant_column
        self.variables = tuple(variables)
        self.lag_hours = tuple(lag_hours)
        self.feature_names = tuple(feature_names)
        self.forecast_horizon_hours = forecast_horizon_hours

    def __getitem__(self, item):
        return getattr(self, item)


def _lag_name(variable, hours):
    return f"{variable}_lag_{hours}h"


def resolve_scenario(pollutant, scenario):
    """Resolve a concrete scenario without duplicating feature definitions."""
    p = pollutant.lower()
    if p in ("co", "carbon_monoxide"):
        pollutant_column = "carbon_monoxide"
    elif p in ("co2", "carbon_dioxide"):
        pollutant_column = "carbon_dioxide"
    else:
        raise ValueError(f"Unsupported pollutant: {pollutant}")

    config = load_yaml_config("features.yaml")
    scenarios = config.get("scenarios", {})
    if scenario not in scenarios:
        raise ValueError(f"Unsupported scenario: {scenario}")

    scenario_config = scenarios[scenario]
    lag_hours = tuple(int(value) for value in config["lag_hours"])
    variables = []

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
        variables=variables,
        lag_hours=lag_hours,
        feature_names=feature_names,
        forecast_horizon_hours=int(config["forecast_horizon_hours"]),
    )


def get_feature_names(pollutant, scenario):
    """Return ordered concrete feature names for an experiment."""
    return list(resolve_scenario(pollutant, scenario).feature_names)

