import argparse
import datetime
import json
import logging
import sys
import time
from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.clean_data import chronological_train_test_split
from src.features.lag_features import create_lag_features
from src.features.scenarios import resolve_scenario
from src.models.estimators import create_estimator
from src.models.experiments import (
    ExperimentRunner,
    ExperimentSpec,
    _get_coordinate_id,
    _get_dataset,
    build_experiment_matrix,
    execute_single_experiment,
    select_best_models,
)
from src.models.interpretation import (
    calculate_tree_shap,
    gain_feature_importance,
    mean_absolute_shap,
)
from src.utils.identifiers import slugify_component
from src.utils.config import ARTIFACTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_model")


# ==============================================================================
# Final Model Retraining Functions
# ==============================================================================

def retrain_single_final_model(
    entry,
    final_dir,
    force=False,
    compute_shap_samples=500,
    use_full_data=True,
):
    """Train a single final deployment model based on its best experiment hyperparameters."""
    loc = entry["location"]
    pol = entry["pollutant"]
    scen = entry["scenario"]
    algo = entry["best_algorithm"]
    best_params = entry["best_params"]
    exp_metrics = entry["metrics"]

    model_dest = final_dir / "model.joblib"
    meta_dest = final_dir / "final_metadata.json"

    if not force and model_dest.is_file() and meta_dest.is_file():
        logger.info(f"Final model already exists for {loc}/{pol}/{scen} -> SKIPPED (use --force to overwrite)")
        with meta_dest.open("r", encoding="utf-8") as f:
            return json.load(f)

    data_scope_desc = "100% FULL HISTORICAL DATA" if use_full_data else "80% DEV SPLIT"
    logger.info(f"Retraining final deployment model ({data_scope_desc}): {loc} | {pol.upper()} | {scen} | {algo.upper()}")

    pollutant_file = "jabodetabek_co_dataset.csv" if pol == "co" else "jabodetabek_co2_dataset.csv"
    df = _get_dataset(pollutant_file)
    coord_id = _get_coordinate_id(loc)

    df_loc = df[(df["location"] == coord_id) | (df["location"] == loc)].copy()
    if df_loc.empty:
        raise ValueError(f"No observation data for location: {loc} (coordinate: {coord_id})")

    df_loc = df_loc.sort_values("datetime").reset_index(drop=True)

    df_features = create_lag_features(
        df_loc,
        pollutant=pol,
        scenario=scen,
        drop_incomplete_rows=True,
    )

    scenario_def = resolve_scenario(pol, scen)
    feature_cols = list(scenario_def.feature_names)
    target_col = scenario_def.pollutant_column

    if use_full_data:
        x_train = df_features[feature_cols]
        y_train = df_features[target_col]
        train_samples_count = len(df_features)
        training_data_type = "full_historical_dataset"
        shap_sample = df_features[feature_cols].tail(compute_shap_samples)
    else:
        train_df, test_df = chronological_train_test_split(df_features, test_fraction=0.2)
        x_train = train_df[feature_cols]
        y_train = train_df[target_col]
        train_samples_count = len(train_df)
        training_data_type = "chronological_development_split"
        shap_sample = test_df[feature_cols].head(compute_shap_samples)

    estimator = create_estimator(algo, parameters=best_params)

    start_train = time.time()
    estimator.fit(x_train, y_train)
    retrain_duration = time.time() - start_train

    df_gain = gain_feature_importance(estimator, feature_cols, normalize=True)
    shap_vals = calculate_tree_shap(estimator, shap_sample)
    df_shap_global = mean_absolute_shap(shap_vals, feature_cols)

    final_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(estimator, model_dest)

    df_gain.to_csv(final_dir / "feature_importance.csv", index=False)
    df_shap_global.to_csv(final_dir / "shap_global.csv", index=False)

    data_start_iso = df_features["datetime"].min().isoformat()
    data_end_iso = df_features["datetime"].max().isoformat()

    metadata = {
        "model_name": "Sistem NapasLoka Final Deployment Model",
        "model_status": "final_deployment",
        "model_version": "1.0.0",
        "creation_timestamp": datetime.timezone.utc and datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "location": loc,
        "pollutant": pol,
        "scenario": scen,
        "algorithm": algo,
        "best_params": best_params,
        "target_variable": target_col,
        "features": feature_cols,
        "n_features": len(feature_cols),
        "n_train_samples": train_samples_count,
        "training_data_type": training_data_type,
        "data_start": data_start_iso,
        "data_end": data_end_iso,
        "training_time_seconds": round(retrain_duration, 4),
        "experiment_id": entry["experiment_id"],
        "experiment_metrics": exp_metrics,
        "selection_rule": "lowest_mae_then_rmse",
        "academic_note": (
            "Model final ini dilatih menggunakan 100% data historis yang tersedia (hingga cutoff deployment) khusus untuk kebutuhan prediksi operasional aplikasi. "
            "Evaluasi komparatif skripsi (MAE/RMSE/MAPE/R2) tetap dibekukan dari model eksperimen hold-out 80:20."
        ),
    }

    with open(meta_dest, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Saved final deployment model and metadata to: {final_dir}")
    return metadata


def retrain_final_models(
    location=None,
    pollutant=None,
    scenario=None,
    force=False,
    generate_registry_only=False,
    primary_metric="mae",
    use_dev_split_only=False,
):
    """Execute retraining flow for final deployment models."""
    logger.info("Generating/verifying Best Model Registry from summary_metrics.csv...")
    registry_file = ARTIFACTS_DIR / "registry" / "best_models.json"
    registry = select_best_models(
        summary_csv_path=ARTIFACTS_DIR / "summary_metrics.csv",
        registry_output_path=registry_file,
        primary_metric=primary_metric,
    )
    logger.info(f"Best Model Registry ready with {registry['total_combinations']} combinations at: {registry_file}")

    if generate_registry_only:
        logger.info("Flag generate_registry_only specified. Exiting without retraining.")
        return

    best_models = registry["best_models"]
    to_retrain = []

    for key, entry in best_models.items():
        if location and entry["location"] != slugify_component(location):
            continue
        if pollutant and entry["pollutant"] != pollutant.lower():
            continue
        if scenario and entry["scenario"] != scenario.lower():
            continue
        to_retrain.append(entry)

    if not to_retrain:
        logger.warning("No model combinations matched the requested filter.")
        return

    use_full = not use_dev_split_only
    logger.info(f"Starting retraining of {len(to_retrain)} final deployment models (use_full_data={use_full})...")
    start_total = time.time()
    completed = 0

    for idx, entry in enumerate(to_retrain, start=1):
        loc = entry["location"]
        pol = entry["pollutant"]
        scen = entry["scenario"]
        final_dir = ARTIFACTS_DIR / "final" / loc / pol / scen

        logger.info(f"[{idx}/{len(to_retrain)}] Processing {entry['key']}...")
        retrain_single_final_model(
            entry,
            final_dir,
            force=force,
            use_full_data=use_full,
        )
        completed += 1

    total_elapsed = time.time() - start_total
    logger.info(f"Finished retraining {completed} final models in {total_elapsed:.2f} seconds!")


# ==============================================================================
# Research Experiment Training Functions
# ==============================================================================

def train_experiments(
    run_all=False,
    location=None,
    pollutant=None,
    scenario=None,
    algorithm=None,
    retry_failed=False,
    force=False,
):
    """Execute research matrix experiments."""
    runner = ExperimentRunner()

    if run_all:
        specs = build_experiment_matrix()
        logger.info(f"Starting batch execution of {len(specs)} research experiments...")
        for idx, spec in enumerate(specs, start=1):
            exp_id = spec.experiment_id
            if not force and not runner.registry.should_run(spec, retry_failed=retry_failed):
                logger.info(f"[{idx}/{len(specs)}] SKIPPED (already completed): {exp_id}")
                continue
            logger.info(f"[{idx}/{len(specs)}] RUNNING: {exp_id}")
            record = runner.run(spec, execute_single_experiment, retry_failed=retry_failed, force=force)
            status = record.get("status", "unknown")
            logger.info(f"[{idx}/{len(specs)}] FINISHED: {exp_id} -> {status}")
        logger.info("Batch execution finished!")
        return

    if not all([location, pollutant, scenario, algorithm]):
        logger.error(
            "Specify either --all OR provide all four dimensions (--location, --pollutant, --scenario, --algorithm)."
        )
        sys.exit(1)

    spec = ExperimentSpec(
        location=location,
        pollutant=pollutant,
        scenario=scenario,
        algorithm=algorithm,
    )
    logger.info(f"Executing single experiment: {spec.experiment_id}")
    record = runner.run(spec, execute_single_experiment, retry_failed=retry_failed, force=force)
    logger.info(f"Experiment completed with status: {record.get('status')}")
    logger.info(f"Artifacts saved to: {spec.artifact_directory}")


# ==============================================================================
# CLI Entry Point
# ==============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Train NapasLoka research experiments or final deployment models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 1. Train all 120 research matrix experiments:
  python -m src.models.train_model --mode experiment --all

  # 2. Train a single specific research experiment:
  python -m src.models.train_model --mode experiment --location taman-kamal --pollutant co --scenario scenario_1 --algorithm xgboost

  # 3. Retrain all 60 final deployment models for production:
  python -m src.models.train_model --mode final --all

  # 4. Generate/verify best_models.json registry only:
  python -m src.models.train_model --mode final --generate-registry-only
""",
    )
    parser.add_argument(
        "--mode",
        choices=["experiment", "final"],
        default="final",
        help="Operational mode: 'experiment' (research matrix) or 'final' (production deployment models). Default: 'final'.",
    )
    parser.add_argument("--all", action="store_true", help="Execute all models for the selected mode.")
    parser.add_argument("--location", help="Location ID (e.g. taman-kamal).")
    parser.add_argument("--pollutant", choices=["co", "co2"], help="Target pollutant.")
    parser.add_argument("--scenario", choices=["scenario_1", "scenario_2"], help="Feature engineering scenario.")
    parser.add_argument("--algorithm", choices=["xgboost", "lightgbm"], help="Algorithm (experiment mode only).")
    parser.add_argument("--force", action="store_true", help="Force retrain and overwrite existing artifacts.")

    # Experiment specific
    parser.add_argument("--retry-failed", action="store_true", help="[Experiment mode] Retry previously failed experiments.")

    # Final specific
    parser.add_argument(
        "--generate-registry-only",
        action="store_true",
        help="[Final mode] Only generate best_models.json registry without retraining.",
    )
    parser.add_argument(
        "--primary-metric",
        default="mae",
        help="[Final mode] Primary selection metric (default: 'mae').",
    )
    parser.add_argument(
        "--use-dev-split-only",
        action="store_true",
        help="[Final mode] Retrain on 80%% dev split instead of 100%% full dataset.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.mode == "experiment":
        train_experiments(
            run_all=args.all,
            location=args.location,
            pollutant=args.pollutant,
            scenario=args.scenario,
            algorithm=args.algorithm,
            retry_failed=args.retry_failed,
            force=args.force,
        )
    elif args.mode == "final":
        retrain_final_models(
            location=args.location,
            pollutant=args.pollutant,
            scenario=args.scenario,
            force=args.force,
            generate_registry_only=args.generate_registry_only,
            primary_metric=args.primary_metric,
            use_dev_split_only=args.use_dev_split_only,
        )


if __name__ == "__main__":
    main()
