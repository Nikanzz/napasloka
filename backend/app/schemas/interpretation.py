from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel

from backend.app.schemas.registry import AlgorithmType, PollutantType, ScenarioType


class InterpretationRequest(BaseModel):
    location: str
    pollutant: PollutantType
    scenario: ScenarioType
    algorithm: AlgorithmType | Literal["auto"] | None = "auto"
    reference_datetime: datetime | str | None = None
    is_live: bool | None = None
    top_k: int = 5


class LocalShapContribution(BaseModel):
    feature_name: str
    label: str
    feature_value: float
    unit: str
    shap_value: float
    direction: Literal["positive", "negative"]
    direction_label: str
    impact_magnitude: float
    percentage_impact: float


class GlobalFeatureItem(BaseModel):
    feature_name: str
    label: str
    gain_importance: float
    mean_abs_shap: float | None = None


class InterpretationResponse(BaseModel):
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

    predicted_value: float
    base_value: float
    target_time: str
    target_time_display: str

    top_contributor: LocalShapContribution
    local_contributions: list[LocalShapContribution]
    chart_series: dict[str, list[Any]]

    global_importance: list[GlobalFeatureItem]

    scientific_disclaimer: str
    interpretation_summary: str

    model_status: str = "Final deployment model"
    is_final_model: bool = True
    best_algorithm: str = "lightgbm"
    is_live_data: bool = False
    live_data_error: str | None = None
