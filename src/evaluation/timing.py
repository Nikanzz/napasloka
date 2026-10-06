"""One timing primitive shared by training and prediction paths."""

from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class PerformanceTimer:
    """Context manager based on a monotonic high-resolution clock."""

    elapsed_seconds: float | None = field(default=None, init=False)
    _started_at: float | None = field(default=None, init=False, repr=False)

    def __enter__(self) -> "PerformanceTimer":
        self._started_at = perf_counter()
        return self

    def __exit__(self, *_: object) -> None:
        if self._started_at is None:
            raise RuntimeError("Timer was not started")
        self.elapsed_seconds = perf_counter() - self._started_at
