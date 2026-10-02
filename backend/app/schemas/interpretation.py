"""Pydantic schemas for model interpretation, local TreeSHAP, and global feature importance."""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

from backend.app.schemas.registry import AlgorithmType, PollutantType, ScenarioType


class InterpretationRequest(BaseModel):
    """Payload to request model interpretation for a predicted observation."""

    location: str = Field(..., min_length=1, description="Location slug identifier")
    pollutant: PollutantType = Field(..., description="Target pollutant ('co' or 'co2')")
    scenario: ScenarioType = Field(..., description="Scenario identifier ('scenario_1' or 'scenario_2')")
    algorithm: AlgorithmType = Field(..., description="Selected algorithm ('xgboost' or 'lightgbm')")
    reference_datetime: datetime | str | None = Field(
        default=None,
        description="Observation timestamp to interpret (defaults to latest available observation)",
    )
    top_k: int = Field(
        default=5,
        description="Number of top influential features to highlight",
    )


class LocalShapContribution(BaseModel):
    """Local TreeSHAP explanation for a single feature at the evaluated point."""

    feature_name: str = Field(..., description="Feature column identifier")
    label: str = Field(..., description="Readable Indonesian feature label")
    feature_value: float = Field(..., description="Actual value of the feature at time t")
    unit: str = Field(..., description="Measurement unit")
    shap_value: float = Field(..., description="SHAP attribution value (marginal contribution)")
    direction: Literal["positive", "negative"] = Field(..., description="'positive' increases prediction, 'negative' decreases it")
    direction_label: str = Field(..., description="Indonesian label describing the impact direction")
    impact_magnitude: float = Field(..., description="Absolute magnitude of contribution (|shap|)")
    percentage_impact: float = Field(..., description="Relative proportion of impact among all features (%)")


class GlobalFeatureItem(BaseModel):
    """Global feature importance and mean absolute SHAP from offline artifacts."""

    feature_name: str
    label: str
    gain_importance: float = Field(..., description="Normalized Gain importance score (0-1)")
    mean_abs_shap: float | None = Field(default=None, description="Offline dataset-wide mean absolute SHAP")


class InterpretationResponse(BaseModel):
    """Complete interpretation report with local TreeSHAP and global importance."""

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

    # Local prediction reference
    predicted_value: float = Field(..., description="Model output prediction f(x)")
    base_value: float = Field(..., description="Expected value baseline E[f(X)]")
    target_time: str
    target_time_display: str

    # Local SHAP decomposition
    top_contributor: LocalShapContribution
    local_contributions: list[LocalShapContribution]
    chart_series: dict[str, list[Any]] = Field(..., description="Formatted arrays for Plotly horizontal bar chart")

    # Global perspective
    global_importance: list[GlobalFeatureItem]

    # Scientific integrity notice
    scientific_disclaimer: str = Field(..., description="Formal non-causality disclosure statement")
    interpretation_summary: str = Field(..., description="Human-readable synthesis of model drivers")
