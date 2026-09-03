"""Feature schema invariants."""

from ml_pipeline.features.scenarios import get_feature_names


def test_scenario_1_has_three_features() -> None:
    assert len(get_feature_names("co", "scenario_1")) == 3


def test_scenario_2_has_fifteen_features() -> None:
    assert len(get_feature_names("co2", "scenario_2")) == 15
