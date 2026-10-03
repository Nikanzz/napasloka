"use strict";

/**
 * Controller for Konfigurasi Prediksi (Precision Matching Chapter 3 Mockup 1).
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
  const evalStartDate = document.getElementById("eval-start-date");
  const evalEndDate = document.getElementById("eval-end-date");
  const scenarioHintText = document.getElementById("scenario-hint-text");

  // Summary elements (Mockup 1 Right Card)
  const summaryLocName = document.getElementById("summary-location-name");
  const summaryPol = document.getElementById("summary-pollutant");
  const summaryScen = document.getElementById("summary-scenario");
  const summaryAlgo = document.getElementById("summary-algorithm");

  // Result card elements
  const resPollutantTitle = document.getElementById("res-pollutant-title");
  const resTargetTimeBadge = document.getElementById("res-target-time-badge");
  const resAssessmentBadge = document.getElementById("res-assessment-badge");
  const resPredictedVal = document.getElementById("res-predicted-val");
  const resUnit = document.getElementById("res-unit");
  const resAssessmentDesc = document.getElementById("res-assessment-desc");
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

  // 1. Load options and populate dropdowns
  try {
    appOptions = await window.NapasLokaApi.getOptions();

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

    // Populate Algorithm
    selectAlgo.innerHTML = "";
    appOptions.algorithms.forEach((algo) => {
      const opt = document.createElement("option");
      opt.value = algo.id;
      opt.textContent = algo.name || algo.label;
      selectAlgo.appendChild(opt);
    });

    // 2. Pre-select values from URL parameters or localStorage
    const urlParams = new URLSearchParams(window.location.search);
    const initialLoc = urlParams.get("location") || localStorage.getItem("napasloka_selected_location") || "petamburan-perkantoran-transjakarta";
    const initialPol = urlParams.get("pollutant") || localStorage.getItem("napasloka_selected_pollutant") || "co2";
    const initialScen = urlParams.get("scenario") || localStorage.getItem("napasloka_selected_scenario") || "scenario_2";
    const initialAlgo = urlParams.get("algorithm") || localStorage.getItem("napasloka_selected_algorithm") || "lightgbm";

    if (selectLoc.querySelector(`option[value="${initialLoc}"]`)) selectLoc.value = initialLoc;
    if (selectPol.querySelector(`option[value="${initialPol}"]`)) {
      selectPol.value = initialPol;
      // sync segmented buttons
      segmentedBtns.forEach((b) => {
        b.classList.toggle("active", b.getAttribute("data-val") === initialPol);
      });
    }
    if (selectScen.querySelector(`option[value="${initialScen}"]`)) selectScen.value = initialScen;
    if (selectAlgo.querySelector(`option[value="${initialAlgo}"]`)) selectAlgo.value = initialAlgo;

    updateSummaryCard();
    await syncDatasetBounds();

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

  // Sync date bounds when location or pollutant changes
  selectLoc.addEventListener("change", syncDatasetBounds);
  selectPol.addEventListener("change", syncDatasetBounds);

  if (evalEndDate) {
    evalEndDate.addEventListener("change", () => {
      if (evalEndDate.value && inputRefTime) {
        inputRefTime.value = `${evalEndDate.value}T23:00:00`;
      }
    });
  }

  async function syncDatasetBounds() {
    try {
      const bounds = await window.NapasLokaApi.getEvaluationRange(selectLoc.value, selectPol.value);
      if (bounds && evalStartDate && evalEndDate) {
        const startDay = bounds.start.substring(0, 10);
        const endDay = bounds.end.substring(0, 10);
        evalStartDate.min = startDay;
        evalStartDate.max = endDay;
        evalEndDate.min = startDay;
        evalEndDate.max = endDay;

        if (!evalEndDate.value || evalEndDate.value > endDay || evalEndDate.value < startDay) {
          evalEndDate.value = endDay;
        }
        if (!evalStartDate.value || evalStartDate.value < startDay || evalStartDate.value > evalEndDate.value) {
          evalStartDate.value = "2026-07-29";
        }
        if (inputRefTime) {
          inputRefTime.value = `${evalEndDate.value}T23:00:00`;
        }
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
    if (algoObj && summaryAlgo) {
      summaryAlgo.textContent = algoObj.name || algoObj.label;
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
    const refTime = (inputRefTime && inputRefTime.value) ? inputRefTime.value : null;

    // Save to localStorage
    localStorage.setItem("napasloka_selected_location", loc);
    localStorage.setItem("napasloka_selected_pollutant", pol);
    localStorage.setItem("napasloka_selected_scenario", scen);
    localStorage.setItem("napasloka_selected_algorithm", algo);

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

    // Header info
    if (resPollutantTitle) {
      resPollutantTitle.textContent = `Prediksi ${res.pollutant_label} di ${res.location_name}`;
    }
    if (resTargetTimeBadge) {
      resTargetTimeBadge.textContent = `Target: ${res.target_time_display}`;
    }

    // Assessment badge & color
    if (resAssessmentBadge) {
      resAssessmentBadge.textContent = res.assessment.category;
      resAssessmentBadge.style.backgroundColor = res.assessment.color || "#10b981";
      resAssessmentBadge.style.color = "#ffffff";
    }
    if (resAssessmentDesc) {
      resAssessmentDesc.textContent = `${res.assessment.description} (${res.assessment.standard})`;
    }

    // Main prediction values
    if (resPredictedVal) {
      resPredictedVal.textContent = res.predicted_value.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 2 });
    }
    if (resUnit) {
      resUnit.textContent = res.pollutant_unit;
    }

    // Update Quick Links to Evaluation and Interpretation
    const startVal = evalStartDate ? evalStartDate.value : "2026-07-29";
    const endVal = evalEndDate ? evalEndDate.value : "2026-08-04";
    const queryParams = `location=${encodeURIComponent(res.location)}&pollutant=${encodeURIComponent(res.pollutant)}&scenario=${encodeURIComponent(res.scenario)}&algorithm=${encodeURIComponent(res.algorithm)}&start_date=${encodeURIComponent(startVal)}&end_date=${encodeURIComponent(endVal)}`;
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
