"""Unit tests for EvaluationService: test set slicing, dynamic metrics, and counterpart comparison."""

import pytest
from backend.app.schemas.evaluation import EvaluationRequest
from backend.app.services.evaluation_service import evaluation_service


def test_evaluate_full_test_dataset():
    """Verify evaluating with no date bounds returns all test samples matching offline metrics."""
    req = EvaluationRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
    )
    res = evaluation_service.evaluate_test_range(req)

    assert res.experiment_id == "taman-kamal__co__scenario_1__xgboost"
    assert res.location == "taman-kamal"
    assert res.location_name == "Taman Kamal"
    assert res.region == "Jakarta Barat"
    assert res.pollutant == "co"
    assert res.pollutant_unit == "µg/m³"
    assert res.time_range.evaluated_samples == 3506
    assert res.time_range.total_test_samples == 3506

    # Metrics on full test set should match known metrics
    assert 60.0 <= res.metrics.mae <= 66.0
    assert 90.0 <= res.metrics.rmse <= 100.0
    assert 0.95 <= res.metrics.r2 <= 0.99

    # Comparison with LightGBM counterpart
    assert res.comparison is not None
    assert res.comparison.counterpart_algorithm == "lightgbm"
    assert res.comparison.counterpart_metrics.mae > 0
    assert res.comparison.summary is not None
    assert len(res.comparison.summary) > 20

    # Chart data
    assert len(res.chart_data.timestamps) > 0
    assert len(res.chart_data.actual) == len(res.chart_data.timestamps)
    assert len(res.chart_data.predicted) == len(res.chart_data.timestamps)
    assert res.chart_data.counterpart_predicted is not None
    assert len(res.chart_data.counterpart_predicted) == len(res.chart_data.timestamps)


def test_evaluate_sliced_date_range():
    """Verify slicing a 14-day window dynamically calculates metrics on only those observations."""
    req = EvaluationRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
        start_datetime="2026-07-01T00:00:00+07:00",
        end_datetime="2026-07-14T23:00:00+07:00",
    )
    res = evaluation_service.evaluate_test_range(req)

    # 14 days * 24 hours = 336 hours (+1 endpoint = 337)
    assert 300 <= res.time_range.evaluated_samples <= 350
    assert res.time_range.evaluated_samples < res.time_range.total_test_samples
    assert res.metrics.mae > 0
    assert res.metrics.rmse > 0
    assert res.metrics.r2 > 0

    # Counterpart comparison should also be computed on the same slice
    assert res.comparison is not None
    assert res.comparison.primary_algorithm == "xgboost"
    assert res.comparison.counterpart_algorithm == "lightgbm"


def test_evaluate_lightgbm_as_primary():
    """Verify selecting LightGBM works and pairs with XGBoost as counterpart."""
    req = EvaluationRequest(
        location="cibinong",
        pollutant="co2",
        scenario="scenario_2",
        algorithm="lightgbm",
    )
    res = evaluation_service.evaluate_test_range(req)

    assert res.algorithm == "lightgbm"
    assert res.comparison is not None
    assert res.comparison.primary_algorithm == "lightgbm"
    assert res.comparison.counterpart_algorithm == "xgboost"
    assert res.pollutant_unit == "ppm"


def test_evaluate_downsampling_for_charts():
    """Verify chart series points are downsampled when max_chart_points is smaller than sample count."""
    req = EvaluationRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
        max_chart_points=200,
    )
    res = evaluation_service.evaluate_test_range(req)

    assert res.time_range.evaluated_samples == 3506
    # Chart series downsampled to roughly 200 points
    assert len(res.chart_data.timestamps) <= 250


def test_evaluate_invalid_date_order_raises():
    """Verify ValueError is raised when start_datetime is after end_datetime."""
    req = EvaluationRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
        start_datetime="2026-05-01T00:00:00+07:00",
        end_datetime="2026-04-01T00:00:00+07:00",
    )
    with pytest.raises(ValueError, match="tidak boleh melebihi"):
        evaluation_service.evaluate_test_range(req)


def test_evaluate_empty_range_raises():
    """Verify ValueError is raised when no observations exist in the selected range."""
    req = EvaluationRequest(
        location="taman-kamal",
        pollutant="co",
        scenario="scenario_1",
        algorithm="xgboost",
        start_datetime="2020-01-01T00:00:00+07:00",
        end_datetime="2020-01-10T00:00:00+07:00",
    )
    with pytest.raises(ValueError, match="Tidak ditemukan data uji observasi"):
        evaluation_service.evaluate_test_range(req)
