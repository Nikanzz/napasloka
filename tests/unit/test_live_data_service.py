import pytest
import pandas as pd
from backend.app.services.live_data_service import live_data_service, _LIVE_CACHE, _get_current_wib_hour


def test_build_live_features_unknown_location_raises():
    with pytest.raises(ValueError, match="Unknown location"):
        live_data_service.build_live_features("unknown-location", "co", "scenario_1")


def test_build_live_features_co_scenario_1():
    X_df, meta = live_data_service.build_live_features("taman-kamal", "co", "scenario_1")
    assert isinstance(X_df, pd.DataFrame)
    assert len(X_df) == 1
    assert "carbon_monoxide_lag_1h" in X_df.columns
    assert "carbon_monoxide_lag_2h" in X_df.columns
    assert "carbon_monoxide_lag_3h" in X_df.columns
    assert "latest_observation_time" in meta
    assert "target_prediction_time" in meta


def test_build_live_features_co2_scenario_2():
    X_df, meta = live_data_service.build_live_features("cibinong", "co2", "scenario_2")
    assert isinstance(X_df, pd.DataFrame)
    assert len(X_df) == 1
    assert len(X_df.columns) == 15
    assert "temperature_2m_lag_1h" in X_df.columns
    assert "carbon_dioxide_lag_1h" in X_df.columns


def test_live_cache_key_generation():
    hour_str = _get_current_wib_hour()
    assert len(hour_str) == 13
    assert hour_str.count("-") == 3
