"""Service health endpoint."""

from fastapi import APIRouter

from backend.app.schemas.common import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Report that the API process and routing layer are available."""

    return HealthResponse(status="OK", service="napasloka-api")
