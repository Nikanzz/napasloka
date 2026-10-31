import logging
from fastapi import APIRouter, HTTPException, status

from backend.app.core.config import settings
from backend.app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from backend.app.services.evaluation_service import evaluation_service
from backend.app.services.registry_service import registry_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("", response_model=EvaluationResponse)
def evaluate_model(request: EvaluationRequest):
    try:
        return evaluation_service.evaluate_test_range(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_EVALUATION_REQUEST", "message": str(e)},
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ARTIFACT_NOT_FOUND", "message": str(e)},
        )
    except Exception as e:
        logger.exception("Unexpected error in evaluation endpoint: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "EVALUATION_ERROR", "message": "Terjadi kesalahan internal saat mengevaluasi model."},
        )


@router.get("/range")
def get_evaluation_time_range(
    location="taman-kamal",
    pollutant="co",
    scenario="scenario_1",
    algorithm="xgboost",
):
    try:
        df = registry_service.load_test_predictions(location, pollutant, scenario, algorithm)
        return {
            "location": location,
            "pollutant": pollutant,
            "start": df["datetime"].min().isoformat(),
            "end": df["datetime"].max().isoformat(),
            "total_samples": len(df),
            "default_start": settings.default_test_start,
            "default_end": settings.default_test_end,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RANGE_NOT_FOUND", "message": str(e)},
        )
