"""Script to generate the Best Model Registry (60 entries) and retrain Final Deployment Models."""

import argparse
import datetime
import json
import logging
import sys
import time
from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.preprocessing import chronological_train_test_split
from src.experiments.best_model import select_best_models
from src.experiments.executor import _get_coordinate_id, _get_dataset
from src.features.lag_features import create_lag_features
from src.features.scenarios import resolve_scenario
from src.interpretation.feature_importance import gain_feature_importance
from src.interpretation.shap_analysis import calculate_tree_shap, mean_absolute_shap
from src.modeling.training import create_estimator
from src.utils.identifiers import slugify_component
from src.utils.paths import ARTIFACTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_final_models")


def retrain_single_final_model(
    entry: dict,
    final_dir: Path,
    force: bool = False,
    compute_shap_samples: int = 500,
    use_full_data: bool = True,
) -> dict:
    """Train a single final deployment model based on its best experiment hyperparameters.

    Parameters:
        entry: Best model registry entry dictionary.
        final_dir: Directory where the retrained model and artifacts are stored.
        force: If True, overwrite existing model artifacts.
        compute_shap_samples: Number of observation samples to calculate global TreeSHAP.
        use_full_data: If True (default/recommended for production), retrains using 100% of available
                       historical data up to the cutoff. If False, trains on the 80% development split.
    """
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

    # Feature engineering matching exact experimental methodology
    df_features = create_lag_features(
        df_loc,
        pollutant=pol,
        scenario=scen,
        drop_incomplete_rows=True,
    )

    scenario_def = resolve_scenario(pol, scen)
    feature_cols = list(scenario_def.feature_names)
    target_col = scenario_def.pollutant_column

    # Data split selection
    if use_full_data:
        # Full historical data up to cutoff for operational deployment
        x_train = df_features[feature_cols]
        y_train = df_features[target_col]
        train_samples_count = len(df_features)
        training_data_type = "full_historical_dataset"
        # Sample most recent observations for operational SHAP base values
        shap_sample = df_features[feature_cols].tail(compute_shap_samples)
    else:
        # Development split only (80:20)
        train_df, test_df = chronological_train_test_split(df_features, test_fraction=0.2)
        x_train = train_df[feature_cols]
        y_train = train_df[target_col]
        train_samples_count = len(train_df)
        training_data_type = "chronological_development_split"
        shap_sample = test_df[feature_cols].head(compute_shap_samples)

    # Instantiate estimator with winning hyperparameters
    estimator = create_estimator(algo, parameters=best_params)

    start_train = time.time()
    estimator.fit(x_train, y_train)
    retrain_duration = time.time() - start_train

    # Feature Importance (Gain-based)
    df_gain = gain_feature_importance(estimator, feature_cols, normalize=True)

    # Global SHAP on observation sample
    shap_vals = calculate_tree_shap(estimator, shap_sample)
    df_shap_global = mean_absolute_shap(shap_vals, feature_cols)

    # Save artifacts in dedicated final models directory
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
        "creation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
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

    with meta_dest.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Saved final deployment model and metadata to: {final_dir}")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Best Model Registry and Retrain Final Deployment Models.")
    parser.add_argument("--all", action="store_true", help="Retrain all 60 best deployment models.")
    parser.add_argument("--location", help="Filter by location (e.g. taman-kamal).")
    parser.add_argument("--pollutant", choices=["co", "co2"], help="Filter by pollutant.")
    parser.add_argument("--scenario", choices=["scenario_1", "scenario_2"], help="Filter by scenario.")
    parser.add_argument("--generate-registry-only", action="store_true", help="Only generate best_models.json registry without retraining.")
    parser.add_argument("--force", action="store_true", help="Force retrain and overwrite existing final models.")
    parser.add_argument("--primary-metric", default="mae", help="Primary selection metric (default: mae).")
    parser.add_argument("--use-dev-split-only", action="store_true", help="Retrain on 80% development split only instead of 100% full dataset.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Step 1: Generate or update best_models.json
    logger.info("Generating/verifying Best Model Registry from summary_metrics.csv...")
    registry_file = ARTIFACTS_DIR / "registry" / "best_models.json"
    registry = select_best_models(
        summary_csv_path=ARTIFACTS_DIR / "summary_metrics.csv",
        registry_output_path=registry_file,
        primary_metric=args.primary_metric,
    )
    logger.info(f"Best Model Registry ready with {registry['total_combinations']} combinations at: {registry_file}")

    if args.generate_registry_only:
        logger.info("Flag --generate-registry-only specified. Exiting without retraining.")
        return

    # Filter combinations
    best_models = registry["best_models"]
    to_retrain = []

    for key, entry in best_models.items():
        if args.location and entry["location"] != slugify_component(args.location):
            continue
        if args.pollutant and entry["pollutant"] != args.pollutant.lower():
            continue
        if args.scenario and entry["scenario"] != args.scenario.lower():
            continue
        to_retrain.append(entry)

    if not to_retrain:
        logger.warning("No model combinations matched the requested filter.")
        return

    use_full = not args.use_dev_split_only
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
            force=args.force,
            use_full_data=use_full,
        )
        completed += 1

    total_elapsed = time.time() - start_total
    logger.info(f"Finished retraining {completed} final models in {total_elapsed:.2f} seconds!")


if __name__ == "__main__":
    main()
