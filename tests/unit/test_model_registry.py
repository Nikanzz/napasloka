"""Unit tests for Model Registry, configuration, and caching mechanisms."""

import pytest
from backend.app.core.cache import MemoryCache, model_cache, predictions_cache
from backend.app.core.config import settings
from backend.app.services.registry_service import registry_service


def test_locations_configuration():
    """Verify all 15 Jabodetabek locations are configured with coordinates and regions."""
    locations = settings.get_locations()
    assert len(locations) == 15
    for loc in locations:
        assert "id" in loc
        assert "name" in loc
        assert "region" in loc
        assert "latitude" in loc
        assert "longitude" in loc
        assert -7.0 <= loc["latitude"] <= -5.0  # Jabodetabek latitude range
        assert 106.0 <= loc["longitude"] <= 108.0  # Jabodetabek longitude range


def test_dimension_validation():
    """Ensure dimension validation accepts valid values and rejects invalid combinations."""
    # Valid call should not raise
    registry_service.validate_dimensions("taman-kamal", "co", "scenario_1", "xgboost")

    # Invalid location
    with pytest.raises(ValueError, match="Unknown location"):
        registry_service.validate_dimensions("bandung", "co", "scenario_1", "xgboost")

    # Invalid pollutant
    with pytest.raises(ValueError, match="Unknown pollutant"):
        registry_service.validate_dimensions("taman-kamal", "so2", "scenario_1", "xgboost")

    # Invalid scenario
    with pytest.raises(ValueError, match="Unknown scenario"):
        registry_service.validate_dimensions("taman-kamal", "co", "scenario_3", "xgboost")

    # Invalid algorithm
    with pytest.raises(ValueError, match="Unknown algorithm"):
        registry_service.validate_dimensions("taman-kamal", "co", "scenario_1", "random_forest")


def test_all_120_models_are_present_and_ready():
    """Verify that all 120 experiment combinations exist on disk with complete artifacts."""
    summary = registry_service.get_all_models_summary()
    assert summary["total_experiments"] == 120
    assert summary["completed_experiments"] == 120
    assert summary["ready_ratio"] == 100.0


def test_counterpart_model_pairing():
    """Verify XGBoost and LightGBM are correctly paired as counterpart baselines."""
    # XGBoost -> LightGBM counterpart
    counterpart_xgb = registry_service.get_counterpart_info(
        "taman-kamal", "co", "scenario_1", "xgboost"
    )
    assert counterpart_xgb is not None
    assert counterpart_xgb.algorithm == "lightgbm"
    assert counterpart_xgb.metrics.mae > 0
    assert counterpart_xgb.metrics.r2 > 0

    # LightGBM -> XGBoost counterpart
    counterpart_lgb = registry_service.get_counterpart_info(
        "taman-kamal", "co", "scenario_1", "lightgbm"
    )
    assert counterpart_lgb is not None
    assert counterpart_lgb.algorithm == "xgboost"
    assert counterpart_lgb.metrics.mae > 0
    assert counterpart_lgb.metrics.r2 > 0


def test_model_loading_and_caching():
    """Verify model estimator can be loaded and is cached in memory for zero-disk subsequent reads."""
    model_cache.clear()
    assert model_cache.stats()["size"] == 0

    # First load - reads from disk
    model1 = registry_service.load_estimator("taman-kamal", "co", "scenario_1", "xgboost")
    assert model1 is not None
    assert model_cache.stats()["size"] == 1

    # Second load - hits cache, returns identical object in memory
    model2 = registry_service.load_estimator("taman-kamal", "co", "scenario_1", "xgboost")
    assert model1 is model2
    assert model_cache.stats()["hits"] >= 1


def test_predictions_csv_loading_and_caching():
    """Verify test predictions DataFrame is parsed properly with datetime column and cached."""
    predictions_cache.clear()
    assert predictions_cache.stats()["size"] == 0

    df1 = registry_service.load_test_predictions("taman-kamal", "co", "scenario_1", "xgboost")
    assert not df1.empty
    assert "datetime" in df1.columns
    assert "actual" in df1.columns
    assert "predicted" in df1.columns
    assert "residual" in df1.columns
    assert len(df1) > 1000

    # Second load - hits cache
    df2 = registry_service.load_test_predictions("taman-kamal", "co", "scenario_1", "xgboost")
    assert df1 is df2
    assert predictions_cache.stats()["hits"] >= 1


def test_memory_cache_lru_behavior():
    """Verify LRU cache limits size and evicts oldest items."""
    cache = MemoryCache(maxsize=3)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.stats()["size"] == 3

    # Adding a 4th item should evict "a"
    cache.set("d", 4)
    assert cache.stats()["size"] == 3
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4
