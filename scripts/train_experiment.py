"""CLI contract for one generic experiment; heavy training is disabled."""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ml_pipeline.experiments.experiment import ExperimentSpec  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse the four experiment dimensions."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--location", required=True)
    parser.add_argument("--pollutant", required=True, choices=["co", "co2"])
    parser.add_argument("--scenario", required=True, choices=["scenario_1", "scenario_2"])
    parser.add_argument("--algorithm", required=True, choices=["xgboost", "lightgbm"])
    return parser.parse_args()


def main() -> None:
    """Validate and show the future experiment without starting training."""

    spec = ExperimentSpec(**vars(parse_args()))
    raise SystemExit(f"Training is disabled in Phase 0. Valid experiment: {spec.experiment_id}")


if __name__ == "__main__":
    main()
