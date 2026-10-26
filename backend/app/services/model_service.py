"""Model service providing high-level model operations backed by the registry."""

from backend.app.services.registry_service import registry_service


class ModelService:
    """Locate, load, and manage trained models for the API layer."""

    def __init__(self):
        self.registry = registry_service

    def is_available(self, request):
        """Return whether all core artifacts for the requested model are ready."""
        try:
            status = self.registry.get_artifact_status(
                location=request.location,
                pollutant=request.pollutant,
                scenario=request.scenario,
                algorithm=request.algorithm,
            )
            return status.is_ready
        except Exception:
            return False

    def get_model(self, location, pollutant, scenario, algorithm):
        """Load and return the trained model estimator."""
        return self.registry.load_estimator(location, pollutant, scenario, algorithm)

    def get_details(self, location, pollutant, scenario, algorithm):
        """Return full model details including metrics and counterpart information."""
        return self.registry.get_model_details(location, pollutant, scenario, algorithm)
