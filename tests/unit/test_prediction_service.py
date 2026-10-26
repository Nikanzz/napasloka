"""Unit tests for next-hour prediction service and air quality assessment."""

import pytest
from backend.app.schemas.prediction import PredictionRequest
from backend.app.services.prediction_service import assess_air_quality, prediction_service


def test_assess_air_quality_co():
    """Verify ISPU air quality assessment categories for Carbon Monoxide."""
    # Baik (<= 4000)
    a1 = assess_air_quality("co", 1500.0)
    assert a1.category == "Baik"
    assert a1.color == "#10b981"

    # Sedang (4001 - 8000)
    a2 = assess_air_quality("co", 6000.0)
    assert a2.category == "Sedang"
    assert a2.color == "#f59e0b"

    # Tidak Sehat (8001 - 15000)
    a3 = assess_air_quality("co", 10000.0)
    assert a3.category == "Tidak Sehat"

    # Sangat Tidak Sehat (15001 - 30000)
    a4 = assess_air_quality("co", 20000.0)
    assert a4.category == "Sangat Tidak Sehat"

    # Berbahaya (> 30000)
    a5 = assess_air_quality("co", 35000.0)
    assert a5.category == "Berbahaya"


def test_assess_air_quality_co2():
    """Verify ambient tropospheric assessment for Carbon Dioxide."""
    # Normal (< 450 ppm)
    a1 = assess_air_quality("co2", 420.0)
    assert a1.category == "Normal Ambien"

    # Terakumulasi sedang (450 - 600 ppm)
    a2 = assess_air_quality("co2", 520.0)
    assert a2.category == "Terakumulasi Sedang"

    # Tinggi (> 600 ppm)
    a3 = assess_air_quality("co2", 650.0)
    assert a3.category == "Tinggi"


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
    assert res.assessment.category in ("Baik", "Sedang", "Tidak Sehat", "Sangat Tidak Sehat", "Berbahaya")

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
