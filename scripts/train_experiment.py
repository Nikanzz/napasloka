"""CLI contract for running one or all research experiments."""

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.experiments.executor import execute_single_experiment
from src.experiments.experiment import ExperimentSpec, build_experiment_matrix
from src.experiments.runner import ExperimentRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train NapasLoka research experiments.")
    parser.add_argument("--all", action="store_true", help="Run all 120 matrix experiments.")
    parser.add_argument("--location", help="Location ID (e.g. taman-kamal).")
    parser.add_argument("--pollutant", choices=["co", "co2"], help="Pollutant target.")
    parser.add_argument("--scenario", choices=["scenario_1", "scenario_2"], help="Feature scenario.")
    parser.add_argument("--algorithm", choices=["xgboost", "lightgbm"], help="Model algorithm.")
    parser.add_argument("--retry-failed", action="store_true", help="Retry previously failed experiments.")
    parser.add_argument("--force", action="store_true", help="Force rerun experiments even if already completed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runner = ExperimentRunner()

    if args.all:
        specs = build_experiment_matrix()
        logging.info(f"Starting batch execution of {len(specs)} experiments...")
        for idx, spec in enumerate(specs, start=1):
            exp_id = spec.experiment_id
            if not args.force and not runner.registry.should_run(spec, retry_failed=args.retry_failed):
                logging.info(f"[{idx}/{len(specs)}] SKIPPED (already completed): {exp_id}")
                continue
            logging.info(f"[{idx}/{len(specs)}] RUNNING: {exp_id}")
            record = runner.run(spec, execute_single_experiment, retry_failed=args.retry_failed, force=args.force)
            status = record.get("status", "unknown")
            logging.info(f"[{idx}/{len(specs)}] FINISHED: {exp_id} -> {status}")
        logging.info("Batch execution finished!")
        return

    if not all([args.location, args.pollutant, args.scenario, args.algorithm]):
        print("Error: Specify either --all OR provide all four dimensions (--location, --pollutant, --scenario, --algorithm).")
        print("Example: python scripts/train_experiment.py --location taman-kamal --pollutant co --scenario scenario_1 --algorithm xgboost")
        sys.exit(1)

    spec = ExperimentSpec(
        location=args.location,
        pollutant=args.pollutant,
        scenario=args.scenario,
        algorithm=args.algorithm,
    )
    logging.info(f"Executing single experiment: {spec.experiment_id}")
    record = runner.run(spec, execute_single_experiment, retry_failed=args.retry_failed, force=args.force)
    logging.info(f"Experiment completed with status: {record.get('status')}")
    logging.info(f"Artifacts saved to: {spec.artifact_directory}")


if __name__ == "__main__":
    main()
