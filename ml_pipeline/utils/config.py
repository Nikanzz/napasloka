"""Safe YAML configuration loading for repository-owned configuration files."""

from pathlib import Path
from typing import Any

import yaml

from ml_pipeline.utils.paths import CONFIG_DIR


def load_yaml_config(relative_path: str | Path) -> dict[str, Any]:
    """Load one YAML file below ``configs`` and return a mapping."""

    path = (CONFIG_DIR / relative_path).resolve()
    if not path.is_relative_to(CONFIG_DIR.resolve()):
        raise ValueError("Configuration path must remain inside the configs directory")
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as stream:
        content = yaml.safe_load(stream) or {}
    if not isinstance(content, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return content
