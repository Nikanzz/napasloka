"""Consolidated model evaluation, metrics synthesis, and academic report generator."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.experiments import build_experiment_matrix
from src.utils.config import ARTIFACTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_model")


def generate_summary_report(
    output_csv: Path | None = None,
    print_tables: bool = True,
    export_markdown: Path | None = None,
) -> pd.DataFrame:
    """Collect metrics across all research experiment artifacts and generate summary tables.

    Parameters:
        output_csv: Path to save the consolidated CSV (default: ARTIFACTS_DIR / "summary_metrics.csv").
        print_tables: If True, prints comparison tables to stdout.
        export_markdown: Optional path to write markdown summary.

    Returns:
        DataFrame containing consolidated metrics across all experiments.
    """
    if output_csv is None:
        output_csv = ARTIFACTS_DIR / "summary_metrics.csv"

    specs = build_experiment_matrix()
    records: list[dict[str, Any]] = []

    for spec in specs:
        artifact_dir = spec.artifact_directory
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
            "location": spec.location,
            "pollutant": spec.pollutant.upper(),
            "scenario": spec.scenario,
            "algorithm": spec.algorithm,
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

    if print_tables:
        print("\n" + "=" * 80)
        print("                 RINGKASAN HASIL EVALUASI RISET NAPASLOKA")
        print("=" * 80)

        print("\n--- 1. Perbandingan Algoritma (XGBoost vs LightGBM) ---")
        algo_comp = df_summary.groupby(["pollutant", "algorithm"])[
            ["mae", "rmse", "mape", "r2", "training_time_seconds"]
        ].mean()
        print(algo_comp.round(4))

        print("\n--- 2. Pengaruh Fitur Cuaca (Skenario 1 vs Skenario 2) ---")
        scen_comp = df_summary.groupby(["pollutant", "scenario"])[
            ["mae", "rmse", "mape", "r2"]
        ].mean()
        print(scen_comp.round(4))

        print("\n--- 3. Top 3 Model dengan Akurasi Tertinggi (CO) ---")
        top_co = df_summary[df_summary["pollutant"] == "CO"].sort_values(by="r2", ascending=False).head(3)
        print(top_co[["location", "scenario", "algorithm", "mae", "mape", "r2"]].to_string(index=False))

        print("\n--- 4. Top 3 Model dengan Akurasi Tertinggi (CO2) ---")
        top_co2 = df_summary[df_summary["pollutant"] == "CO2"].sort_values(by="r2", ascending=False).head(3)
        print(top_co2[["location", "scenario", "algorithm", "mae", "mape", "r2"]].to_string(index=False))
        print("=" * 80)

    if export_markdown:
        export_markdown.parent.mkdir(parents=True, exist_ok=True)
        with export_markdown.open("w", encoding="utf-8") as f:
            f.write("# Ringkasan Evaluasi Model NapasLoka\n\n")
            f.write("## Perbandingan Algoritma (Rata-rata)\n")
            f.write(algo_comp.round(4).to_markdown() + "\n\n")
            f.write("## Pengaruh Fitur Cuaca (Rata-rata)\n")
            f.write(scen_comp.round(4).to_markdown() + "\n\n")
            f.write("## Top 3 Model CO (Berdasarkan R2)\n")
            f.write(top_co[["location", "scenario", "algorithm", "mae", "mape", "r2"]].to_markdown(index=False) + "\n\n")
            f.write("## Top 3 Model CO2 (Berdasarkan R2)\n")
            f.write(top_co2[["location", "scenario", "algorithm", "mae", "mape", "r2"]].to_markdown(index=False) + "\n")
        logger.info(f"Markdown evaluation summary exported to: {export_markdown}")

    return df_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synthesize experiment metrics and generate thesis-grade evaluation reports."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ARTIFACTS_DIR / "summary_metrics.csv",
        help="Path to output summary_metrics.csv (default: artifacts/summary_metrics.csv).",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        help="Optional path to output markdown summary report.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress terminal printing of summary tables.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_summary_report(
        output_csv=args.output,
        print_tables=not args.quiet,
        export_markdown=args.markdown,
    )


if __name__ == "__main__":
    main()
