"""Resumable orchestration around a generic experiment execution callback."""

import json
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ml_pipeline.experiments.experiment import ExperimentSpec
from ml_pipeline.experiments.registry import ExperimentRegistry, ExperimentStatus


ExperimentExecutor = Callable[[ExperimentSpec, Path], dict[str, Any]]


class ExperimentRunner:
    """Run independent specs while persisting status after every model."""

    def __init__(self, registry: ExperimentRegistry | None = None) -> None:
        self.registry = registry or ExperimentRegistry()

    def run(
        self,
        spec: ExperimentSpec,
        executor: ExperimentExecutor,
        *,
        retry_failed: bool = False,
    ) -> dict[str, Any]:
        """Execute one experiment, or return its existing record when skipped."""

        self.registry.register(spec)
        if not self.registry.should_run(spec, retry_failed=retry_failed):
            return self.registry.get(spec.experiment_id) or {}

        artifact_directory = spec.artifact_directory
        artifact_directory.mkdir(parents=True, exist_ok=True)
        self.registry.update(spec, ExperimentStatus.RUNNING)
        try:
            metadata = executor(spec, artifact_directory)
            _write_metadata(spec, artifact_directory, metadata)
        except Exception as exc:
            self.registry.update(spec, ExperimentStatus.FAILED, error=str(exc))
            raise
        return self.registry.update(spec, ExperimentStatus.COMPLETED)

    def run_many(
        self,
        specs: Iterable[ExperimentSpec],
        executor: ExperimentExecutor,
        *,
        retry_failed: bool = False,
    ) -> list[dict[str, Any]]:
        """Run specs sequentially so every completion is independently durable."""

        return [
            self.run(spec, executor, retry_failed=retry_failed)
            for spec in specs
        ]


def _write_metadata(
    spec: ExperimentSpec,
    directory: Path,
    metadata: dict[str, Any],
) -> None:
    payload = {
        "experiment_id": spec.experiment_id,
        **spec.as_dict(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    path = directory / "experiment_metadata.json"
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
