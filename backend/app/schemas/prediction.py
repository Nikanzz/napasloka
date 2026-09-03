"""Selection-only prediction schema; no manual scientific inputs are accepted."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """Select a trained experiment and optional available time range."""

    location: str = Field(min_length=1)
    pollutant: Literal["co", "co2"]
    scenario: Literal["scenario_1", "scenario_2"]
    algorithm: Literal["xgboost", "lightgbm"]
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
