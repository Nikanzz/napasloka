"""Common API response schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str
    service: str
