"""Pydantic schemas for test dataset evaluation and model comparison."""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

from backend.app.schemas.registry import ModelMetrics, PollutantType, ScenarioType, AlgorithmType


class EvaluationRequest(BaseModel):
    """Request payload for slicing test set evaluation data."""

    location: str = Field(..., min_length=1, description="Location slug identifier")
    pollutant: PollutantType = Field(..., description="Target pollutant ('co' or 'co2')")
    scenario: ScenarioType = Field(..., description="Scenario identifier ('scenario_1' or 'scenario_2')")
    algorithm: AlgorithmType = Field(..., description="Selected algorithm ('xgboost' or 'lightgbm')")
    start_datetime: datetime | str | None = Field(
        default=None,
        description="Filter range start ISO timestamp (e.g. '2026-04-01T00:00:00+07:00')",
    )
    end_datetime: datetime | str | None = Field(
        default=None,
        description="Filter range end ISO timestamp (e.g. '2026-05-01T00:00:00+07:00')",
    )
    max_chart_points: int | None = Field(
        default=1500,
        description="Maximum data points returned for charting to optimize transmission (None for all points)",
    )


class ComparisonMetrics(BaseModel):
    """Comparative evaluation metrics between primary and counterpart algorithms."""

    primary_algorithm: str
    primary_label: str
    primary_metrics: ModelMetrics
    counterpart_algorithm: str
    counterpart_label: str
    counterpart_metrics: ModelMetrics
    mae_diff_pct: float = Field(..., description="Percentage improvement in MAE (positive = primary is better)")
    rmse_diff_pct: float = Field(..., description="Percentage improvement in RMSE (positive = primary is better)")
    mape_diff: float = Field(..., description="Absolute point difference in MAPE (positive = primary is lower error)")
    r2_diff: float = Field(..., description="Absolute difference in R2 (positive = primary is higher)")
    winner: str = Field(..., description="Algorithm with lower MAE ('xgboost' or 'lightgbm')")
    summary: str = Field(..., description="Indonesian narrative summarizing comparative model performance")


class EvaluationChartSeries(BaseModel):
    """Time-series data arrays formatted for Plotly.js visualization."""

    timestamps: list[str]
    actual: list[float]
    predicted: list[float]
    counterpart_predicted: list[float] | None = None
    residual: list[float]


class EvaluationTimeRange(BaseModel):
    """Temporal coverage information for the evaluation dataset."""

    start: str
    end: str
    dataset_start: str
    dataset_end: str
    total_test_samples: int
    evaluated_samples: int


class EvaluationResponse(BaseModel):
    """Complete evaluation report with sliced metrics, comparison, and chart series."""

    experiment_id: str
    location: str
    location_name: str
    region: str
    pollutant: PollutantType
    pollutant_label: str
    pollutant_unit: str
    scenario: ScenarioType
    scenario_label: str
    algorithm: AlgorithmType
    algorithm_label: str
    time_range: EvaluationTimeRange
    metrics: ModelMetrics
    comparison: ComparisonMetrics | None = None
    chart_data: EvaluationChartSeries
    best_model_algorithm: str | None = None
    best_model_label: str | None = None
    is_best_model: bool = False

