"""Generate consolidated metrics summary and report tables from all 120 experiment artifacts."""

import json
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.paths import EXPERIMENTS_DIR, ARTIFACTS_DIR
from src.experiments.experiment import build_experiment_matrix


def main() -> None:
    specs = build_experiment_matrix()
    records = []

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
        print("Belum ada artefak metrik yang ditemukan!")
        return

    output_csv = ARTIFACTS_DIR / "summary_metrics.csv"
    df_summary.to_csv(output_csv, index=False)
    print(f"\n[SUKSES] Seluruh {len(df_summary)} hasil eksperimen berhasil direkap ke: {output_csv}")

    # Summary metrics
    print("\n" + "="*80)
    print("               RINGKASAN HASIL PENELITIAN ")
    print("="*80)

    print("\n--- 1. Perbandingan Algoritma (XGBoost vs LightGBM) ---")
    algo_comp = df_summary.groupby(["pollutant", "algorithm"])[["mae", "rmse", "mape", "r2", "training_time_seconds"]].mean()
    print(algo_comp.round(4))

    print("\n--- 2. Pengaruh Fitur Cuaca (Skenario 1 vs Skenario 2) ---")
    scen_comp = df_summary.groupby(["pollutant", "scenario"])[["mae", "rmse", "mape", "r2"]].mean()
    print(scen_comp.round(4))

    print("\n--- 3. Top 3 Model dengan Akurasi Tertinggi (CO) ---")
    top_co = df_summary[df_summary["pollutant"] == "CO"].sort_values(by="r2", ascending=False).head(3)
    print(top_co[["location", "scenario", "algorithm", "mae", "mape", "r2"]].to_string(index=False))

    print("\n--- 4. Top 3 Model dengan Akurasi Tertinggi (CO2) ---")
    top_co2 = df_summary[df_summary["pollutant"] == "CO2"].sort_values(by="r2", ascending=False).head(3)
    print(top_co2[["location", "scenario", "algorithm", "mae", "mape", "r2"]].to_string(index=False))
    print("="*80)


if __name__ == "__main__":
    main()
