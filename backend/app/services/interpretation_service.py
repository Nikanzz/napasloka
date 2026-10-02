"""Interpretation service for local TreeSHAP attribution and global feature importance."""

import logging
from typing import Any
import numpy as np
import pandas as pd

import ml_pipeline.interpretation.shap_analysis  # Sets up Windows SAC protection
import shap

from backend.app.core.config import (
    ALGORITHM_METADATA,
    LOCATION_REGIONS,
    POLLUTANT_METADATA,
    SCENARIO_METADATA,
    settings,
)
from backend.app.schemas.interpretation import (
    GlobalFeatureItem,
    InterpretationRequest,
    InterpretationResponse,
    LocalShapContribution,
)
from backend.app.services.data_service import data_service
from backend.app.services.prediction_service import format_indo_timestamp, get_feature_display_info
from backend.app.services.registry_service import registry_service
from ml_pipeline.utils.identifiers import build_experiment_id, slugify_component

logger = logging.getLogger(__name__)

SCIENTIFIC_DISCLAIMER = (
    "Pemberitahuan Metodologis: Nilai SHAP (SHapley Additive exPlanations) merepresentasikan kontribusi "
    "marginal matematis dari masing-masing variabel masukan terhadap deviasi output model dari nilai dasar "
    "(expected value). Nilai kontribusi ini mencerminkan mekanisme asosiatif internal model machine learning "
    "dan BUKAN merupakan bukti hubungan kausalitas (sebab-akibat) fisik atmosfer secara langsung."
)


class InterpretationService:
    """Computes dynamic local TreeSHAP explanations and collates global feature importance."""

    def __init__(self) -> None:
        self.registry = registry_service
        self.data_service = data_service
        self.supported_locations = {loc["id"]: loc for loc in settings.get_locations()}

    def interpret_prediction(self, request: InterpretationRequest) -> InterpretationResponse:
        """Calculate on-the-fly local TreeSHAP attribution and aggregate offline global importance."""
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

        # 1. Build input feature vector
        X_df, meta = self.data_service.build_next_hour_features(
            loc_slug,
            request.pollutant,
            request.scenario,
            reference_datetime=request.reference_datetime,
        )

        # 2. Load model estimator
        model = self.registry.load_estimator(
            loc_slug,
            request.pollutant,
            request.scenario,
            request.algorithm,
        )

        # 3. Compute TreeSHAP
        explainer = shap.TreeExplainer(model)
        shap_raw = explainer.shap_values(X_df)
        if isinstance(shap_raw, list):
            shap_raw = shap_raw[0]

        shap_array = np.asarray(shap_raw).flatten()
        base_val_raw = (
            float(explainer.expected_value)
            if isinstance(explainer.expected_value, (int, float, np.floating))
            else float(explainer.expected_value[0])
        )
        base_value = round(base_val_raw, 2)
        pred_value = round(float(model.predict(X_df)[0]), 2)

        # 4. Form local contributions
        total_abs_impact = float(np.sum(np.abs(shap_array)))
        contributions: list[LocalShapContribution] = []

        for idx, col in enumerate(X_df.columns):
            val = float(X_df[col].iloc[0])
            sv = float(shap_array[idx])
            magnitude = abs(sv)
            pct = (magnitude / total_abs_impact * 100) if total_abs_impact > 0 else 0.0
            direction = "positive" if sv >= 0 else "negative"
            label, unit = get_feature_display_info(col, pollutant_info["unit"])

            if direction == "positive":
                dir_label = f"Menaikkan Prediksi (+{magnitude:.2f} {pollutant_info['unit']})"
            else:
                dir_label = f"Menurunkan Prediksi (-{magnitude:.2f} {pollutant_info['unit']})"

            contributions.append(
                LocalShapContribution(
                    feature_name=col,
                    label=label,
                    feature_value=round(val, 2),
                    unit=unit,
                    shap_value=round(sv, 2),
                    direction=direction,
                    direction_label=dir_label,
                    impact_magnitude=round(magnitude, 2),
                    percentage_impact=round(pct, 2),
                )
            )

        # Sort by impact magnitude descending
        contributions.sort(key=lambda c: c.impact_magnitude, reverse=True)
        top_contributor = contributions[0]

        # Top-K for charting
        top_k = min(request.top_k, len(contributions))
        top_contributions = contributions[:top_k]

        # 5. Format chart series for Plotly (horizontal bar chart)
        # Invert order for Plotly so top contributor is rendered at the top
        chart_items = list(reversed(top_contributions))
        chart_series = {
            "features": [c.label for c in chart_items],
            "values": [c.shap_value for c in chart_items],
            "colors": ["#10b981" if c.direction == "positive" else "#ef4444" for c in chart_items],
            "text": [
                f"{c.label}: {c.shap_value:+.2f} {pollutant_info['unit']} (Nilai: {c.feature_value} {c.unit})"
                for c in chart_items
            ],
            "feature_values": [c.feature_value for c in chart_items],
            "units": [c.unit for c in chart_items],
        }

        # 6. Collate global feature importance from saved artifacts
        global_importance: list[GlobalFeatureItem] = []
        try:
            raw_gain = self.registry.get_feature_importance(
                loc_slug,
                request.pollutant,
                request.scenario,
                request.algorithm,
            )
            raw_shap = self.registry.get_global_shap(
                loc_slug,
                request.pollutant,
                request.scenario,
                request.algorithm,
            )
            shap_map = {row["feature"]: float(row["mean_absolute_shap"]) for row in raw_shap}

            for row in raw_gain:
                feat_name = row["feature"]
                label, _ = get_feature_display_info(feat_name, pollutant_info["unit"])
                global_importance.append(
                    GlobalFeatureItem(
                        feature_name=feat_name,
                        label=label,
                        gain_importance=round(float(row["importance"]), 4),
                        mean_abs_shap=round(shap_map.get(feat_name, 0.0), 3) if feat_name in shap_map else None,
                    )
                )
            global_importance.sort(key=lambda g: g.gain_importance, reverse=True)
        except Exception as e:
            logger.warning("Could not load global importance artifacts: %s", e)

        # 7. Synthesize human-readable interpretation narrative
        target_ts = meta["target_prediction_time"]
        global_lead = global_importance[0] if global_importance else None
        global_lead_text = (
            f" Secara konsisten dalam dataset latih global, fitur '{global_lead.label}' menjadi faktor paling deterministik "
            f"dengan proporsi Gain importance sebesar {global_lead.gain_importance:.1%}."
            if global_lead else ""
        )

        interpretation_summary = (
            f"Model {algorithm_info['name']} menghasilkan prediksi {pred_value:.2f} {pollutant_info['unit']} "
            f"dari nilai dasar (base value) {base_value:.2f} {pollutant_info['unit']}. "
            f"Faktor pendorong lokal terbesar pada jam ini adalah '{top_contributor.label}' dengan nilai aktual "
            f"{top_contributor.feature_value:.2f} {top_contributor.unit}, yang memberikan kontribusi "
            f"{top_contributor.shap_value:+.2f} {pollutant_info['unit']} ({top_contributor.direction_label.lower()})."
            f"{global_lead_text}"
        )

        experiment_id = build_experiment_id(
            loc_slug,
            request.pollutant,
            request.scenario,
            request.algorithm,
        )

        return InterpretationResponse(
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
            predicted_value=pred_value,
            base_value=base_value,
            target_time=target_ts.isoformat(),
            target_time_display=format_indo_timestamp(target_ts),
            top_contributor=top_contributor,
            local_contributions=contributions,
            chart_series=chart_series,
            global_importance=global_importance,
            scientific_disclaimer=SCIENTIFIC_DISCLAIMER,
            interpretation_summary=interpretation_summary,
        )


# Singleton interpretation service instance
interpretation_service = InterpretationService()
