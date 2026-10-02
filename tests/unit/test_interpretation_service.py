"""Unit tests for InterpretationService (local TreeSHAP and global importance)."""

import pytest
from backend.app.schemas.interpretation import InterpretationRequest
from backend.app.services.interpretation_service import interpretation_service


def test_interpret_prediction_co_scenario_1_xgboost() -> None:
    """Verify local TreeSHAP and global importance for CO Scenario 1 with XGBoost."""
    req = InterpretationRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
    )
    res = interpretation_service.interpret_prediction(req)

    assert res.experiment_id == "taman-kamal__co__scenario_1__xgboost"
    assert res.location == "taman-kamal"
    assert res.pollutant == "co"
    assert res.pollutant_unit == "µg/m³"
    assert res.predicted_value > 0
    assert res.base_value > 0

    # Local SHAP decomposition (Scenario 1 has 3 features)
    assert len(res.local_contributions) == 3
    assert res.top_contributor is not None
    assert res.top_contributor.impact_magnitude > 0
    assert res.top_contributor.direction in ("positive", "negative")

    # Additivity verification: base_value + sum(shap) ~= predicted_value
    sum_shap = sum(c.shap_value for c in res.local_contributions)
    assert abs((res.base_value + sum_shap) - res.predicted_value) < 1.0

    # Chart series
    assert "features" in res.chart_series
    assert "values" in res.chart_series
    assert "colors" in res.chart_series
    assert len(res.chart_series["features"]) == 3

    # Global importance
    assert len(res.global_importance) == 3
    assert res.global_importance[0].gain_importance > 0

    # Scientific disclaimer
    assert "BUKAN merupakan bukti hubungan kausalitas" in res.scientific_disclaimer


def test_interpret_prediction_co2_scenario_2_lightgbm() -> None:
    """Verify local TreeSHAP for CO2 Scenario 2 with LightGBM (15 features)."""
    req = InterpretationRequest(
        location="cibinong",
        pollutant="co2",
        scenario="scenario_2",
        algorithm="lightgbm",
        top_k=5,
    )
    res = interpretation_service.interpret_prediction(req)

    assert res.algorithm == "lightgbm"
    assert res.pollutant == "co2"
    assert res.pollutant_unit == "ppm"

    # All 15 local contributions
    assert len(res.local_contributions) == 15

    # Top-K chart series limited to 5
    assert len(res.chart_series["features"]) == 5

    # Meteorological features present in contributions
    feature_names = [c.feature_name for c in res.local_contributions]
    assert any("temperature" in name for name in feature_names)
    assert any("wind_speed" in name for name in feature_names)


def test_interpret_with_reference_time() -> None:
    """Verify interpretation on historical reference point."""
    req = InterpretationRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
        reference_datetime="2026-04-10T12:00:00+07:00",
    )
    res = interpretation_service.interpret_prediction(req)
    assert "2026-04-10T13:00:00" in res.target_time


def test_interpret_invalid_location_raises() -> None:
    """Verify ValueError is raised on invalid location."""
    req = InterpretationRequest(
        location="invalid-loc",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
    )
    with pytest.raises(ValueError, match="Unknown location"):
        interpretation_service.interpret_prediction(req)
