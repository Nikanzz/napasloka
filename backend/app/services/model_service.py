"""Resolve trained model artifacts selected by the API."""

from backend.app.schemas.prediction import PredictionRequest
from ml_pipeline.experiments.experiment import ExperimentSpec


class ModelService:
    """Locate, and later load, the exact model for four experiment dimensions."""

    MODEL_PATTERNS = ("model.joblib", "model.ubj", "model.txt", "model.pkl")

    def is_available(self, request: PredictionRequest) -> bool:
        """Return whether a recognized persisted model file exists."""

        spec = ExperimentSpec(
            location=request.location,
            pollutant=request.pollutant,
            scenario=request.scenario,
            algorithm=request.algorithm,
        )
        return any((spec.artifact_directory / name).is_file() for name in self.MODEL_PATTERNS)
