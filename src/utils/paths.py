"""Canonical project and artifact paths."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"
DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
EXPERIMENTS_DIR = ARTIFACTS_DIR / "experiments"
REGISTRY_DIR = ARTIFACTS_DIR / "registry"


def project_path(*parts: str) -> Path:
    """Return a path below the repository root."""

    return PROJECT_ROOT.joinpath(*parts)
