from datetime import datetime
from pydantic import BaseModel

from backend.app.schemas.registry import ModelMetrics, PollutantType, ScenarioType, AlgorithmType


class EvaluationRequest(BaseModel):
    location: str
    pollutant: PollutantType
    scenario: ScenarioType
    algorithm: AlgorithmType
    start_datetime: datetime | str | None = None
    end_datetime: datetime | str | None = None
    max_chart_points: int | None = 1500


class ComparisonMetrics(BaseModel):
    primary_algorithm: str
    primary_label: str
    primary_metrics: ModelMetrics
    counterpart_algorithm: str
    counterpart_label: str
    counterpart_metrics: ModelMetrics
    mae_diff_pct: float
    rmse_diff_pct: float
    mape_diff: float
    r2_diff: float
    winner: str
    summary: str


class EvaluationChartSeries(BaseModel):
    timestamps: list[str]
    actual: list[float]
    predicted: list[float]
    counterpart_predicted: list[float] | None = None
    residual: list[float]


class EvaluationTimeRange(BaseModel):
    start: str
    end: str
    dataset_start: str
    dataset_end: str
    total_test_samples: int
    evaluated_samples: int


class EvaluationResponse(BaseModel):
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
