"""Unit and integration tests for the Best Model Registry and Final Deployment Models."""

import json
from pathlib import Path
import pytest

from backend.app.core.config import settings
from backend.app.schemas.prediction import PredictionRequest
from backend.app.schemas.interpretation import InterpretationRequest
from backend.app.schemas.evaluation import EvaluationRequest
from backend.app.services.registry_service import registry_service
from backend.app.services.prediction_service import prediction_service
from backend.app.services.interpretation_service import interpretation_service
from backend.app.services.evaluation_service import evaluation_service


def test_best_models_registry_completeness():
    """Verify that best_models.json contains exactly 60 entries (15 locations x 2 pollutants x 2 scenarios)."""
    registry_file = settings.best_models_file
    assert registry_file.is_file(), f"Best models file missing: {registry_file}"

    with open(registry_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("total_combinations") == 60
    best_models = data.get("best_models", {})
    assert len(best_models) == 60

    locations = [loc["id"] for loc in settings.get_locations()]
    pollutants = ["co", "co2"]
    scenarios = ["scenario_1", "scenario_2"]

    for loc in locations:
        for pol in pollutants:
            for scen in scenarios:
                key = f"{loc}__{pol}__{scen}"
                assert key in best_models, f"Missing combination: {key}"
                entry = best_models[key]
                assert entry["best_algorithm"] in ["lightgbm", "xgboost"]
                assert "mae" in entry["metrics"]
                assert "best_params" in entry


def test_final_models_presence_and_loading():
    """Verify that all 60 final deployment models exist on disk and can be loaded."""
    registry = registry_service.get_all_best_models()
    best_models = registry.get("best_models", {})

    # Check a representative sample across locations and pollutants
    sample_keys = [
        "cibinong__co__scenario_1",
        "daerah-pelabuhan-tanjung-priuk__co2__scenario_2",
        "taman-kamal__co__scenario_2",
        "smpn-92-jakarta-timur__co2__scenario_1",
        "tol-serpong-interchange__co__scenario_1",
    ]

    for key in sample_keys:
        entry = best_models[key]
        loc = entry["location"]
        pol = entry["pollutant"]
        scen = entry["scenario"]

        final_dir = settings.final_models_dir / loc / pol / scen
        assert (final_dir / "model.joblib").is_file(), f"Final model missing at: {final_dir}"
        assert (final_dir / "final_metadata.json").is_file(), f"Metadata missing at: {final_dir}"

        # Test estimator loading
        estimator = registry_service.load_final_estimator(loc, pol, scen)
        assert estimator is not None
        assert hasattr(estimator, "predict")

        # Test metadata loading
        meta = registry_service.get_final_metadata(loc, pol, scen)
        assert meta["model_status"] == "final_deployment"
        assert meta["algorithm"] == entry["best_algorithm"]


def test_prediction_uses_final_deployment_model():
    """Verify that next-hour prediction defaults to final deployment model."""
    req = PredictionRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_2",
        algorithm="auto",
    )
    resp = prediction_service.predict_next_hour(req)
    assert resp.is_final_model is True
    assert resp.model_status == "Final deployment model"
    assert resp.algorithm == resp.best_algorithm
    assert resp.predicted_value > 0


def test_interpretation_uses_final_deployment_model():
    """Verify that local TreeSHAP interpretation uses the retrained final deployment model."""
    req = InterpretationRequest(
        location="cibinong",
        pollutant="co2",
        scenario="scenario_2",
        algorithm="auto",
        top_k=5,
    )
    resp = interpretation_service.interpret_prediction(req)
    assert resp.is_final_model is True
    assert resp.model_status == "Final deployment model"
    assert resp.algorithm == resp.best_algorithm
    assert len(resp.chart_series["features"]) == 5
    assert len(resp.local_contributions) == 15
    assert resp.top_contributor is not None


def test_evaluation_retains_comparison_and_flags_best_model():
    """Verify that Evaluation page compares XGBoost vs LightGBM and flags the winning algorithm."""
    req = EvaluationRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_1",
        algorithm="lightgbm",
    )
    resp = evaluation_service.evaluate_test_range(req)
    assert resp.comparison is not None
    assert resp.comparison.counterpart_algorithm == "xgboost"
    assert resp.best_model_algorithm == "lightgbm"
    assert resp.is_best_model is True

