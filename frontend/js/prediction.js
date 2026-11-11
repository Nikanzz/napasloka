"use strict";

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

  const segmentedBtns = document.querySelectorAll("#pollutant-segmented .segmented-btn");
  segmentedBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      segmentedBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      selectPol.value = btn.getAttribute("data-val");
      selectPol.dispatchEvent(new Event("change"));
    });
  });

  let appOptions = null;
  let bestModelsRegistry = null;
  let latestObsTimestamp = "2026-08-04T23:00";

  const fmt = (n, d = 2) => (n != null && !isNaN(n) ? Number(n).toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: d }) : "-");

  function setElText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function formatIndoTime(isoStr) {
    if (!isoStr) return "-";
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
      const day = String(d.getDate()).padStart(2, "0");
      const hours = String(d.getHours()).padStart(2, "0");
      const mins = String(d.getMinutes()).padStart(2, "0");
      return `${day} ${months[d.getMonth()]} ${d.getFullYear()}, ${hours}:${mins} WIB`;
    } catch {
      return isoStr;
    }
  }

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

  function updateAlgorithmDisplay() {
    const loc = selectLoc?.value || "";
    const pol = selectPol?.value || "";
    const scen = selectScen?.value || "";
    const key = `${loc}__${pol}__${scen}`;
    let winnerAlgo = "LightGBM";
    if (bestModelsRegistry?.best_models?.[key]) {
      const entry = bestModelsRegistry.best_models[key];
      winnerAlgo = entry.best_algorithm?.toLowerCase() === "xgboost" ? "XGBoost" : "LightGBM";
    }
    if (selectAlgo) {
      selectAlgo.innerHTML = `<option value="auto" selected>Otomatis: ${winnerAlgo} (Model Terbaik — Final Deployment)</option>`;
      selectAlgo.disabled = true;
    }
    return winnerAlgo;
  }

  function showError(msg) {
    if (!statusContainer) return;
    statusContainer.style.display = "block";
    statusContainer.innerHTML = `
      <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 1rem; color: #b91c1c; font-size: 0.85rem;">
        <strong>Terjadi Kendala:</strong> ${msg}
      </div>
    `;
  }

  function hideError() {
    if (!statusContainer) return;
    statusContainer.style.display = "none";
    statusContainer.innerHTML = "";
  }

  try {
    appOptions = await window.NapasLokaApi.getOptions();

    try {
      bestModelsRegistry = await window.NapasLokaApi.getBestModels();
    } catch (e) {
      console.warn("Gagal memuat registri model terbaik:", e);
    }

    selectLoc.innerHTML = "";
    appOptions.locations.forEach((loc) => {
      const opt = document.createElement("option");
      opt.value = loc.id;
      opt.textContent = loc.name;
      selectLoc.appendChild(opt);
    });

    selectPol.innerHTML = "";
    appOptions.pollutants.forEach((pol) => {
      const opt = document.createElement("option");
      opt.value = pol.id;
      opt.textContent = `${pol.label} [${pol.unit}]`;
      selectPol.appendChild(opt);
    });

    selectScen.innerHTML = "";
    appOptions.scenarios.forEach((sc) => {
      const opt = document.createElement("option");
      opt.value = sc.id;
      opt.textContent = sc.id === "scenario_1" ? "S1 · Historis polutan" : "S2 · Polutan + meteorologi";
      selectScen.appendChild(opt);
    });

    updateAlgorithmDisplay();

    const urlParams = new URLSearchParams(window.location.search);
    const initialLoc = urlParams.get("location") || localStorage.getItem("napasloka_selected_location") || "petamburan-perkantoran-transjakarta";
    const initialPol = urlParams.get("pollutant") || localStorage.getItem("napasloka_selected_pollutant") || "co2";
    const initialScen = urlParams.get("scenario") || localStorage.getItem("napasloka_selected_scenario") || "scenario_2";
    const initialRefTime = urlParams.get("reference_datetime") || urlParams.get("end_date");

    if (selectLoc.querySelector(`option[value="${initialLoc}"]`)) selectLoc.value = initialLoc;
    if (selectPol.querySelector(`option[value="${initialPol}"]`)) {
      selectPol.value = initialPol;
      segmentedBtns.forEach((b) => b.classList.toggle("active", b.getAttribute("data-val") === initialPol));
    }
    if (selectScen.querySelector(`option[value="${initialScen}"]`)) selectScen.value = initialScen;

    updateAlgorithmDisplay();
    await syncDatasetBounds();

    if (initialRefTime && inputRefTime) {
      inputRefTime.value = initialRefTime.includes("T") ? initialRefTime.substring(0, 16) : `${initialRefTime}T23:00`;
    }

    updateSummaryCard();
  } catch (err) {
    showError("Gagal menginisialisasi parameter sistem: " + err.message);
  }

  [selectLoc, selectPol, selectScen].forEach((el) => {
    el?.addEventListener("change", () => {
      updateAlgorithmDisplay();
      updateSummaryCard();
    });
  });

  selectLoc?.addEventListener("change", syncDatasetBounds);
  selectPol?.addEventListener("change", syncDatasetBounds);

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
    if (!inputRefTime?.value) return;
    const datePart = inputRefTime.value.substring(0, 10);
    if (evalEndDate) evalEndDate.value = datePart;
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
        latestObsTimestamp = `${endDay}T23:00`;

        if (inputRefTime) {
          inputRefTime.value = "";
          inputRefTime.disabled = true;
        }

        const refHint = document.getElementById("ref-time-hint");
        if (refHint) {
          refHint.innerHTML = `<span style="color: var(--color-primary); font-weight: 600;">✓ Prediksi Real-Time Aktif</span> &mdash; Mengambil observasi atmosfer jam terkini dari Open-Meteo untuk memproyeksikan 1 jam ke depan.`;
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
      console.warn("Gagal sinkronisasi rentang dataset:", e);
    }
  }

  function updateSummaryCard() {
    if (!appOptions) return;
    const locObj = appOptions.locations.find((l) => l.id === selectLoc.value);
    const polObj = appOptions.pollutants.find((p) => p.id === selectPol.value);
    const scenObj = appOptions.scenarios.find((s) => s.id === selectScen.value);

    if (locObj) setElText("summary-location-name", locObj.name);
    if (polObj) setElText("summary-pollutant", `${polObj.symbol} · ${polObj.unit}`);

    if (scenObj) {
      const isS1 = scenObj.id === "scenario_1";
      setElText("summary-scenario", isS1 ? "Historis polutan" : "Polutan + meteorologi");
      if (scenarioHintText) {
        scenarioHintText.textContent = isS1
          ? "Fitur lag 3 jam historis konsentrasi polutan."
          : "Fitur lag polutan digabungkan dengan kondisi meteorologis.";
      }
    }

    const winnerAlgo = updateAlgorithmDisplay();
    setElText("summary-algorithm", `${winnerAlgo} (Model Terbaik)`);
    setElText("summary-model-status", "Final deployment model");

    const isCustom = inputRefTime && !inputRefTime.disabled && inputRefTime.value;
    if (isCustom) {
      setElText("summary-ref-time", formatIndoTime(inputRefTime.value));
      setElText("summary-target-time", formatIndoTime(calculateTargetIso(inputRefTime.value)));
    } else {
      setElText("summary-ref-time", "Data Terkini (Real-time)");
      setElText("summary-target-time", "+1 Jam ke Depan");
    }
  }

  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      executePrediction();
    });
  }

  async function executePrediction() {
    hideError();
    const loc = selectLoc.value;
    const pol = selectPol.value;
    const scen = selectScen.value;
    const isCustom = inputRefTime && !inputRefTime.disabled && inputRefTime.value;

    localStorage.setItem("napasloka_selected_location", loc);
    localStorage.setItem("napasloka_selected_pollutant", pol);
    localStorage.setItem("napasloka_selected_scenario", scen);
    localStorage.setItem("napasloka_selected_algorithm", "auto");

    submitBtn.disabled = true;
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = "<span>Memproses Prediksi...</span>";

    try {
      const payload = { location: loc, pollutant: pol, scenario: scen, algorithm: "auto" };
      if (isCustom) {
        payload.reference_datetime = inputRefTime.value;
      } else if (navigator.onLine && appOptions?.locations) {
        const locObj = appOptions.locations.find((l) => l.id === loc);
        if (locObj && locObj.latitude && locObj.longitude) {
          submitBtn.innerHTML = "<span>Mengambil Cuaca Jam Ini...</span>";
          const clientLive = await window.NapasLokaApi.fetchClientLiveFeatures(
            locObj.latitude,
            locObj.longitude,
            pol,
            scen
          );
          if (clientLive) {
            payload.client_live_features = clientLive;
          }
        }
      }

      submitBtn.innerHTML = "<span>Memproses Model Prediksi...</span>";
      const res = await window.NapasLokaApi.postPrediction(payload);
      renderPredictionResult(res);
    } catch (err) {
      showError(err.message || "Gagal memproses prediksi satu jam berikutnya.");
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  }

  // Configuration constants for status evaluation thresholds and reference standards
  const STATUS_CONFIG = Object.freeze({
    CO: {
      HALF_THRESHOLD: 5000,
      LIMIT_THRESHOLD: 10000,
      STANDARD_NAME: "Rujukan: PP No. 22 Tahun 2021 (Baku Mutu CO 1 Jam: 10.000 µg/m³)",
    },
    CO2: {
      Q1: 449,
      Q3: 472,
      STANDARD_NAME: "Rujukan: Distribusi empiris data referensi Jabodetabek (Q1 = 449 ppm, Q3 = 472 ppm)",
    },
  });

  function renderPredictionResult(res) {
    if (resultSection) resultSection.style.display = "block";

    setElText("res-pollutant-title", `Prediksi ${res.pollutant_label} di ${res.location_name}`);

    // Direct if-else condition for concentration status
    const pol = (res.pollutant || "co").toLowerCase();
    const val = Number(res.predicted_value) || 0;

    let catLabel = "";
    let catColor = "#10b981";
    let catStandard = "";
    let catDesc = "";
    let showDisclaimer = false;

    if (pol === "co") {
      catStandard = STATUS_CONFIG.CO.STANDARD_NAME;

      if (val <= STATUS_CONFIG.CO.HALF_THRESHOLD) {
        catLabel = "Memenuhi Baku Mutu";
        catColor = "#10b981";
        catDesc = "Konsentrasi berada di bawah 50% dari baku mutu CO 1 jam nasional.";
      } else if (val <= STATUS_CONFIG.CO.LIMIT_THRESHOLD) {
        catLabel = "Mendekati Baku Mutu";
        catColor = "#f59e0b";
        catDesc = "Konsentrasi masih memenuhi baku mutu CO 1 jam nasional.";
      } else {
        catLabel = "Melebihi Baku Mutu";
        catColor = "#ef4444";
        catDesc = "Konsentrasi melebihi baku mutu CO 1 jam nasional sebesar 10.000 µg/m³.";
      }
    } else {
      catStandard = STATUS_CONFIG.CO2.STANDARD_NAME;
      showDisclaimer = true;

      if (val <= STATUS_CONFIG.CO2.Q1) {
        catLabel = "Rendah Relatif";
        catColor = "#10b981";
        catDesc = "Termasuk dalam 25% konsentrasi terendah berdasarkan distribusi empiris data referensi Jabodetabek.";
      } else if (val <= STATUS_CONFIG.CO2.Q3) {
        catLabel = "Tipikal Relatif";
        catColor = "#3b82f6";
        catDesc = "Berada dalam rentang 50% nilai pusat distribusi historis Jabodetabek (Interquartile Range).";
      } else {
        catLabel = "Tinggi Relatif";
        catColor = "#ef4444";
        catDesc = "Termasuk dalam 25% konsentrasi tertinggi berdasarkan distribusi empiris data referensi Jabodetabek.";
      }
    }

    const statusBadge = document.getElementById("res-status-badge");
    if (statusBadge) {
      statusBadge.textContent = catLabel;
      statusBadge.style.backgroundColor = catColor;
      statusBadge.style.color = "#ffffff";
      statusBadge.style.display = "inline-block";
    }

    const statusStandard = document.getElementById("res-status-standard");
    if (statusStandard) {
      statusStandard.textContent = catStandard;
    }

    const statusDesc = document.getElementById("res-status-desc");
    if (statusDesc) {
      statusDesc.textContent = catDesc;
    }

    const statusDisclaimer = document.getElementById("res-status-disclaimer");
    if (statusDisclaimer) {
      statusDisclaimer.style.display = showDisclaimer ? "block" : "none";
    }

    const badge = document.getElementById("res-assessment-badge");
    if (badge) {
      badge.textContent = catLabel;
      badge.style.backgroundColor = catColor;
      badge.style.color = "#ffffff";
      badge.style.display = "inline-block";
    }

    const resHorizonBadge = document.getElementById("res-horizon-badge");
    if (resHorizonBadge) {
      resHorizonBadge.textContent = res.is_live_data ? "🟢 Live Open-Meteo (t+1)" : "Estimasi Horizon (t+1)";
      resHorizonBadge.style.backgroundColor = res.is_live_data ? "#ecfdf5" : "#eff6ff";
      resHorizonBadge.style.color = res.is_live_data ? "#047857" : "#1d4ed8";
    }

    const refHint = document.getElementById("ref-time-hint");
    if (refHint && res.latest_observation_display && res.target_time_display) {
      if (res.is_live_data) {
        refHint.innerHTML = `<span style="color: #059669; font-weight: 600;">🟢 Live Data Open-Meteo</span> &mdash; Acuan (t): <strong>${res.latest_observation_display}</strong> &rarr; Target (t+1): <strong>${res.target_time_display}</strong>`;
      } else {
        const errDetail = res.live_data_error ? ` (${res.live_data_error})` : "";
        refHint.innerHTML = `<span style="color: #d97706; font-weight: 600;">⚠️ Data Acuan Historis (Fallback)</span> &mdash; Acuan (t): <strong>${res.latest_observation_display}</strong> &rarr; Target (t+1): <strong>${res.target_time_display}</strong><span style="display:block; font-size:0.75rem; color: var(--color-text-muted);">${errDetail ? "Koneksi stasiun luar: " + errDetail : "Menggunakan observasi historis dataset."}</span>`;
      }
    }

    setElText("res-latest-time", res.latest_observation_display || formatIndoTime(res.latest_observation_time));
    setElText("res-latest-val", fmt(res.latest_observation_value));
    setElText("res-latest-unit", res.pollutant_unit);
    setElText("res-target-time-badge", res.target_time_display || formatIndoTime(res.target_time));
    setElText("res-target-summary-val", fmt(res.predicted_value));
    setElText("res-target-summary-unit", res.pollutant_unit);

    setElText("res-predicted-val", fmt(res.predicted_value));
    setElText("res-unit", res.pollutant_unit);

    const deltaSign = res.delta_value > 0 ? "+" : "";
    const pctSign = res.delta_percentage > 0 ? "+" : "";
    setElText("res-delta-val", `${deltaSign}${fmt(res.delta_value)} ${res.pollutant_unit}`);
    setElText("res-delta-pct", `(${pctSign}${Number(res.delta_percentage).toFixed(2)}%)`);

    const resTrendBadge = document.getElementById("res-trend-badge");
    if (resTrendBadge) {
      resTrendBadge.className = `pred-trend-pill trend-${res.trend}`;
      setElText("res-trend-label", res.trend.charAt(0).toUpperCase() + res.trend.slice(1));
      const icon = document.getElementById("res-trend-icon");
      if (icon) icon.innerHTML = res.trend === "naik" ? "&#9650;" : res.trend === "turun" ? "&#9660;" : "&#9679;";
    }

    setElText("res-standard-ref", catStandard);
    setElText("res-assessment-desc", catDesc);

    const meterFill = document.getElementById("res-meter-fill");
    const meterLabels = document.getElementById("res-meter-labels");
    if (meterFill) {
      let fillPct = 50;
      if (res.pollutant === "co") {
        fillPct = Math.min(100, Math.max(5, (res.predicted_value / STATUS_CONFIG.CO.LIMIT_THRESHOLD) * 100));
        if (meterLabels) meterLabels.innerHTML = "<span>Memenuhi (&le; 5k)</span><span>Mendekati (5k-10k)</span><span>Melebihi (> 10k µg/m³)</span>";
      } else {
        fillPct = Math.min(100, Math.max(5, ((res.predicted_value - 420) / (520 - 420)) * 100));
        if (meterLabels) meterLabels.innerHTML = "<span>Rendah (&le; 449)</span><span>Tipikal (449-472)</span><span>Tinggi (> 472 ppm)</span>";
      }
      meterFill.style.width = `${fillPct.toFixed(1)}%`;
      meterFill.style.backgroundColor = catColor;
    }

    setElText("res-active-algo-name", `${res.algorithm_label} (${res.model_status})`);
    setElText("res-active-algo-val", `${fmt(res.predicted_value)} ${res.pollutant_unit}`);
    setElText("res-counterpart-label", res.counterpart_label);

    if (res.counterpart_predicted_value != null) {
      setElText("res-counterpart-val", `${fmt(res.counterpart_predicted_value)} ${res.pollutant_unit}`);
      const cpDeltaSign = res.counterpart_delta > 0 ? "+" : "";
      setElText("res-counterpart-delta", `Selisih: ${cpDeltaSign}${fmt(res.counterpart_delta)} ${res.pollutant_unit}`);
      const absDiff = Math.abs(res.counterpart_delta);
      const pctDiff = (absDiff / (res.predicted_value || 1)) * 100;
      setElText("res-counterpart-agreement", pctDiff < 2 ? `Deviasi ${pctDiff.toFixed(1)}% · Konsensus kedua model sangat tinggi` : `Deviasi ${pctDiff.toFixed(1)}% · Terdapat variasi estimasi antar model`);
    }

    setElText("res-features-count", res.feature_inputs ? res.feature_inputs.length : 0);
    const featureChips = document.getElementById("res-feature-chips");
    if (featureChips && res.feature_inputs?.length) {
      featureChips.innerHTML = "";
      res.feature_inputs.forEach((item, idx) => {
        const row = document.createElement("div");
        row.className = "pred-feature-list-row";
        row.innerHTML = `
          <div class="pred-feature-list-info">
            <span class="pred-feature-list-idx">${idx + 1}.</span>
            <div class="pred-feature-list-meta">
              <span class="pred-feature-list-label">${item.label}</span>
              ${item.name ? `<span class="pred-feature-list-code">${item.name}</span>` : ""}
            </div>
          </div>
          <div class="pred-feature-list-val-badge">
            <span class="pred-feature-list-val">${fmt(item.value)}</span>
            <span class="pred-feature-list-unit">${item.unit}</span>
          </div>
        `;
        featureChips.appendChild(row);
      });
    }

    const startVal = evalStartDate?.value || "2026-07-29";
    const endVal = evalEndDate?.value || "2026-08-04";
    const refVal = res.latest_observation_time || "2026-08-04T23:00";
    const liveParam = res.is_live_data ? "&live=true" : "";
    const queryParams = `location=${encodeURIComponent(res.location)}&pollutant=${encodeURIComponent(res.pollutant)}&scenario=${encodeURIComponent(res.scenario)}&algorithm=${encodeURIComponent(res.algorithm)}&reference_datetime=${encodeURIComponent(refVal)}&start_date=${encodeURIComponent(startVal)}&end_date=${encodeURIComponent(endVal)}${liveParam}`;

    const btnGotoEval = document.getElementById("btn-goto-evaluation");
    const btnGotoInterp = document.getElementById("btn-goto-interpretation");
    if (btnGotoEval) btnGotoEval.href = `/pages/evaluation.html?${queryParams}`;
    if (btnGotoInterp) btnGotoInterp.href = `/pages/interpretation.html?${queryParams}`;

    resultSection?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
});
