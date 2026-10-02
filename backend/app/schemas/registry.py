"""Pydantic schemas for model registry and metadata representations."""

from typing import Any, Literal
from pydantic import BaseModel, Field


PollutantType = Literal["co", "co2"]
ScenarioType = Literal["scenario_1", "scenario_2"]
AlgorithmType = Literal["xgboost", "lightgbm"]


class ExperimentIdentifier(BaseModel):
    """Four research dimensions identifying one experiment."""

    location: str = Field(..., min_length=1, description="Location slug identifier")
    pollutant: PollutantType = Field(..., description="Target atmospheric pollutant")
    scenario: ScenarioType = Field(..., description="Feature scenario identifier")
    algorithm: AlgorithmType = Field(..., description="Machine learning algorithm")


class ModelArtifactStatus(BaseModel):
    """Presence of artifact files in the experiment directory."""

    model_joblib: bool = Field(..., description="Trained estimator file (model.joblib)")
    metrics_json: bool = Field(..., description="Offline evaluation metrics (metrics.json)")
    predictions_csv: bool = Field(..., description="Test set predictions (predictions.csv)")
    feature_importance_csv: bool = Field(..., description="Gain feature importance")
    shap_global_csv: bool = Field(..., description="Global SHAP values")
    experiment_metadata_json: bool = Field(..., description="Full experiment run metadata")
    is_ready: bool = Field(..., description="Whether all core artifacts are present and ready")


class ModelMetrics(BaseModel):
    """Model evaluation metrics on the test dataset."""

    mae: float = Field(..., description="Mean Absolute Error")
    rmse: float = Field(..., description="Root Mean Squared Error")
    mape: float = Field(..., description="Mean Absolute Percentage Error (%)")
    r2: float = Field(..., description="Coefficient of Determination (R²)")
    training_time_seconds: float | None = Field(default=None, description="Training duration in seconds")
    prediction_time_seconds: float | None = Field(default=None, description="Evaluation duration in seconds")


class CounterpartModelInfo(BaseModel):
    """Information on the comparative counterpart algorithm for the same condition."""

    algorithm: AlgorithmType
    algorithm_label: str
    experiment_id: str
    metrics: ModelMetrics
    is_available: bool


class ModelDetailResponse(BaseModel):
    """Detailed metadata and offline performance metrics for a specific model."""

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


class RegistrySummary(BaseModel):
    """Summary of all 120 trained models in the NapasLoka registry."""

    total_experiments: int = Field(..., description="Total planned combinations (120)")
    completed_experiments: int = Field(..., description="Total fully completed models")
    ready_ratio: float = Field(..., description="Percentage of ready models")
    locations_count: int
    pollutants: list[str]
    scenarios: list[str]
    algorithms: list[str]
    models: list[dict[str, Any]]
