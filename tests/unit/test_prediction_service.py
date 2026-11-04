"""Unit tests for next-hour prediction service."""

import pytest
from backend.app.schemas.prediction import PredictionRequest
from backend.app.services.prediction_service import prediction_service


def test_predict_next_hour_co_scenario_1():
    """Verify next-hour prediction for CO Scenario 1 with XGBoost."""
    req = PredictionRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
    )
    res = prediction_service.predict_next_hour(req)

    assert res.experiment_id == "taman-kamal__co__scenario_1__xgboost"
    assert res.location == "taman-kamal"
    assert res.location_name == "Taman Kamal"
    assert res.region == "Jakarta Barat"
    assert res.pollutant == "co"
    assert res.pollutant_unit == "µg/m³"
    assert res.predicted_value > 0
    assert "WIB" in res.target_time_display
    assert "WIB" in res.latest_observation_display

    # Reference comparison
    assert res.latest_observation_value > 0
    assert res.trend in ("naik", "turun", "stabil")

    # Feature inputs (Scenario 1 has 3 features)
    assert len(res.feature_inputs) == 3
    assert any("lag_1h" in item.name for item in res.feature_inputs)

    # Counterpart comparison (LightGBM)
    assert res.counterpart_algorithm == "lightgbm"
    assert res.counterpart_predicted_value is not None
    assert res.counterpart_predicted_value > 0


def test_predict_next_hour_co2_scenario_2():
    """Verify next-hour prediction for CO2 Scenario 2 with LightGBM (15 features)."""
    req = PredictionRequest(
        location="cibinong",
        pollutant="co2",
        scenario="scenario_2",
        algorithm="lightgbm",
    )
    res = prediction_service.predict_next_hour(req)

    assert res.experiment_id == "cibinong__co2__scenario_2__lightgbm"
    assert res.algorithm == "lightgbm"
    assert res.pollutant == "co2"
    assert res.pollutant_unit == "ppm"
    assert res.predicted_value > 300.0  # CO2 is around 400+ ppm

    # Scenario 2 has 15 features (3 pollutant lags + 12 meteo lags)
    assert len(res.feature_inputs) == 15
    feature_names = [f.name for f in res.feature_inputs]
    assert "temperature_2m_lag_1h" in feature_names
    assert "relative_humidity_2m_lag_1h" in feature_names
    assert "rain_lag_1h" in feature_names
    assert "wind_speed_100m_lag_1h" in feature_names

    # Counterpart comparison (XGBoost)
    assert res.counterpart_algorithm == "xgboost"
    assert res.counterpart_predicted_value is not None


def test_predict_next_hour_with_reference_time():
    """Verify point-forecast can use an explicit historical reference timestamp."""
    req = PredictionRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
        reference_datetime="2026-04-10T12:00:00+07:00",
    )
    res = prediction_service.predict_next_hour(req)
    assert "2026-04-10T12:00:00" in res.latest_observation_time
    assert "2026-04-10T13:00:00" in res.target_time


def test_predict_invalid_location_raises():
    """Verify ValueError is raised on unsupported location."""
    req = PredictionRequest(
        location="unknown-place",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
    )
    with pytest.raises(ValueError, match="Unknown location"):
        prediction_service.predict_next_hour(req)
