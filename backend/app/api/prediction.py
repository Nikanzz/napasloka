"""FastAPI router for next-hour pollutant concentration prediction."""

import logging
from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.prediction import NextHourPredictionResponse, PredictionRequest
from backend.app.services.prediction_service import prediction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["prediction"])


@router.post("", response_model=NextHourPredictionResponse)
def request_prediction(request: PredictionRequest) -> NextHourPredictionResponse:
    """Generate next-hour prediction for the selected location, pollutant, scenario, and algorithm."""
    try:
        return prediction_service.predict_next_hour(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PREDICTION_REQUEST", "message": str(e)},
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MODEL_OR_DATA_NOT_FOUND", "message": str(e)},
        )
    except Exception as e:
        logger.exception("Unexpected error in prediction endpoint: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "PREDICTION_FAILED", "message": "Terjadi kesalahan saat memproses prediksi satu jam berikutnya."},
        )
