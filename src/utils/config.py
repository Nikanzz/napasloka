from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"
DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
EXPERIMENTS_DIR = ARTIFACTS_DIR / "experiments"
REGISTRY_DIR = ARTIFACTS_DIR / "registry"


def project_path(*parts):
    return PROJECT_ROOT.joinpath(*parts)


def load_yaml_config(relative_path):
    path = (CONFIG_DIR / relative_path).resolve()
    with path.open("r", encoding="utf-8") as stream:
        content = yaml.safe_load(stream) or {}

    if not isinstance(content, dict):
        raise ValueError(f"Harus YAML Mapping agar bisa terbentuk dictionary pada {path}")

    return content
