import logging
from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.interpretation import InterpretationRequest, InterpretationResponse
from backend.app.services.interpretation_service import interpretation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interpretation", tags=["interpretation"])


@router.post("", response_model=InterpretationResponse)
def interpret_model_prediction(request: InterpretationRequest):
    """Calculate TreeSHAP local feature contributions for a specific prediction request."""
    try:
        return interpretation_service.interpret_prediction(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INTERPRETATION_REQUEST", "message": str(e)},
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MODEL_OR_ARTIFACT_NOT_FOUND", "message": str(e)},
        )
    except Exception as e:
        logger.exception("Unexpected error in interpretation endpoint: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERPRETATION_FAILED", "message": "Terjadi kesalahan saat memproses interpretasi model SHAP."},
        )
