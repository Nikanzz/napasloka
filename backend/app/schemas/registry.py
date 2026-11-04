from typing import Any, Literal
from pydantic import BaseModel

PollutantType = Literal["co", "co2"]
ScenarioType = Literal["scenario_1", "scenario_2"]
AlgorithmType = Literal["xgboost", "lightgbm"]


class ModelArtifactStatus(BaseModel):
    model_joblib: bool
    metrics_json: bool
    predictions_csv: bool
    feature_importance_csv: bool
    shap_global_csv: bool
    experiment_metadata_json: bool
    is_ready: bool


class ModelMetrics(BaseModel):
    mae: float
    rmse: float
    mape: float
    r2: float
    training_time_seconds: float | None = None
    prediction_time_seconds: float | None = None


class CounterpartModelInfo(BaseModel):
    algorithm: AlgorithmType
    algorithm_label: str
    experiment_id: str
    metrics: ModelMetrics
    is_available: bool


class ModelDetailResponse(BaseModel):
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
    features: list[str]
    best_params: dict[str, Any]
    metrics: ModelMetrics
    counterpart: CounterpartModelInfo | None = None
    artifact_status: ModelArtifactStatus
