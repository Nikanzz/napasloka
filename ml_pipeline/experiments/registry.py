"""JSON-backed experiment state registry for resumable multi-day execution."""

import json
import os
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from ml_pipeline.experiments.experiment import ExperimentSpec
from ml_pipeline.utils.paths import REGISTRY_DIR


class ExperimentStatus(StrEnum):
    """Allowed lifecycle states for one experiment."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentRegistry:
    """Persist experiment progress after every independent model run."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or REGISTRY_DIR / "experiments.json"

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "experiments": {}}
        with self.path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data.get("experiments"), dict):
            raise ValueError(f"Invalid experiment registry: {self.path}")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            delete=False,
            suffix=".tmp",
        ) as temporary:
            json.dump(data, temporary, indent=2, ensure_ascii=False)
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, self.path)

    def register(self, spec: ExperimentSpec) -> dict[str, Any]:
        """Create a pending record if the experiment is not registered."""

        data = self._read()
        records = data["experiments"]
        record = records.setdefault(
            spec.experiment_id,
            {
                **spec.as_dict(),
                "experiment_id": spec.experiment_id,
                "status": ExperimentStatus.PENDING,
                "updated_at": _utc_now(),
                "error": None,
            },
        )
        self._write(data)
        return record.copy()

    def update(
        self,
        spec: ExperimentSpec,
        status: ExperimentStatus,
        *,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Persist a lifecycle transition immediately."""

        data = self._read()
        records = data["experiments"]
        record = records.get(spec.experiment_id, {**spec.as_dict(), "experiment_id": spec.experiment_id})
        record.update(status=status, updated_at=_utc_now(), error=error)
        records[spec.experiment_id] = record
        self._write(data)
        return record.copy()

    def get(self, experiment_id: str) -> dict[str, Any] | None:
        """Return one registry record, or None when unseen."""

        record = self._read()["experiments"].get(experiment_id)
        return record.copy() if record else None

    def should_run(self, spec: ExperimentSpec, *, retry_failed: bool = False) -> bool:
        """Skip completed work; rerun an interrupted ``running`` record."""

        record = self.get(spec.experiment_id)
        if record is None:
            return True
        status = record["status"]
        return status in {ExperimentStatus.PENDING, ExperimentStatus.RUNNING} or (
            retry_failed and status == ExperimentStatus.FAILED
        )

    def all(self) -> list[dict[str, Any]]:
        """Return all records in deterministic identifier order."""

        records = self._read()["experiments"]
        return [records[key].copy() for key in sorted(records)]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
