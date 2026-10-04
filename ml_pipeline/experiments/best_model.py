"""Logic for selecting the best model per location x pollutant x scenario from evaluation metrics."""

import json
from pathlib import Path
from typing import Any
import pandas as pd

from ml_pipeline.utils.identifiers import slugify_component
from ml_pipeline.utils.paths import ARTIFACTS_DIR


def select_best_models(
    summary_csv_path: Path | None = None,
    registry_output_path: Path | None = None,
    primary_metric: str = "mae",
    secondary_metric: str = "rmse",
) -> dict[str, Any]:
    """Determine the winning algorithm for each (location, pollutant, scenario) combination.

    Ranking rule:
      1. Lowest primary metric (default: MAE)
      2. Lowest secondary metric (default: RMSE) as tie-breaker
    """
    if summary_csv_path is None:
        summary_csv_path = ARTIFACTS_DIR / "summary_metrics.csv"
    if registry_output_path is None:
        registry_output_path = ARTIFACTS_DIR / "registry" / "best_models.json"

    if not summary_csv_path.exists():
        raise FileNotFoundError(f"Summary metrics CSV not found at: {summary_csv_path}")

    df = pd.read_csv(summary_csv_path)

    # Standardize column values
    df["location_slug"] = df["location"].apply(slugify_component)
    df["pollutant_lower"] = df["pollutant"].str.lower()
    df["scenario_lower"] = df["scenario"].str.lower()
    df["algorithm_lower"] = df["algorithm"].str.lower()

    # Sort deterministically: lowest MAE first, then lowest RMSE
    df_sorted = df.sort_values(
        by=["location_slug", "pollutant_lower", "scenario_lower", primary_metric, secondary_metric],
        ascending=[True, True, True, True, True],
    )

    # Group and pick first
    best_df = df_sorted.groupby(["location_slug", "pollutant_lower", "scenario_lower"]).first().reset_index()

    total_expected = 15 * 2 * 2  # 60 combinations
    if len(best_df) != total_expected:
        raise ValueError(
            f"Expected {total_expected} best model combinations, but found {len(best_df)}. "
            "Please check summary_metrics.csv completeness."
        )

    best_registry: dict[str, Any] = {
        "version": 1,
        "selection_rule": f"lowest_{primary_metric}_then_{secondary_metric}",
        "total_combinations": len(best_df),
        "best_models": {},
    }

    for _, row in best_df.iterrows():
        loc = row["location_slug"]
        pol = row["pollutant_lower"]
        scen = row["scenario_lower"]
        algo = row["algorithm_lower"]

        key = f"{loc}__{pol}__{scen}"
        experiment_id = f"{loc}__{pol}__{scen}__{algo}"

        # Parse best_params safely
        params_val = row.get("best_params", "{}")
        if isinstance(params_val, str):
            try:
                # Replace single quotes if present
                import ast
                best_params = ast.literal_eval(params_val)
            except Exception:
                best_params = {}
        elif isinstance(params_val, dict):
            best_params = params_val
        else:
            best_params = {}

        best_registry["best_models"][key] = {
            "key": key,
            "location": loc,
            "pollutant": pol,
            "scenario": scen,
            "best_algorithm": algo,
            "experiment_id": experiment_id,
            "metrics": {
                "mae": round(float(row["mae"]), 4),
                "rmse": round(float(row["rmse"]), 4),
                "mape": round(float(row["mape"]), 4),
                "r2": round(float(row["r2"]), 4),
                "training_time_seconds": round(float(row["training_time_seconds"]), 4) if pd.notna(row.get("training_time_seconds")) else None,
                "prediction_time_seconds": round(float(row["prediction_time_seconds"]), 4) if pd.notna(row.get("prediction_time_seconds")) else None,
            },
            "best_params": best_params,
            "experiment_artifact_dir": f"artifacts/experiments/{loc}/{pol}/{scen}/{algo}",
            "final_model_dir": f"artifacts/final/{loc}/{pol}/{scen}",
        }

    # Ensure output parent directory exists
    registry_output_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_output_path.open("w", encoding="utf-8") as f:
        json.dump(best_registry, f, indent=2)

    return best_registry
