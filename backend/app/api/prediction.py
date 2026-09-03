"""Prediction contract without fabricated Phase 0 output."""

from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.prediction import PredictionRequest
from backend.app.services.model_service import ModelService


router = APIRouter(prefix="/predict", tags=["prediction"])


@router.post("")
def request_prediction(request: PredictionRequest) -> dict[str, str]:
    """Reject requests clearly until the selected trained artifact exists."""

    service = ModelService()
    if not service.is_available(request):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "MODEL_NOT_AVAILABLE",
                "message": "The selected trained model is not available.",
            },
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "PREDICTION_NOT_IMPLEMENTED",
            "message": "Prediction orchestration is scheduled for a later phase.",
        },
    )
