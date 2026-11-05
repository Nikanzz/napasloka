from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.services.registry_service import registry_service

router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/options")
def configuration_options():
    """Return available options for locations, pollutants, scenarios, and algorithms."""
    return {
        "locations": settings.get_locations(),
        "pollutants": settings.get_pollutants(),
        "scenarios": settings.get_scenarios(),
        "algorithms": settings.get_algorithms(),
        "evaluation_range": {
            "start": settings.default_test_start,
            "end": settings.default_test_end,
        },
        "forecast_horizon_hours": 1,
    }


@router.get("/models")
def get_all_models_summary():
    """Return readiness summary and status for all experimental models."""
    return registry_service.get_all_models_summary()


@router.get("/best-models")
def get_best_models_registry():
    """Return the complete registry of winning models per configuration."""
    return registry_service.get_all_best_models()
