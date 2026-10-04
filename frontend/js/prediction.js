"use strict";

/**
 * Controller for Konfigurasi Prediksi (Precision Matching Chapter 3 Mockup 1 + Rich Foresight Result Panel).
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
  const btnUseLatestObs = document.getElementById("btn-use-latest-obs");
  const evalStartDate = document.getElementById("eval-start-date");
  const evalEndDate = document.getElementById("eval-end-date");
  const scenarioHintText = document.getElementById("scenario-hint-text");

  // Summary elements (Mockup 1 Right Card)
  const summaryLocName = document.getElementById("summary-location-name");
  const summaryPol = document.getElementById("summary-pollutant");
  const summaryScen = document.getElementById("summary-scenario");
  const summaryAlgo = document.getElementById("summary-algorithm");
  const summaryRefTime = document.getElementById("summary-ref-time");
  const summaryTargetTime = document.getElementById("summary-target-time");

  // Result card elements: Header & timeline
  const resPollutantTitle = document.getElementById("res-pollutant-title");
  const resAssessmentBadge = document.getElementById("res-assessment-badge");
  const resLatestTime = document.getElementById("res-latest-time");
  const resLatestVal = document.getElementById("res-latest-val");
  const resLatestUnit = document.getElementById("res-latest-unit");
  const resTargetTimeBadge = document.getElementById("res-target-time-badge");
  const resTargetSummaryVal = document.getElementById("res-target-summary-val");
  const resTargetSummaryUnit = document.getElementById("res-target-summary-unit");

  // Result card elements: Hero metric & dynamics
  const resPredictedVal = document.getElementById("res-predicted-val");
  const resUnit = document.getElementById("res-unit");
  const resTrendBadge = document.getElementById("res-trend-badge");
  const resTrendIcon = document.getElementById("res-trend-icon");
  const resTrendLabel = document.getElementById("res-trend-label");
  const resDeltaVal = document.getElementById("res-delta-val");
  const resDeltaPct = document.getElementById("res-delta-pct");

  // Result card elements: Health & Standards
  const resStandardRef = document.getElementById("res-standard-ref");
  const resAssessmentDesc = document.getElementById("res-assessment-desc");
  const resMeterFill = document.getElementById("res-meter-fill");
  const resMeterLabels = document.getElementById("res-meter-labels");

  // Result card elements: Counterpart benchmark
  const resActiveAlgoName = document.getElementById("res-active-algo-name");
  const resActiveAlgoVal = document.getElementById("res-active-algo-val");
  const resCounterpartLabel = document.getElementById("res-counterpart-label");
  const resCounterpartVal = document.getElementById("res-counterpart-val");
  const resCounterpartDelta = document.getElementById("res-counterpart-delta");
  const resCounterpartAgreement = document.getElementById("res-counterpart-agreement");

  // Result card elements: Features & Navigation
  const resFeaturesCount = document.getElementById("res-features-count");
  const resFeatureChips = document.getElementById("res-feature-chips");
  const btnGotoEvaluation = document.getElementById("btn-goto-evaluation");
  const btnGotoInterpretation = document.getElementById("btn-goto-interpretation");

  // Segmented control buttons (CO / CO2)
  const segmentedBtns = document.querySelectorAll("#pollutant-segmented .segmented-btn");
  segmentedBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      segmentedBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const val = btn.getAttribute("data-val");
      selectPol.value = val;
      selectPol.dispatchEvent(new Event("change"));
    });
  });

  let appOptions = null;
  let bestModelsRegistry = null;
  let latestObsTimestamp = "2026-08-04T23:00";

  // Helper: Format ISO string to Indonesian display timestamp
  function formatIndoTime(isoStr) {
    if (!isoStr) return "-";
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
      const day = String(d.getDate()).padStart(2, "0");
      const month = months[d.getMonth()];
      const year = d.getFullYear();
      const hours = String(d.getHours()).padStart(2, "0");
      const mins = String(d.getMinutes()).padStart(2, "0");
      return `${day} ${month} ${year}, ${hours}:${mins} WIB`;
    } catch {
      return isoStr;
    }
  }

  // Helper: Calculate Target Time (t + 1 hour)
  function calculateTargetIso(isoStr) {
    if (!isoStr) return "";
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return "";
    d.setHours(d.getHours() + 1);
    const yr = d.getFullYear();
    const mo = String(d.getMonth() + 1).padStart(2, "0");
    const da = String(d.getDate()).padStart(2, "0");
    const ho = String(d.getHours()).padStart(2, "0");
    const mi = String(d.getMinutes()).padStart(2, "0");
    return `${yr}-${mo}-${da}T${ho}:${mi}`;
  }

  // Helper: Update disabled algorithm select option with current winning model
  function updateAlgorithmDisplay() {
    const loc = selectLoc ? selectLoc.value : "";
    const pol = selectPol ? selectPol.value : "";
    const scen = selectScen ? selectScen.value : "";
    const key = `${loc}__${pol}__${scen}`;
    let winnerAlgo = "LightGBM";
    if (bestModelsRegistry && bestModelsRegistry.best_models && bestModelsRegistry.best_models[key]) {
      const entry = bestModelsRegistry.best_models[key];
      winnerAlgo = entry.best_algorithm && entry.best_algorithm.toLowerCase() === "xgboost" ? "XGBoost" : "LightGBM";
    }

    if (selectAlgo) {
      selectAlgo.innerHTML = `<option value="auto" selected>Otomatis: ${winnerAlgo} (Model Terbaik — Final Deployment)</option>`;
      selectAlgo.disabled = true;
    }
    return winnerAlgo;
  }

  // 1. Load options and populate dropdowns
  try {
    appOptions = await window.NapasLokaApi.getOptions();

    // Load best models registry
    try {
      bestModelsRegistry = await window.NapasLokaApi.getBestModels();
    } catch (regErr) {
      console.warn("Could not load best models registry:", regErr);
    }

    // Populate Location
    selectLoc.innerHTML = "";
    appOptions.locations.forEach((loc) => {
      const opt = document.createElement("option");
      opt.value = loc.id;
      opt.textContent = loc.name;
      selectLoc.appendChild(opt);
    });

    // Populate Pollutant select
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
      opt.textContent = sc.id === "scenario_1" ? "S1 · Historis polutan" : "S2 · Polutan + meteorologi";
      selectScen.appendChild(opt);
    });

    // Lock Algorithm select to Auto (Best Model)
    updateAlgorithmDisplay();

    // 2. Pre-select values from URL parameters or localStorage
    const urlParams = new URLSearchParams(window.location.search);
    const initialLoc = urlParams.get("location") || localStorage.getItem("napasloka_selected_location") || "petamburan-perkantoran-transjakarta";
    const initialPol = urlParams.get("pollutant") || localStorage.getItem("napasloka_selected_pollutant") || "co2";
    const initialScen = urlParams.get("scenario") || localStorage.getItem("napasloka_selected_scenario") || "scenario_2";
    const initialRefTime = urlParams.get("reference_datetime") || urlParams.get("end_date");

    if (selectLoc.querySelector(`option[value="${initialLoc}"]`)) selectLoc.value = initialLoc;
    if (selectPol.querySelector(`option[value="${initialPol}"]`)) {
      selectPol.value = initialPol;
      // sync segmented buttons
      segmentedBtns.forEach((b) => {
        b.classList.toggle("active", b.getAttribute("data-val") === initialPol);
      });
    }
    if (selectScen.querySelector(`option[value="${initialScen}"]`)) selectScen.value = initialScen;

    updateAlgorithmDisplay();
    await syncDatasetBounds();

    if (initialRefTime && inputRefTime) {
      const formattedInitialTime = initialRefTime.includes("T") ? initialRefTime.substring(0, 16) : `${initialRefTime}T23:00`;
      inputRefTime.value = formattedInitialTime;
    }

    updateSummaryCard();

    // 3. Automatically perform initial prediction
    executePrediction();
  } catch (err) {
    showError("Gagal menginisialisasi parameter sistem: " + err.message);
  }

  // Update summary card on any select change
  [selectLoc, selectPol, selectScen].forEach((el) => {
    el.addEventListener("change", () => {
      updateAlgorithmDisplay();
      updateSummaryCard();
    });
  });

  // Sync date bounds when location or pollutant changes
  selectLoc.addEventListener("change", syncDatasetBounds);
  selectPol.addEventListener("change", syncDatasetBounds);

  if (inputRefTime) {
    inputRefTime.addEventListener("change", () => {
      syncDatesFromInputRefTime();
      updateSummaryCard();
    });
  }

  if (btnUseLatestObs) {
    btnUseLatestObs.addEventListener("click", () => {
      if (inputRefTime) {
        inputRefTime.value = latestObsTimestamp;
        syncDatesFromInputRefTime();
        updateSummaryCard();
        executePrediction();
      }
    });
  }

  function syncDatesFromInputRefTime() {
    if (!inputRefTime || !inputRefTime.value) return;
    const datePart = inputRefTime.value.substring(0, 10);
    if (evalEndDate) evalEndDate.value = datePart;

    // Calculate 6 days prior for 7-day evaluation window
    try {
      const d = new Date(datePart);
      d.setDate(d.getDate() - 6);
      const yr = d.getFullYear();
      const mo = String(d.getMonth() + 1).padStart(2, "0");
      const da = String(d.getDate()).padStart(2, "0");
      if (evalStartDate) evalStartDate.value = `${yr}-${mo}-${da}`;
    } catch {
      if (evalStartDate) evalStartDate.value = "2026-07-29";
    }
  }

  async function syncDatasetBounds() {
    try {
      const bounds = await window.NapasLokaApi.getEvaluationRange(selectLoc.value, selectPol.value);
      if (bounds) {
        const startDay = bounds.start.substring(0, 10);
        const endDay = bounds.end.substring(0, 10);
        const maxIso = `${endDay}T23:00`;
        const minIso = `${startDay}T00:00`;
        latestObsTimestamp = maxIso;

        if (inputRefTime) {
          inputRefTime.value = maxIso;
          inputRefTime.disabled = true;
        }

        const refHint = document.getElementById("ref-time-hint");
        if (refHint) {
          const targetIso = calculateTargetIso(maxIso);
          refHint.innerHTML = `<span style="color: var(--color-primary); font-weight: 600;">✓ Waktu Otomatis Aktif</span> &mdash; Memproyeksikan konsentrasi 1 jam ke depan (${formatIndoTime(targetIso)}) berdasarkan observasi sensor mutakhir (${formatIndoTime(maxIso)}).`;
        }

        if (evalStartDate) {
          evalStartDate.min = startDay;
          evalStartDate.max = endDay;
        }
        if (evalEndDate) {
          evalEndDate.min = startDay;
          evalEndDate.max = endDay;
        }

        syncDatesFromInputRefTime();
      }
    } catch (e) {
      console.warn("Could not sync evaluation range bounds:", e);
    }
  }

  function updateSummaryCard() {
    if (!appOptions) return;

    const locObj = appOptions.locations.find((l) => l.id === selectLoc.value);
    const polObj = appOptions.pollutants.find((p) => p.id === selectPol.value);
    const scenObj = appOptions.scenarios.find((s) => s.id === selectScen.value);
    const algoObj = appOptions.algorithms.find((a) => a.id === selectAlgo.value);

    if (locObj && summaryLocName) {
      summaryLocName.textContent = locObj.name;
    }
    if (polObj && summaryPol) {
      summaryPol.textContent = `${polObj.symbol} · ${polObj.unit}`;
    }
    if (scenObj && summaryScen) {
      const isS1 = scenObj.id === "scenario_1";
      summaryScen.textContent = isS1 ? "Historis polutan" : "Polutan + meteorologi";
      if (scenarioHintText) {
        scenarioHintText.textContent = isS1
          ? "Fitur lag 3 jam historis konsentrasi polutan."
          : "Fitur lag polutan digabungkan dengan kondisi meteorologis.";
      }
    }
    const winnerAlgo = updateAlgorithmDisplay();
    const summaryModelStatus = document.getElementById("summary-model-status");
    if (summaryAlgo) summaryAlgo.textContent = `${winnerAlgo} (Model Terbaik)`;
    if (summaryModelStatus) summaryModelStatus.textContent = "Final deployment model";

    const currentRefVal = inputRefTime && inputRefTime.value ? inputRefTime.value : latestObsTimestamp;
    if (summaryRefTime) {
      summaryRefTime.textContent = formatIndoTime(currentRefVal);
    }
    if (summaryTargetTime) {
      const targetIso = calculateTargetIso(currentRefVal);
      summaryTargetTime.textContent = formatIndoTime(targetIso);
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
    const algo = "auto";
    const refTime = latestObsTimestamp || (inputRefTime && inputRefTime.value ? inputRefTime.value : null);

    // Save to localStorage
    localStorage.setItem("napasloka_selected_location", loc);
    localStorage.setItem("napasloka_selected_pollutant", pol);
    localStorage.setItem("napasloka_selected_scenario", scen);
    localStorage.setItem("napasloka_selected_algorithm", "auto");

    // Set button loading state
    submitBtn.disabled = true;
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span>Memproses Prediksi...</span>';

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

    // 1. Header info & Badge
    if (resPollutantTitle) {
      resPollutantTitle.textContent = `Prediksi ${res.pollutant_label} di ${res.location_name}`;
    }
    if (resAssessmentBadge) {
      resAssessmentBadge.textContent = res.assessment.category;
      resAssessmentBadge.style.backgroundColor = res.assessment.color || "#10b981";
      resAssessmentBadge.style.color = "#ffffff";
    }

    // 2. Timeline Bar (Observation t -> Target t+1)
    if (resLatestTime) {
      resLatestTime.textContent = res.latest_observation_display || formatIndoTime(res.latest_observation_time);
    }
    if (resLatestVal) {
      resLatestVal.textContent = Number(res.latest_observation_value).toLocaleString("id-ID", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 2,
      });
    }
    if (resLatestUnit) {
      resLatestUnit.textContent = res.pollutant_unit;
    }
    if (resTargetTimeBadge) {
      resTargetTimeBadge.textContent = res.target_time_display || formatIndoTime(res.target_time);
    }
    if (resTargetSummaryVal) {
      resTargetSummaryVal.textContent = Number(res.predicted_value).toLocaleString("id-ID", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 2,
      });
    }
    if (resTargetSummaryUnit) {
      resTargetSummaryUnit.textContent = res.pollutant_unit;
    }

    // 3. Hero Metric & Dynamics
    if (resPredictedVal) {
      resPredictedVal.textContent = Number(res.predicted_value).toLocaleString("id-ID", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 2,
      });
    }
    if (resUnit) {
      resUnit.textContent = res.pollutant_unit;
    }

    // Delta & Trend
    const deltaSign = res.delta_value > 0 ? "+" : "";
    if (resDeltaVal) {
      resDeltaVal.textContent = `${deltaSign}${Number(res.delta_value).toLocaleString("id-ID", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 2,
      })} ${res.pollutant_unit}`;
    }
    const pctSign = res.delta_percentage > 0 ? "+" : "";
    if (resDeltaPct) {
      resDeltaPct.textContent = `(${pctSign}${Number(res.delta_percentage).toFixed(2)}%)`;
    }

    if (resTrendBadge) {
      resTrendBadge.className = `pred-trend-pill trend-${res.trend}`;
      if (resTrendLabel) {
        resTrendLabel.textContent = res.trend.charAt(0).toUpperCase() + res.trend.slice(1);
      }
      if (resTrendIcon) {
        if (res.trend === "naik") {
          resTrendIcon.innerHTML = "&#9650;";
        } else if (res.trend === "turun") {
          resTrendIcon.innerHTML = "&#9660;";
        } else {
          resTrendIcon.innerHTML = "&#9679;";
        }
      }
    }

    // 4. Assessment Card & Standard Meter
    if (resStandardRef) {
      resStandardRef.textContent = res.assessment.standard || "Baku Mutu ISPU";
    }
    if (resAssessmentDesc) {
      resAssessmentDesc.textContent = res.assessment.description;
    }

    if (resMeterFill) {
      let fillPct = 50;
      if (res.pollutant === "co") {
        fillPct = Math.min(100, Math.max(5, (res.predicted_value / 15000) * 100));
        if (resMeterLabels) {
          resMeterLabels.innerHTML = "<span>Baik (&le; 4.000)</span><span>Sedang (8.000)</span><span>Tidak Sehat (15.000+)</span>";
        }
      } else {
        fillPct = Math.min(100, Math.max(5, ((res.predicted_value - 380) / (700 - 380)) * 100));
        if (resMeterLabels) {
          resMeterLabels.innerHTML = "<span>Normal (&le; 450)</span><span>Terakumulasi (600)</span><span>Tinggi (650+ ppm)</span>";
        }
      }
      resMeterFill.style.width = `${fillPct.toFixed(1)}%`;
      resMeterFill.style.backgroundColor = res.assessment.color || "#10b981";
    }

    // 5. Counterpart Benchmark
    if (resActiveAlgoName) {
      resActiveAlgoName.textContent = `${res.algorithm_label} (${res.model_status})`;
    }
    const summaryModelStatus = document.getElementById("summary-model-status");
    if (summaryModelStatus) {
      summaryModelStatus.textContent = res.model_status;
    }
    if (summaryAlgo) {
      summaryAlgo.textContent = `${res.algorithm_label} (${res.is_final_model ? "Model Terbaik" : "Komparasi"})`;
    }
    if (resActiveAlgoVal) {
      resActiveAlgoVal.textContent = `${Number(res.predicted_value).toLocaleString("id-ID", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 2,
      })} ${res.pollutant_unit}`;
    }
    if (resCounterpartLabel) {
      resCounterpartLabel.textContent = res.counterpart_label;
    }
    if (res.counterpart_predicted_value != null) {
      if (resCounterpartVal) {
        resCounterpartVal.textContent = `${Number(res.counterpart_predicted_value).toLocaleString("id-ID", {
          minimumFractionDigits: 1,
          maximumFractionDigits: 2,
        })} ${res.pollutant_unit}`;
      }
      const cpDeltaSign = res.counterpart_delta > 0 ? "+" : "";
      if (resCounterpartDelta) {
        resCounterpartDelta.textContent = `Selisih: ${cpDeltaSign}${Number(res.counterpart_delta).toLocaleString("id-ID", {
          minimumFractionDigits: 1,
          maximumFractionDigits: 2,
        })} ${res.pollutant_unit}`;
      }
      if (resCounterpartAgreement) {
        const absDiff = Math.abs(res.counterpart_delta);
        const pctDiff = (absDiff / (res.predicted_value || 1)) * 100;
        if (pctDiff < 2) {
          resCounterpartAgreement.textContent = `Deviasi ${pctDiff.toFixed(1)}% · Konsensus kedua model sangat tinggi`;
        } else {
          resCounterpartAgreement.textContent = `Deviasi ${pctDiff.toFixed(1)}% · Terdapat variasi estimasi antar model`;
        }
      }
    } else {
      if (resCounterpartVal) resCounterpartVal.textContent = "-";
      if (resCounterpartDelta) resCounterpartDelta.textContent = "-";
      if (resCounterpartAgreement) resCounterpartAgreement.textContent = "Data pembanding tidak tersedia";
    }

    // 6. Feature Inputs Inspection
    if (resFeaturesCount) {
      resFeaturesCount.textContent = res.feature_inputs ? res.feature_inputs.length : 0;
    }
    if (resFeatureChips) {
      resFeatureChips.innerHTML = "";
      if (res.feature_inputs && res.feature_inputs.length > 0) {
        res.feature_inputs.forEach((item, idx) => {
          const row = document.createElement("div");
          row.className = "pred-feature-list-row";
          const formattedVal = Number(item.value).toLocaleString("id-ID", {
            minimumFractionDigits: 1,
            maximumFractionDigits: 2,
          });
          row.innerHTML = `
            <div class="pred-feature-list-info">
              <span class="pred-feature-list-idx">${idx + 1}.</span>
              <div class="pred-feature-list-meta">
                <span class="pred-feature-list-label">${item.label}</span>
                ${item.name ? `<span class="pred-feature-list-code">${item.name}</span>` : ""}
              </div>
            </div>
            <div class="pred-feature-list-val-badge">
              <span class="pred-feature-list-val">${formattedVal}</span>
              <span class="pred-feature-list-unit">${item.unit}</span>
            </div>
          `;
          resFeatureChips.appendChild(row);
        });
      }
    }

    // 7. Update Quick Links to Evaluation and Interpretation
    const startVal = evalStartDate ? evalStartDate.value : "2026-07-29";
    const endVal = evalEndDate ? evalEndDate.value : "2026-08-04";
    const refVal = res.latest_observation_time || "2026-08-04T23:00";
    const queryParams = `location=${encodeURIComponent(res.location)}&pollutant=${encodeURIComponent(res.pollutant)}&scenario=${encodeURIComponent(res.scenario)}&algorithm=${encodeURIComponent(res.algorithm)}&reference_datetime=${encodeURIComponent(refVal)}&start_date=${encodeURIComponent(startVal)}&end_date=${encodeURIComponent(endVal)}`;
    if (btnGotoEvaluation) btnGotoEvaluation.href = `/pages/evaluation.html?${queryParams}`;
    if (btnGotoInterpretation) btnGotoInterpretation.href = `/pages/interpretation.html?${queryParams}`;

    // Smooth scroll to result
    resultSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function showError(msg) {
    statusContainer.style.display = "block";
    statusContainer.innerHTML = `
      <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 1rem; color: #b91c1c; font-size: 0.85rem;">
        <strong>Terjadi Kendala:</strong> ${msg}
      </div>
    `;
  }

  function hideError() {
    statusContainer.style.display = "none";
    statusContainer.innerHTML = "";
  }
});
