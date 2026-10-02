"""Pydantic schemas for next-hour prediction request and response."""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

from backend.app.schemas.registry import AlgorithmType, PollutantType, ScenarioType


class PredictionRequest(BaseModel):
    """Payload for next-hour atmospheric pollutant prediction."""

    location: str = Field(..., min_length=1, description="Location slug identifier")
    pollutant: PollutantType = Field(..., description="Target pollutant ('co' or 'co2')")
    scenario: ScenarioType = Field(..., description="Scenario identifier ('scenario_1' or 'scenario_2')")
    algorithm: AlgorithmType = Field(..., description="Selected algorithm ('xgboost' or 'lightgbm')")
    reference_datetime: datetime | str | None = Field(
        default=None,
        description="Historical observation point t to forecast from (defaults to latest available observation)",
    )
    # Optional fields for backwards compatibility
    start_datetime: datetime | str | None = None
    end_datetime: datetime | str | None = None


class AirQualityAssessment(BaseModel):
    """Assessment of the predicted concentration based on health standards."""

    category: str = Field(..., description="Category label, e.g. 'Baik', 'Sedang', 'Tidak Sehat'")
    color: str = Field(..., description="Hex color code for UI badges")
    description: str = Field(..., description="Health advisory and impact description")
    standard: str = Field(..., description="Air quality standard reference (ISPU Permen LHK / WHO)")


class FeatureInputItem(BaseModel):
    """Details of an individual feature fed into the model."""

    name: str = Field(..., description="Feature column identifier")
    label: str = Field(..., description="Human-readable feature label")
    value: float = Field(..., description="Feature numerical value")
    unit: str = Field(..., description="Measurement unit")


class NextHourPredictionResponse(BaseModel):
    """Complete prediction report for next-hour forecast."""

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

    # Forecast values
    predicted_value: float = Field(..., description="Predicted concentration for the next hour (t+1)")
    target_time: str = Field(..., description="ISO timestamp of predicted hour (t+1)")
    target_time_display: str = Field(..., description="Formatted Indonesian display string for target time")

    # Reference observation (t)
    latest_observation_time: str = Field(..., description="ISO timestamp of reference observation (t)")
    latest_observation_display: str = Field(..., description="Formatted Indonesian display string for reference observation")
    latest_observation_value: float = Field(..., description="Observed concentration at reference hour (t)")
    delta_value: float = Field(..., description="Absolute change (predicted - latest)")
    delta_percentage: float = Field(..., description="Relative percentage change")
    trend: str = Field(..., description="Directional trend ('naik', 'turun', or 'stabil')")

    # Health and environmental assessment
    assessment: AirQualityAssessment

    # Inputs used
    feature_inputs: list[FeatureInputItem]

    # Baseline comparison (what does counterpart algorithm forecast on identical inputs?)
    counterpart_algorithm: str
    counterpart_label: str
    counterpart_predicted_value: float | None = None
    counterpart_delta: float | None = None
