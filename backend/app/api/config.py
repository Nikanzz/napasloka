"""Read-only options exposed to the PWA."""

from typing import Any

from fastapi import APIRouter

from ml_pipeline.utils.config import load_yaml_config


router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/options")
def configuration_options() -> dict[str, list[dict[str, Any]]]:
    """Return only locations and experiment dimensions supported by config."""

    project = load_yaml_config("project.yaml")
    features = load_yaml_config("features.yaml")
    locations = load_yaml_config("locations.yaml").get("locations", [])
    pollutants = [
        {"id": key, **value}
        for key, value in project.get("pollutants", {}).items()
    ]
    scenarios = [
        {"id": key, "label": value["label"]}
        for key, value in features.get("scenarios", {}).items()
    ]
    algorithms = [
        {"id": value, "label": "XGBoost" if value == "xgboost" else "LightGBM"}
        for value in project.get("algorithms", [])
    ]
    return {
        "locations": locations,
        "pollutants": pollutants,
        "scenarios": scenarios,
        "algorithms": algorithms,
    }
