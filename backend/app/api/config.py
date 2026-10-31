from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.services.registry_service import registry_service

router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/options")
def configuration_options():
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
    return registry_service.get_all_models_summary()


@router.get("/best-models")
def get_best_models_registry():
    return registry_service.get_all_best_models()
