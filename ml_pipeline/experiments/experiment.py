"""A single generic experiment definition for all model combinations."""

from dataclasses import asdict, dataclass
from pathlib import Path

from ml_pipeline.utils.identifiers import build_experiment_id, slugify_component
from ml_pipeline.utils.paths import EXPERIMENTS_DIR
from ml_pipeline.utils.config import load_yaml_config


SUPPORTED_POLLUTANTS = {"co", "co2"}
SUPPORTED_SCENARIOS = {"scenario_1", "scenario_2"}
SUPPORTED_ALGORITHMS = {"xgboost", "lightgbm"}


@dataclass(frozen=True)
class ExperimentSpec:
    """Four dimensions that uniquely select one independent experiment."""

    location: str
    pollutant: str
    scenario: str
    algorithm: str

    def __post_init__(self) -> None:
        if self.pollutant not in SUPPORTED_POLLUTANTS:
            raise ValueError(f"Unsupported pollutant: {self.pollutant}")
        if self.scenario not in SUPPORTED_SCENARIOS:
            raise ValueError(f"Unsupported scenario: {self.scenario}")
        if self.algorithm not in SUPPORTED_ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
        slugify_component(self.location)

    @property
    def experiment_id(self) -> str:
        """Return the deterministic identifier used by logs and registry."""

        return build_experiment_id(
            self.location,
            self.pollutant,
            self.scenario,
            self.algorithm,
        )

    @property
    def artifact_directory(self) -> Path:
        """Return the required location/pollutant/scenario/algorithm path."""

        return EXPERIMENTS_DIR.joinpath(
            slugify_component(self.location),
            self.pollutant,
            self.scenario,
            self.algorithm,
        )

    def as_dict(self) -> dict[str, str]:
        """Serialize dimensions for metadata and registry records."""

        return asdict(self)


def build_experiment_matrix() -> list[ExperimentSpec]:
    """Expand configured locations across all research dimensions."""

    locations = load_yaml_config("locations.yaml").get("locations", [])
    project = load_yaml_config("project.yaml")
    scenarios = load_yaml_config("features.yaml").get("scenarios", {})
    specs: list[ExperimentSpec] = []
    for location in locations:
        location_id = location.get("id")
        if not location_id:
            raise ValueError("Every configured location must have a non-empty id")
        for pollutant in project.get("pollutants", {}):
            for scenario in scenarios:
                for algorithm in project.get("algorithms", []):
                    specs.append(
                        ExperimentSpec(location_id, pollutant, scenario, algorithm)
                    )
    return specs
