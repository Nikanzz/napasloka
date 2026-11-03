import json
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.experiments import build_experiment_matrix
from src.utils.config import ARTIFACTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_model")


def generate_summary_report(output_csv=None):
    """Collect metrics across all research experiment artifacts into a single CSV."""
    if output_csv is None:
        output_csv = ARTIFACTS_DIR / "summary_metrics.csv"
    else:
        output_csv = Path(output_csv)

    specs = build_experiment_matrix()
    records = []

    for spec in specs:
        artifact_dir = spec["artifact_dir"]
        metrics_path = artifact_dir / "metrics.json"
        params_path = artifact_dir / "best_params.json"

        if not metrics_path.exists():
            continue

        with metrics_path.open("r", encoding="utf-8") as f:
            metrics = json.load(f)

        best_params = {}
        if params_path.exists():
            with params_path.open("r", encoding="utf-8") as f:
                best_params = json.load(f)

        records.append({
            "location": spec["location"],
            "pollutant": spec["pollutant"].upper(),
            "scenario": spec["scenario"],
            "algorithm": spec["algorithm"],
            "mae": metrics.get("mae"),
            "rmse": metrics.get("rmse"),
            "mape": metrics.get("mape"),
            "r2": metrics.get("r2"),
            "training_time_seconds": metrics.get("training_time_seconds"),
            "prediction_time_seconds": metrics.get("prediction_time_seconds"),
            "best_params": str(best_params),
        })

    df_summary = pd.DataFrame(records)
    if df_summary.empty:
        logger.warning("No experiment metric artifacts found in artifacts/experiments/!")
        return df_summary

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df_summary.to_csv(output_csv, index=False)
    logger.info(f"Consolidated {len(df_summary)} experiments into: {output_csv}")

    return df_summary


def main():
    """Execute metric consolidation workflow directly."""
    generate_summary_report()


if __name__ == "__main__":
    main()
