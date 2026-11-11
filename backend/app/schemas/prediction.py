from datetime import datetime
from typing import Literal
from pydantic import BaseModel

from backend.app.schemas.registry import AlgorithmType, PollutantType, ScenarioType


class ClientLiveFeatures(BaseModel):
    latest_observation_time: str
    latest_observation_value: float
    target_prediction_time: str
    feature_values: dict[str, float]


class PredictionStatus(BaseModel):
    status_level: str
    category_label: str
    color: str
    standard_name: str
    description: str
    is_official_standard: bool


class PredictionRequest(BaseModel):
    location: str
    pollutant: PollutantType
    scenario: ScenarioType
    algorithm: AlgorithmType | Literal["auto"] | None = "auto"
    reference_datetime: datetime | str | None = None
    start_datetime: datetime | str | None = None
    end_datetime: datetime | str | None = None
    client_live_features: ClientLiveFeatures | None = None


class FeatureInputItem(BaseModel):
    name: str
    label: str
    value: float
    unit: str


class NextHourPredictionResponse(BaseModel):
    experiment_id: str
    location: str
    location_name: str
    region: str
    latitude: float
    longitude: float
    pollutant: PollutantType
    pollutant_label: str
    pollutant_unit: str
    scenario: ScenarioType
    scenario_label: str
    algorithm: AlgorithmType
    algorithm_label: str

    predicted_value: float
    target_time: str
    target_time_display: str

    latest_observation_time: str
    latest_observation_display: str
    latest_observation_value: float
    delta_value: float
    delta_percentage: float
    trend: str

    status: PredictionStatus
    feature_inputs: list[FeatureInputItem]

    counterpart_algorithm: str
    counterpart_label: str
    counterpart_predicted_value: float | None = None
    counterpart_delta: float | None = None

    model_status: str = "Final deployment model"
    is_final_model: bool = True
    best_algorithm: str = "lightgbm"
    is_live_data: bool = False
    live_data_error: str | None = None
