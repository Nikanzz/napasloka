"use strict";

/**
 * Controller for Grafik & Evaluasi Model (Precision Matching Chapter 3 Mockup 3) using Plotly.js.
 */
document.addEventListener("DOMContentLoaded", async () => {
  const form = document.getElementById("evaluation-filter-form");
  const btnApply = document.getElementById("btn-apply-eval");
  const statusContainer = document.getElementById("eval-status-container");

  const selectLoc = document.getElementById("eval-select-location");
  const selectPol = document.getElementById("eval-select-pollutant");
  const selectScen = document.getElementById("eval-select-scenario");
  const selectAlgo = document.getElementById("eval-select-algorithm");
  const inputStartDate = document.getElementById("eval-start-date");
  const inputEndDate = document.getElementById("eval-end-date");

  // Hero card elements (Mockup 3)
  const heroHeadlineSub = document.getElementById("hero-headline-sub");
  const heroPredVal = document.getElementById("hero-pred-val");
  const heroPredUnit = document.getElementById("hero-pred-unit");
  const heroLocName = document.getElementById("hero-loc-name");
  const heroModelName = document.getElementById("hero-model-name");
  const heroTimeStamp = document.getElementById("hero-time-stamp");

  // Metric elements
  const valMae = document.getElementById("val-mae");
  const unitMae = document.getElementById("unit-mae");
  const valRmse = document.getElementById("val-rmse");
  const unitRmse = document.getElementById("unit-rmse");
  const valMape = document.getElementById("val-mape");
  const valR2 = document.getElementById("val-r2");

  // Model comparison box elements (Mockup 3 Right Card)
  const selAlgoName = document.getElementById("selected-algo-name");
  const selAlgoRmse = document.getElementById("selected-algo-rmse");
  const cpAlgoName = document.getElementById("counterpart-algo-name");
  const cpAlgoRmse = document.getElementById("counterpart-algo-rmse");

  // Chart
  const chartContainer = document.getElementById("plotly-evaluation-chart");

  let appOptions = null;
  let datasetBounds = null;
  let currentEvalResponse = null;

  // 1. Initialize options & dropdowns
  try {
    appOptions = await window.NapasLokaApi.getOptions();

    // Populate dropdowns
    selectLoc.innerHTML = "";
    appOptions.locations.forEach((loc) => {
      const opt = document.createElement("option");
      opt.value = loc.id;
      opt.textContent = `${loc.name} (${loc.region || "Jabodetabek"})`;
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

    selectAlgo.innerHTML = "";
    appOptions.algorithms.forEach((algo) => {
      const opt = document.createElement("option");
      opt.value = algo.id;
      opt.textContent = algo.label || algo.name;
      selectAlgo.appendChild(opt);
    });

    // Read initial selections from URL or localStorage
    const urlParams = new URLSearchParams(window.location.search);
    const initialLoc = urlParams.get("location") || localStorage.getItem("napasloka_selected_location") || "petamburan-perkantoran-transjakarta";
    const initialPol = urlParams.get("pollutant") || localStorage.getItem("napasloka_selected_pollutant") || "co";
    const initialScen = urlParams.get("scenario") || localStorage.getItem("napasloka_selected_scenario") || "scenario_2";
    let initialAlgo = urlParams.get("algorithm") || localStorage.getItem("napasloka_selected_algorithm") || "lightgbm";
    if (!initialAlgo || initialAlgo === "auto") {
      initialAlgo = "lightgbm";
    }

    if (selectLoc.querySelector(`option[value="${initialLoc}"]`)) selectLoc.value = initialLoc;
    if (selectPol.querySelector(`option[value="${initialPol}"]`)) selectPol.value = initialPol;
    if (selectScen.querySelector(`option[value="${initialScen}"]`)) selectScen.value = initialScen;
    if (selectAlgo.querySelector(`option[value="${initialAlgo}"]`)) selectAlgo.value = initialAlgo;

    const initialStart = urlParams.get("start_date");
    const initialEnd = urlParams.get("end_date");
    if (initialStart && inputStartDate) inputStartDate.value = `${initialStart}T00:00`;
    if (initialEnd && inputEndDate) inputEndDate.value = `${initialEnd}T23:59`;

    // Load available date bounds
    await updateDatasetBounds();

    // Trigger initial evaluation load
    await loadEvaluationData();
  } catch (err) {
    showError("Gagal menginisialisasi parameter evaluasi: " + err.message);
  }

  // Update bounds when location or pollutant changes
  selectLoc.addEventListener("change", async () => {
    await updateDatasetBounds();
  });
  selectPol.addEventListener("change", async () => {
    await updateDatasetBounds();
  });

  async function updateDatasetBounds() {
    try {
      datasetBounds = await window.NapasLokaApi.getEvaluationRange(selectLoc.value, selectPol.value);
    } catch (e) {
      console.warn("Could not fetch dataset bounds:", e);
    }
  }

  function formatDateDisplay(isoStr) {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    const months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
    return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()} · ${`${d.getHours()}`.padStart(2, "0")}:${`${d.getMinutes()}`.padStart(2, "0")}`;
  }

  // Handle form submit
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      await loadEvaluationData();
    });
  }

  async function loadEvaluationData() {
    hideError();
    if (btnApply) {
      btnApply.disabled = true;
      btnApply.innerHTML = '<span>Memproses...</span>';
    }

    const payload = {
      location: selectLoc.value,
      pollutant: selectPol.value,
      scenario: selectScen.value,
      algorithm: selectAlgo.value,
      max_chart_points: 1000,
    };

    if (inputStartDate && inputStartDate.value) {
      payload.start_datetime = inputStartDate.value;
    }
    if (inputEndDate && inputEndDate.value) {
      payload.end_datetime = inputEndDate.value;
    }

    // Save selection
    localStorage.setItem("napasloka_selected_location", payload.location);
    localStorage.setItem("napasloka_selected_pollutant", payload.pollutant);
    localStorage.setItem("napasloka_selected_scenario", payload.scenario);
    localStorage.setItem("napasloka_selected_algorithm", payload.algorithm);

    try {
      const res = await window.NapasLokaApi.postEvaluation(payload);
      currentEvalResponse = res;
      renderEvaluationDashboard(res);
    } catch (err) {
      showError(err.message || "Gagal memproses data evaluasi model.");
    } finally {
      if (btnApply) {
        btnApply.disabled = false;
        btnApply.innerHTML = '<span>Perbarui Tampilan</span>';
      }
    }
  }

  function renderEvaluationDashboard(res) {
    // 1. Top Hero Card (Mockup 3)
    if (heroHeadlineSub) {
      heroHeadlineSub.textContent = `Prediksi ${res.pollutant.toUpperCase()} satu jam berikutnya`;
    }
    if (res.chart_data && res.chart_data.predicted && res.chart_data.predicted.length > 0) {
      const lastPred = res.chart_data.predicted[res.chart_data.predicted.length - 1];
      if (heroPredVal) heroPredVal.textContent = lastPred.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    }
    if (heroPredUnit) heroPredUnit.textContent = res.pollutant_unit;
    if (heroLocName) heroLocName.textContent = res.location_name;

    const algoShortName = res.algorithm === "xgboost" ? "XGBoost" : "LightGBM";
    const scenShortName = res.scenario === "scenario_1" ? "Skenario 1" : "Skenario 2";
    if (heroModelName) heroModelName.textContent = `${algoShortName} · ${scenShortName}`;

    if (heroTimeStamp) {
      try {
        const d = new Date(res.time_range.end);
        d.setHours(d.getHours() + 1);
        heroTimeStamp.textContent = `${formatDateDisplay(d.toISOString())} WIB`;
      } catch {
        heroTimeStamp.textContent = `${formatDateDisplay(res.time_range.end)} WIB`;
      }
    }

    // 2. 4 Metric Cards (Mockup 3)
    if (valMae) valMae.textContent = res.metrics.mae.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (unitMae) unitMae.textContent = res.pollutant_unit;

    if (valRmse) valRmse.textContent = res.metrics.rmse.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (unitRmse) unitRmse.textContent = res.pollutant_unit;

    if (valMape) valMape.textContent = res.metrics.mape.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (valR2) valR2.textContent = res.metrics.r2.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    // Update Quality Badges
    const badgeMae = document.getElementById("badge-mae-quality");
    const badgeRmse = document.getElementById("badge-rmse-quality");
    const badgeMape = document.getElementById("badge-mape-quality");
    const badgeR2 = document.getElementById("badge-r2-quality");
    const humanSummary = document.getElementById("eval-human-summary");
    const btnGotoInterp = document.getElementById("btn-eval-goto-interp");

    if (badgeMape && res.metrics.mape !== undefined) {
      if (res.metrics.mape < 10) {
        badgeMape.textContent = "Akurasi Tinggi";
        badgeMape.className = "badge badge-emerald";
      } else if (res.metrics.mape < 20) {
        badgeMape.textContent = "Akurasi Baik";
        badgeMape.className = "badge badge-blue";
      } else {
        badgeMape.textContent = "Akurasi Cukup";
        badgeMape.className = "badge badge-gray";
      }
    }

    if (badgeR2 && res.metrics.r2 !== undefined) {
      if (res.metrics.r2 >= 0.85) {
        badgeR2.textContent = "Korelasi Sangat Kuat";
        badgeR2.className = "badge badge-emerald";
      } else if (res.metrics.r2 >= 0.70) {
        badgeR2.textContent = "Korelasi Kuat";
        badgeR2.className = "badge badge-blue";
      } else {
        badgeR2.textContent = "Korelasi Moderat";
        badgeR2.className = "badge badge-gray";
      }
    }

    if (humanSummary && res.metrics) {
      const r2Pct = Math.round(res.metrics.r2 * 100);
      const mapeVal = res.metrics.mape.toFixed(1);
      const algoName = res.algorithm_label || "Model terpilih";
      let compNote = "";
      if (res.comparison && res.comparison.counterpart_metrics) {
        const isBetter = res.metrics.rmse <= res.comparison.counterpart_metrics.rmse;
        const diffRmse = Math.abs(res.metrics.rmse - res.comparison.counterpart_metrics.rmse).toFixed(2);
        compNote = isBetter
          ? `Model ${algoName} lebih unggul dibanding ${res.comparison.counterpart_label} dengan margin RMSE ${diffRmse} ${res.pollutant_unit}.`
          : `Model pembanding (${res.comparison.counterpart_label}) memiliki error lebih rendah sebesar ${diffRmse} ${res.pollutant_unit}.`;
      }
      humanSummary.textContent = `${algoName} berhasil menjelaskan ${r2Pct}% variasi polutan (R² = ${res.metrics.r2.toFixed(2)}) dengan deviasi rata-rata ${mapeVal}%. ${compNote}`;
    }

    if (btnGotoInterp) {
      const loc = selectLoc ? selectLoc.value : res.location;
      const pol = selectPol ? selectPol.value : res.pollutant;
      const scen = selectScen ? selectScen.value : res.scenario;
      const algo = selectAlgo ? selectAlgo.value : res.algorithm;
      btnGotoInterp.href = `/pages/interpretation.html?location=${encodeURIComponent(loc)}&pollutant=${encodeURIComponent(pol)}&scenario=${encodeURIComponent(scen)}&algorithm=${encodeURIComponent(algo)}`;
    }

    // 3. Render Plotly Chart
    renderPlotlyChart(res);

    // 4. Comparison Cards (Mockup 3 Right Card)
    if (selAlgoName) selAlgoName.textContent = res.algorithm_label;
    if (selAlgoRmse) selAlgoRmse.textContent = `RMSE ${res.metrics.rmse.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    if (cpAlgoName) cpAlgoName.textContent = res.comparison ? res.comparison.counterpart_label : "Model Pembanding";
    if (cpAlgoRmse && res.comparison) {
      cpAlgoRmse.textContent = `RMSE ${res.comparison.counterpart_metrics.rmse.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    const bestModelPill = document.getElementById("eval-best-model-pill");
    if (bestModelPill && res.best_model_label) {
      bestModelPill.textContent = `⭐ Model Terbaik: ${res.best_model_label}`;
      bestModelPill.title = "Algoritma dengan nilai MAE terendah yang terpilih sebagai final deployment model";
    }
  }


  function renderPlotlyChart(res) {
    if (!chartContainer) return;
    const data = res.chart_data;

    const traceActual = {
      x: data.timestamps,
      y: data.actual,
      name: "Aktual",
      type: "scatter",
      mode: "lines+markers",
      line: { color: "#0c1445", width: 2 },
      marker: { size: 4, color: "#0c1445" },
      hoverinfo: "x+y",
      hoverlabel: {
        bgcolor: "#ffffff",
        bordercolor: "#cbd5e1",
        font: { color: "#0c1445", size: 12, family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" },
      },
    };

    const tracePredicted = {
      x: data.timestamps,
      y: data.predicted,
      name: "Prediksi",
      type: "scatter",
      mode: "lines+markers",
      line: { color: "#2563eb", width: 2, dash: "dash" },
      marker: { size: 4, color: "#2563eb" },
      hoverinfo: "x+y",
      hoverlabel: {
        bgcolor: "#ffffff",
        bordercolor: "#cbd5e1",
        font: { color: "#2563eb", size: 12, family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" },
      },
    };

    const traces = [traceActual, tracePredicted];

    const layout = {
      margin: { t: 15, r: 15, l: 45, b: 35 },
      hovermode: "x unified",
      hoverlabel: {
        bgcolor: "#ffffff",
        bordercolor: "#cbd5e1",
        font: {
          family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          size: 12,
          color: "#0f172a",
        },
        namelength: -1,
      },
      showlegend: false,
      xaxis: {
        showgrid: true,
        gridcolor: "#f1f5f9",
        tickfont: { size: 10, color: "#64748b" },
      },
      yaxis: {
        showgrid: true,
        gridcolor: "#f1f5f9",
        tickfont: { size: 10, color: "#64748b" },
      },
      font: { family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" },
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
    };

    const config = {
      responsive: true,
      displayModeBar: false,
    };

    Plotly.newPlot(chartContainer, traces, layout, config);
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
});
