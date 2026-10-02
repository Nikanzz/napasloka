"use strict";

/**
 * Controller for Konfigurasi Prediksi (Prediction Page).
 */
document.addEventListener("DOMContentLoaded", async () => {
  const form = document.getElementById("prediction-form");
  const submitBtn = document.getElementById("btn-submit-prediction");
  const statusContainer = document.getElementById("prediction-status-container");
  const resultSection = document.getElementById("prediction-result-section");

  const selectLoc = document.getElementById("select-location");
  const selectPol = document.getElementById("select-pollutant");
  const selectScen = document.getElementById("select-scenario");
  const selectAlgo = document.getElementById("select-algorithm");
  const inputRefTime = document.getElementById("input-ref-time");

  // Summary elements
  const summaryLocName = document.getElementById("summary-location-name");
  const summaryRegion = document.getElementById("summary-region");
  const summaryCoords = document.getElementById("summary-coords");
  const summaryPol = document.getElementById("summary-pollutant");
  const summaryUnit = document.getElementById("summary-unit");
  const summaryScen = document.getElementById("summary-scenario");
  const summaryFeaturesCount = document.getElementById("summary-features-count");
  const summaryAlgo = document.getElementById("summary-algorithm");

  // Result card elements
  const resPollutantTitle = document.getElementById("res-pollutant-title");
  const resTargetTimeBadge = document.getElementById("res-target-time-badge");
  const resAssessmentBadge = document.getElementById("res-assessment-badge");
  const resPredictedVal = document.getElementById("res-predicted-val");
  const resUnit = document.getElementById("res-unit");
  const resAssessmentDesc = document.getElementById("res-assessment-desc");
  const resLatestVal = document.getElementById("res-latest-val");
  const resLatestTime = document.getElementById("res-latest-time");
  const resDeltaVal = document.getElementById("res-delta-val");
  const resDeltaPct = document.getElementById("res-delta-pct");
  const resTrendBadge = document.getElementById("res-trend-badge");
  const resCounterpartLabel = document.getElementById("res-counterpart-label");
  const resCounterpartVal = document.getElementById("res-counterpart-val");
  const resCounterpartDelta = document.getElementById("res-counterpart-delta");
  const resFeatureChips = document.getElementById("res-feature-chips");
  const btnGotoEvaluation = document.getElementById("btn-goto-evaluation");
  const btnGotoInterpretation = document.getElementById("btn-goto-interpretation");

  let appOptions = null;

  // 1. Load options and populate dropdowns
  try {
    appOptions = await window.NapasLokaApi.getOptions();

    // Populate Location
    selectLoc.innerHTML = "";
    appOptions.locations.forEach((loc) => {
      const opt = document.createElement("option");
      opt.value = loc.id;
      opt.textContent = `${loc.name} (${loc.region || "Jabodetabek"})`;
      selectLoc.appendChild(opt);
    });

    // Populate Pollutant
    selectPol.innerHTML = "";
    appOptions.pollutants.forEach((pol) => {
      const opt = document.createElement("option");
      opt.value = pol.id;
      opt.textContent = `${pol.label} [${pol.unit}]`;
      selectPol.appendChild(opt);
    });

    // Populate Scenario
    selectScen.innerHTML = "";
    appOptions.scenarios.forEach((sc) => {
      const opt = document.createElement("option");
      opt.value = sc.id;
      opt.textContent = `${sc.label} (${sc.feature_count || (sc.id === "scenario_1" ? 3 : 15)} Fitur)`;
      selectScen.appendChild(opt);
    });

    // Populate Algorithm
    selectAlgo.innerHTML = "";
    appOptions.algorithms.forEach((algo) => {
      const opt = document.createElement("option");
      opt.value = algo.id;
      opt.textContent = algo.label || algo.name;
      selectAlgo.appendChild(opt);
    });

    // 2. Pre-select values from URL parameters or localStorage
    const urlParams = new URLSearchParams(window.location.search);
    const initialLoc = urlParams.get("location") || localStorage.getItem("napasloka_selected_location") || "taman-kamal";
    const initialPol = urlParams.get("pollutant") || localStorage.getItem("napasloka_selected_pollutant") || "co";
    const initialScen = urlParams.get("scenario") || localStorage.getItem("napasloka_selected_scenario") || "scenario_1";
    const initialAlgo = urlParams.get("algorithm") || localStorage.getItem("napasloka_selected_algorithm") || "xgboost";

    if (selectLoc.querySelector(`option[value="${initialLoc}"]`)) selectLoc.value = initialLoc;
    if (selectPol.querySelector(`option[value="${initialPol}"]`)) selectPol.value = initialPol;
    if (selectScen.querySelector(`option[value="${initialScen}"]`)) selectScen.value = initialScen;
    if (selectAlgo.querySelector(`option[value="${initialAlgo}"]`)) selectAlgo.value = initialAlgo;

    updateSummaryCard();

    // 3. Automatically perform initial prediction
    executePrediction();
  } catch (err) {
    showError("Gagal menginisialisasi parameter sistem: " + err.message);
  }

  // Update summary card on any select change
  [selectLoc, selectPol, selectScen, selectAlgo].forEach((el) => {
    el.addEventListener("change", () => {
      updateSummaryCard();
    });
  });

  function updateSummaryCard() {
    if (!appOptions) return;

    const locObj = appOptions.locations.find((l) => l.id === selectLoc.value);
    const polObj = appOptions.pollutants.find((p) => p.id === selectPol.value);
    const scenObj = appOptions.scenarios.find((s) => s.id === selectScen.value);
    const algoObj = appOptions.algorithms.find((a) => a.id === selectAlgo.value);

    if (locObj) {
      summaryLocName.textContent = locObj.name;
      summaryRegion.textContent = locObj.region || "Jabodetabek";
      summaryCoords.textContent = `${locObj.latitude.toFixed(2)}, ${locObj.longitude.toFixed(2)}`;
    }
    if (polObj) {
      summaryPol.textContent = polObj.label;
      summaryUnit.textContent = polObj.unit;
    }
    if (scenObj) {
      summaryScen.textContent = scenObj.label;
      summaryFeaturesCount.textContent = `${scenObj.feature_count || (scenObj.id === "scenario_1" ? 3 : 15)} Fitur`;
    }
    if (algoObj) {
      summaryAlgo.textContent = algoObj.label || algoObj.name;
    }
  }

  // Form submit handler
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    executePrediction();
  });

  async function executePrediction() {
    hideError();
    const loc = selectLoc.value;
    const pol = selectPol.value;
    const scen = selectScen.value;
    const algo = selectAlgo.value;
    const refTime = inputRefTime.value || null;

    // Save to localStorage
    localStorage.setItem("napasloka_selected_location", loc);
    localStorage.setItem("napasloka_selected_pollutant", pol);
    localStorage.setItem("napasloka_selected_scenario", scen);
    localStorage.setItem("napasloka_selected_algorithm", algo);

    // Set button loading state
    submitBtn.disabled = true;
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="spinner"></span> <span>Memproses Prediksi...</span>';

    try {
      const payload = {
        location: loc,
        pollutant: pol,
        scenario: scen,
        algorithm: algo,
      };
      if (refTime) {
        payload.reference_datetime = refTime;
      }

      const res = await window.NapasLokaApi.postPrediction(payload);
      renderPredictionResult(res);
    } catch (err) {
      showError(err.message || "Gagal memproses prediksi satu jam berikutnya.");
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnText;
    }
  }

  function renderPredictionResult(res) {
    resultSection.style.display = "block";

    // Header info
    resPollutantTitle.textContent = `${res.pollutant_label} di ${res.location_name}`;
    resTargetTimeBadge.textContent = `🎯 Target Prediksi: ${res.target_time_display}`;

    // Assessment badge & color
    resAssessmentBadge.textContent = res.assessment.category;
    resAssessmentBadge.style.backgroundColor = res.assessment.color || "#10b981";
    resAssessmentBadge.style.color = "#ffffff";
    resAssessmentDesc.textContent = `${res.assessment.description} (${res.assessment.standard})`;

    // Main prediction values
    resPredictedVal.textContent = res.predicted_value.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    resUnit.textContent = res.pollutant_unit;

    // Latest observation pill
    resLatestVal.textContent = `${res.latest_observation_value.toLocaleString("id-ID", { minimumFractionDigits: 2 })} ${res.pollutant_unit}`;
    resLatestTime.textContent = `Acuan: ${res.latest_observation_display}`;

    // Delta & percentage
    const deltaSign = res.delta_value >= 0 ? "+" : "";
    resDeltaVal.textContent = `${deltaSign}${res.delta_value.toLocaleString("id-ID", { minimumFractionDigits: 2 })} ${res.pollutant_unit}`;
    resDeltaPct.textContent = `(${deltaSign}${res.delta_percentage.toFixed(1)}%)`;

    // Trend badge
    if (res.trend === "naik") {
      resTrendBadge.className = "trend-badge trend-up";
      resTrendBadge.innerHTML = "📈 Tren Naik";
    } else if (res.trend === "turun") {
      resTrendBadge.className = "trend-badge trend-down";
      resTrendBadge.innerHTML = "📉 Tren Menurun";
    } else {
      resTrendBadge.className = "trend-badge trend-stable";
      resTrendBadge.innerHTML = "➡️ Stabil";
    }

    // Counterpart comparison pill
    resCounterpartLabel.textContent = `Pembanding ${res.counterpart_label}`;
    if (res.counterpart_predicted_value !== null && res.counterpart_predicted_value !== undefined) {
      resCounterpartVal.textContent = `${res.counterpart_predicted_value.toLocaleString("id-ID", { minimumFractionDigits: 2 })} ${res.pollutant_unit}`;
      const cpDeltaSign = (res.counterpart_delta || 0) >= 0 ? "+" : "";
      resCounterpartDelta.textContent = `Selisih: ${cpDeltaSign}${(res.counterpart_delta || 0).toFixed(2)} ${res.pollutant_unit}`;
    } else {
      resCounterpartVal.textContent = "Tidak tersedia";
      resCounterpartDelta.textContent = "";
    }

    // Feature input chips
    resFeatureChips.innerHTML = "";
    if (res.feature_inputs && res.feature_inputs.length > 0) {
      res.feature_inputs.forEach((f) => {
        const chip = document.createElement("div");
        chip.className = "feature-chip";
        chip.innerHTML = `
          <span class="feature-chip-title" title="${f.label}">${f.label}</span>
          <span class="feature-chip-val">${f.value.toLocaleString("id-ID", { minimumFractionDigits: 2 })} <small style="font-weight: normal; font-size: 0.75rem; color: #64748b;">${f.unit}</small></span>
        `;
        resFeatureChips.appendChild(chip);
      });
    }

    // Update Quick Links to Evaluation and Interpretation
    const queryParams = `location=${encodeURIComponent(res.location)}&pollutant=${encodeURIComponent(res.pollutant)}&scenario=${encodeURIComponent(res.scenario)}&algorithm=${encodeURIComponent(res.algorithm)}`;
    btnGotoEvaluation.href = `/pages/evaluation.html?${queryParams}`;
    btnGotoInterpretation.href = `/pages/interpretation.html?${queryParams}`;

    // Smooth scroll to result
    resultSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function showError(msg) {
    statusContainer.style.display = "block";
    statusContainer.innerHTML = `
      <div class="alert alert-warning" role="alert">
        <div class="alert-icon">⚠️</div>
        <div class="alert-content">
          <h4>Terjadi Kendala Prediksi</h4>
          <p>${msg}</p>
        </div>
      </div>
    `;
  }

  function hideError() {
    statusContainer.style.display = "none";
    statusContainer.innerHTML = "";
  }
});
