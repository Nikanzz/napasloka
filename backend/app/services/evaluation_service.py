"""Evaluation service for slicing test set observations, calculating dynamic metrics, and comparing models."""

import logging
from typing import Any
import numpy as np
import pandas as pd

from backend.app.core.config import (
    ALGORITHM_METADATA,
    LOCATION_REGIONS,
    POLLUTANT_METADATA,
    SCENARIO_METADATA,
    settings,
)
from backend.app.schemas.evaluation import (
    ComparisonMetrics,
    EvaluationChartSeries,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationTimeRange,
)
from backend.app.schemas.registry import ModelMetrics
from backend.app.services.registry_service import registry_service
from ml_pipeline.evaluation.metrics import calculate_regression_metrics
from ml_pipeline.utils.identifiers import build_experiment_id, slugify_component

logger = logging.getLogger(__name__)


class EvaluationService:
    """Orchestrates test data evaluation, slicing, metric computation, and model comparison."""

    def __init__(self) -> None:
        self.registry = registry_service
        self.supported_locations = {loc["id"]: loc for loc in settings.get_locations()}

    def _normalize_timestamp(self, ts_input: Any, reference_tz: Any) -> pd.Timestamp | None:
        """Convert any datetime or ISO string to timestamp matching the reference timezone."""
        if ts_input is None:
            return None
        ts = pd.to_datetime(ts_input)
        if ts.tzinfo is None:
            return ts.tz_localize(reference_tz)
        return ts.tz_convert(reference_tz)

    def evaluate_test_range(self, request: EvaluationRequest) -> EvaluationResponse:
        """Slice test observations for the requested period, compute metrics, and compare with baseline."""
        self.registry.validate_dimensions(
            request.location,
            request.pollutant,
            request.scenario,
            request.algorithm,
        )

        loc_slug = slugify_component(request.location)
        loc_info = self.supported_locations[loc_slug]
        pollutant_info = POLLUTANT_METADATA[request.pollutant]
        scenario_info = SCENARIO_METADATA[request.scenario]
        algorithm_info = ALGORITHM_METADATA[request.algorithm]

        # 1. Load primary model test predictions
        df_primary = self.registry.load_test_predictions(
            loc_slug,
            request.pollutant,
            request.scenario,
            request.algorithm,
        ).copy()

        ref_tz = df_primary["datetime"].dt.tz
        dataset_min = df_primary["datetime"].min()
        dataset_max = df_primary["datetime"].max()
        total_samples = len(df_primary)

        # 2. Parse and normalize requested date range
        start_ts = self._normalize_timestamp(request.start_datetime, ref_tz) or dataset_min
        end_ts = self._normalize_timestamp(request.end_datetime, ref_tz) or dataset_max

        if start_ts > end_ts:
            raise ValueError(f"Tanggal mulai ({start_ts}) tidak boleh melebihi tanggal akhir ({end_ts}).")

        # 3. Slice primary dataframe
        mask = (df_primary["datetime"] >= start_ts) & (df_primary["datetime"] <= end_ts)
        df_sliced = df_primary[mask].sort_values("datetime").reset_index(drop=True)

        if df_sliced.empty:
            raise ValueError(
                f"Tidak ditemukan data uji observasi pada rentang waktu yang dipilih. "
                f"Rentang data uji tersedia: {dataset_min.isoformat()} s.d. {dataset_max.isoformat()}."
            )

        evaluated_samples = len(df_sliced)

        # 4. Compute dynamic regression metrics on the sliced range
        primary_metrics_dict = calculate_regression_metrics(
            df_sliced["actual"].values,
            df_sliced["predicted"].values,
        )
        stored_metrics = self.registry.get_metrics(
            loc_slug,
            request.pollutant,
            request.scenario,
            request.algorithm,
        )

        primary_metrics = ModelMetrics(
            mae=round(primary_metrics_dict["mae"], 3),
            rmse=round(primary_metrics_dict["rmse"], 3),
            mape=round(primary_metrics_dict["mape"], 3),
            r2=round(primary_metrics_dict["r2"], 4),
            training_time_seconds=stored_metrics.training_time_seconds,
            prediction_time_seconds=stored_metrics.prediction_time_seconds,
        )

        # 5. Load and evaluate counterpart model on the identical slice
        counterpart_algo = self.registry.get_counterpart_algorithm(request.algorithm)
        counterpart_info = ALGORITHM_METADATA.get(counterpart_algo, {})
        comparison: ComparisonMetrics | None = None
        df_cp_sliced: pd.DataFrame | None = None

        try:
            df_cp = self.registry.load_test_predictions(
                loc_slug,
                request.pollutant,
                request.scenario,
                counterpart_algo,
            )
            cp_mask = (df_cp["datetime"] >= start_ts) & (df_cp["datetime"] <= end_ts)
            df_cp_sliced = df_cp[cp_mask].sort_values("datetime").reset_index(drop=True)

            if len(df_cp_sliced) == evaluated_samples:
                cp_metrics_dict = calculate_regression_metrics(
                    df_cp_sliced["actual"].values,
                    df_cp_sliced["predicted"].values,
                )
                cp_stored = self.registry.get_metrics(
                    loc_slug,
                    request.pollutant,
                    request.scenario,
                    counterpart_algo,
                )
                cp_metrics = ModelMetrics(
                    mae=round(cp_metrics_dict["mae"], 3),
                    rmse=round(cp_metrics_dict["rmse"], 3),
                    mape=round(cp_metrics_dict["mape"], 3),
                    r2=round(cp_metrics_dict["r2"], 4),
                    training_time_seconds=cp_stored.training_time_seconds,
                    prediction_time_seconds=cp_stored.prediction_time_seconds,
                )

                # Differences (positive = primary is superior)
                mae_diff_pct = (
                    round(((cp_metrics.mae - primary_metrics.mae) / cp_metrics.mae) * 100, 2)
                    if cp_metrics.mae > 0 else 0.0
                )
                rmse_diff_pct = (
                    round(((cp_metrics.rmse - primary_metrics.rmse) / cp_metrics.rmse) * 100, 2)
                    if cp_metrics.rmse > 0 else 0.0
                )
                mape_diff = round(cp_metrics.mape - primary_metrics.mape, 2)
                r2_diff = round(primary_metrics.r2 - cp_metrics.r2, 4)

                winner = request.algorithm if primary_metrics.mae <= cp_metrics.mae else counterpart_algo

                pri_label = algorithm_info.get("name", request.algorithm.upper())
                cp_label = counterpart_info.get("name", counterpart_algo.upper())

                if mae_diff_pct > 0:
                    summary = (
                        f"Pada rentang evaluasi terpilih, {pri_label} mengungguli {cp_label} dengan MAE "
                        f"{primary_metrics.mae:.2f} {pollutant_info['unit']} ({abs(mae_diff_pct):.1f}% lebih presisi) "
                        f"dan koefisien determinasi R² {primary_metrics.r2:.4f} (selisih +{r2_diff:.4f})."
                    )
                elif mae_diff_pct < 0:
                    summary = (
                        f"Pada rentang evaluasi terpilih, {cp_label} memiliki nilai MAE {cp_metrics.mae:.2f} "
                        f"{pollutant_info['unit']} ({abs(mae_diff_pct):.1f}% lebih rendah dibanding {pri_label} "
                        f"dengan MAE {primary_metrics.mae:.2f}) dengan R² {cp_metrics.r2:.4f} vs {primary_metrics.r2:.4f}."
                    )
                else:
                    summary = (
                        f"Kedua model ({pri_label} dan {cp_label}) menunjukkan performa setara dengan MAE "
                        f"{primary_metrics.mae:.2f} {pollutant_info['unit']} pada periode evaluasi ini."
                    )

                comparison = ComparisonMetrics(
                    primary_algorithm=request.algorithm,
                    primary_label=algorithm_info.get("label", request.algorithm.upper()),
                    primary_metrics=primary_metrics,
                    counterpart_algorithm=counterpart_algo,
                    counterpart_label=counterpart_info.get("label", counterpart_algo.upper()),
                    counterpart_metrics=cp_metrics,
                    mae_diff_pct=mae_diff_pct,
                    rmse_diff_pct=rmse_diff_pct,
                    mape_diff=mape_diff,
                    r2_diff=r2_diff,
                    winner=winner,
                    summary=summary,
                )
        except Exception as e:
            logger.warning("Could not calculate counterpart comparison: %s", e)

        # 6. Prepare chart series (support downsampling if large)
        chart_df = df_sliced
        chart_cp_pred: list[float] | None = None

        if request.max_chart_points and evaluated_samples > request.max_chart_points:
            step = max(1, evaluated_samples // request.max_chart_points)
            chart_df = df_sliced.iloc[::step].copy()
            if df_cp_sliced is not None and len(df_cp_sliced) == evaluated_samples:
                chart_cp_pred = [round(float(v), 2) for v in df_cp_sliced["predicted"].iloc[::step].values]
        else:
            if df_cp_sliced is not None and len(df_cp_sliced) == evaluated_samples:
                chart_cp_pred = [round(float(v), 2) for v in df_cp_sliced["predicted"].values]

        timestamps = [dt.strftime("%Y-%m-%d %H:%M") for dt in chart_df["datetime"]]
        actuals = [round(float(v), 2) for v in chart_df["actual"].values]
        preds = [round(float(v), 2) for v in chart_df["predicted"].values]
        residuals = [round(float(v), 2) for v in chart_df["residual"].values]

        chart_data = EvaluationChartSeries(
            timestamps=timestamps,
            actual=actuals,
            predicted=preds,
            counterpart_predicted=chart_cp_pred,
            residual=residuals,
        )

        time_range = EvaluationTimeRange(
            start=df_sliced["datetime"].min().isoformat(),
            end=df_sliced["datetime"].max().isoformat(),
            dataset_start=dataset_min.isoformat(),
            dataset_end=dataset_max.isoformat(),
            total_test_samples=total_samples,
            evaluated_samples=evaluated_samples,
        )

        experiment_id = build_experiment_id(
            loc_slug,
            request.pollutant,
            request.scenario,
            request.algorithm,
        )

        # Lookup registered best model for this combination
        best_algo = None
        best_algo_label = None
        is_best = False
        try:
            best_entry = self.registry.get_best_model(loc_slug, request.pollutant, request.scenario)
            best_algo = best_entry["best_algorithm"]
            best_meta = ALGORITHM_METADATA.get(best_algo, {})
            best_algo_label = best_meta.get("label", best_algo.upper())
            is_best = (request.algorithm == best_algo)
        except Exception as e:
            logger.warning("Could not determine best model for evaluation: %s", e)

        return EvaluationResponse(
            experiment_id=experiment_id,
            location=loc_slug,
            location_name=loc_info["name"],
            region=LOCATION_REGIONS.get(loc_slug, "Jabodetabek"),
            pollutant=request.pollutant,
            pollutant_label=pollutant_info["label"],
            pollutant_unit=pollutant_info["unit"],
            scenario=request.scenario,
            scenario_label=scenario_info["label"],
            algorithm=request.algorithm,
            algorithm_label=algorithm_info["label"],
            time_range=time_range,
            metrics=primary_metrics,
            comparison=comparison,
            chart_data=chart_data,
            best_model_algorithm=best_algo,
            best_model_label=best_algo_label,
            is_best_model=is_best,
        )


# Singleton service instance
evaluation_service = EvaluationService()

