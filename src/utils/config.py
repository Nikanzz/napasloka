from pathlib import Path
from typing import Any

import yaml

from src.utils.paths import CONFIG_DIR


def load_yaml_config(relative_path: str | Path) -> dict[str, Any]:
    path = (CONFIG_DIR / relative_path).resolve()

    with path.open("r", encoding="utf-8") as stream:
        content = yaml.safe_load(stream) or {}

    if not isinstance(content, dict):
        raise ValueError(f"Harus YAML Mapping agar bisa terbentuk dictionary pada {path}")
    
    return content
