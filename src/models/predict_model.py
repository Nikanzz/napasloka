"""Offline and batch inference CLI / programmatic interface for trained NapasLoka models."""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.features.lag_features import create_lag_features
from src.features.scenarios import resolve_scenario
from src.utils.identifiers import slugify_component
from src.utils.config import ARTIFACTS_DIR, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("predict_model")


def load_final_model_artifacts(location, pollutant, scenario):
    """Load trained final deployment model and its metadata."""
    loc_slug = slugify_component(location)
    pol_slug = pollutant.lower()
    scen_slug = scenario.lower()

    model_dir = ARTIFACTS_DIR / "final" / loc_slug / pol_slug / scen_slug
    model_path = model_dir / "model.joblib"
    meta_path = model_dir / "final_metadata.json"

    if not model_path.exists():
        raise FileNotFoundError(
            f"Final model not found at: {model_path}. "
            f"Make sure you have trained final models with 'python -m src.models.train_model --mode final'."
        )

    model = joblib.load(model_path)
    metadata = {}
    if meta_path.exists():
        with meta_path.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

    return model, metadata


def predict_from_artifact(location, pollutant, scenario, feature_df):
    """Execute prediction using final deployment model on the provided dataframe."""
    model, metadata = load_final_model_artifacts(location, pollutant, scenario)
    required_features = metadata.get("features")
    if not required_features:
        scenario_def = resolve_scenario(pollutant, scenario)
        required_features = list(scenario_def.feature_names)

    missing = [c for c in required_features if c not in feature_df.columns]
    if missing:
        raise ValueError(f"Input DataFrame is missing required features: {missing}")

    x_input = feature_df[required_features]

    start_time = time.time()
    preds = model.predict(x_input)
    inference_duration = time.time() - start_time

    return np.asarray(preds), inference_duration


def run_demo_prediction(location, pollutant, scenario, n_samples=5):
    """Run a quick demonstration of inference using test observations from processed data."""
    logger.info(f"Running demo prediction for: {location} | {pollutant.upper()} | {scenario} (n={n_samples})")

    pol_file = "jabodetabek_co_dataset.csv" if pollutant.lower() == "co" else "jabodetabek_co2_dataset.csv"
    data_path = DATA_DIR / "processed" / pol_file
    if not data_path.exists():
        logger.error(f"Dataset {data_path} not found. Please run preprocessing first.")
        return

    df = pd.read_csv(data_path)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert("Asia/Jakarta")

    from src.models.experiments import _get_coordinate_id
    coord_id = _get_coordinate_id(location)
    df_loc = df[(df["location"] == coord_id) | (df["location"] == location)].sort_values("datetime").reset_index(drop=True)

    if df_loc.empty:
        logger.error(f"No observations found for {location} ({coord_id}).")
        return

    df_features = create_lag_features(df_loc, pollutant=pollutant, scenario=scenario, drop_incomplete_rows=True)
    sample_df = df_features.tail(n_samples).reset_index(drop=True)

    preds, duration = predict_from_artifact(location, pollutant, scenario, sample_df)

    scenario_def = resolve_scenario(pollutant, scenario)
    actuals = sample_df[scenario_def.pollutant_column].values

    print("\n" + "=" * 70)
    print(f" DEMO INFERENCE: {location} | {pollutant.upper()} | {scenario}")
    print(f" Inference Time: {duration * 1000:.2f} ms ({duration / n_samples * 1000:.3f} ms/sample)")
    print("=" * 70)
    res_df = pd.DataFrame({
        "datetime": sample_df["datetime"].astype(str),
        "actual": np.round(actuals, 4),
        "predicted": np.round(preds, 4),
        "error": np.round(np.abs(actuals - preds), 4),
    })
    print(res_df.to_string(index=False))
    print("=" * 70)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Predict pollutant concentrations using trained NapasLoka models."
    )
    parser.add_argument("--location", required=True, help="Location ID (e.g. taman-kamal).")
    parser.add_argument("--pollutant", required=True, choices=["co", "co2"], help="Pollutant target.")
    parser.add_argument("--scenario", required=True, choices=["scenario_1", "scenario_2"], help="Feature scenario.")
    parser.add_argument("--input-csv", type=Path, help="Path to input features CSV for batch inference.")
    parser.add_argument("--output-csv", type=Path, help="Path to save predicted outputs.")
    parser.add_argument("--demo", action="store_true", help="Run demo inference on recent test observations.")
    parser.add_argument("--samples", type=int, default=5, help="Number of demo samples (default: 5).")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.demo or not args.input_csv:
        run_demo_prediction(args.location, args.pollutant, args.scenario, n_samples=args.samples)
        return

    logger.info(f"Loading input features from: {args.input_csv}")
    input_df = pd.read_csv(args.input_csv)
    preds, duration = predict_from_artifact(args.location, args.pollutant, args.scenario, input_df)

    output_df = input_df.copy()
    output_df[f"predicted_{args.pollutant.lower()}"] = preds

    if args.output_csv:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        output_df.to_csv(args.output_csv, index=False)
        logger.info(f"Predictions saved to {args.output_csv} (took {duration:.4f}s)")
    else:
        print(output_df[[f"predicted_{args.pollutant.lower()}"]].head())


if __name__ == "__main__":
    main()
