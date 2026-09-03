"""Experiment identifier determinism."""

from ml_pipeline.utils.identifiers import build_experiment_id


def test_experiment_id_is_deterministic() -> None:
    first = build_experiment_id("UNTAR", "co", "scenario_1", "xgboost")
    second = build_experiment_id(" untar ", "co", "scenario_1", "xgboost")
    assert first == second == "untar__co__scenario_1__xgboost"
