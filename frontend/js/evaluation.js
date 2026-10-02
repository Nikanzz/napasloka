"use strict";

/**
 * Controller for Grafik & Evaluasi Model (Evaluation Page) using Plotly.js.
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
  const hintStartDate = document.getElementById("hint-start-date");
  const hintEndDate = document.getElementById("hint-end-date");

  // Hero summary
  const heroModelTitle = document.getElementById("hero-model-title");
  const heroModelSubtitle = document.getElementById("hero-model-subtitle");
  const heroTimeRangeBadge = document.getElementById("hero-time-range-badge");
  const heroSamplesBadge = document.getElementById("hero-samples-badge");

  // Metric elements
  const valMae = document.getElementById("val-mae");
  const unitMae = document.getElementById("unit-mae");
  const valRmse = document.getElementById("val-rmse");
  const unitRmse = document.getElementById("unit-rmse");
  const valMape = document.getElementById("val-mape");
  const valR2 = document.getElementById("val-r2");

  // Chart and toggle
  const chartContainer = document.getElementById("plotly-evaluation-chart");
  const toggleCounterpart = document.getElementById("toggle-counterpart-trace");
  const labelCounterpartToggle = document.getElementById("label-counterpart-toggle");

  // Comparison table elements
  const thPrimary = document.getElementById("th-primary-model");
  const thCounterpart = document.getElementById("th-counterpart-model");
  const winnerBadge = document.getElementById("comparison-winner-badge");
  const summaryText = document.getElementById("comparison-summary-text");

  const cellPriMae = document.getElementById("cell-primary-mae");
  const cellCpMae = document.getElementById("cell-counterpart-mae");
  const cellDiffMae = document.getElementById("cell-diff-mae");
  const cellWinMae = document.getElementById("cell-winner-mae");

  const cellPriRmse = document.getElementById("cell-primary-rmse");
  const cellCpRmse = document.getElementById("cell-counterpart-rmse");
  const cellDiffRmse = document.getElementById("cell-diff-rmse");
  const cellWinRmse = document.getElementById("cell-winner-rmse");

  const cellPriMape = document.getElementById("cell-primary-mape");
  const cellCpMape = document.getElementById("cell-counterpart-mape");
  const cellDiffMape = document.getElementById("cell-diff-mape");
  const cellWinMape = document.getElementById("cell-winner-mape");

  const cellPriR2 = document.getElementById("cell-primary-r2");
  const cellCpR2 = document.getElementById("cell-counterpart-r2");
  const cellDiffR2 = document.getElementById("cell-diff-r2");
  const cellWinR2 = document.getElementById("cell-winner-r2");

  const cellPriTrain = document.getElementById("cell-primary-train-time");
  const cellCpTrain = document.getElementById("cell-counterpart-train-time");
  const cellDiffTrain = document.getElementById("cell-diff-train-time");
  const cellWinTrain = document.getElementById("cell-winner-train-time");

  // Quick Links
  const btnGotoPrediction = document.getElementById("btn-eval-goto-prediction");
  const btnGotoInterpretation = document.getElementById("btn-eval-goto-interpretation");

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
      opt.textContent = `${sc.label} (${sc.feature_count || (sc.id === "scenario_1" ? 3 : 15)} Fitur)`;
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
    const initialLoc = urlParams.get("location") || localStorage.getItem("napasloka_selected_location") || "taman-kamal";
    const initialPol = urlParams.get("pollutant") || localStorage.getItem("napasloka_selected_pollutant") || "co";
    const initialScen = urlParams.get("scenario") || localStorage.getItem("napasloka_selected_scenario") || "scenario_1";
    const initialAlgo = urlParams.get("algorithm") || localStorage.getItem("napasloka_selected_algorithm") || "xgboost";

    if (selectLoc.querySelector(`option[value="${initialLoc}"]`)) selectLoc.value = initialLoc;
    if (selectPol.querySelector(`option[value="${initialPol}"]`)) selectPol.value = initialPol;
    if (selectScen.querySelector(`option[value="${initialScen}"]`)) selectScen.value = initialScen;
    if (selectAlgo.querySelector(`option[value="${initialAlgo}"]`)) selectAlgo.value = initialAlgo;

    // Load available date bounds for the initial location
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
      if (datasetBounds) {
        const startStr = datasetBounds.start.substring(0, 16);
        const endStr = datasetBounds.end.substring(0, 16);
        inputStartDate.min = startStr;
        inputStartDate.max = endStr;
        inputEndDate.min = startStr;
        inputEndDate.max = endStr;

        hintStartDate.textContent = `Batas awal: ${formatDateDisplay(datasetBounds.start)}`;
        hintEndDate.textContent = `Batas akhir: ${formatDateDisplay(datasetBounds.end)}`;
      }
    } catch (e) {
      console.warn("Could not fetch dataset bounds:", e);
    }
  }

  // Handle Preset Buttons
  document.querySelectorAll(".preset-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".preset-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      if (!datasetBounds) return;
      const endDateObj = new Date(datasetBounds.end);
      const preset = btn.getAttribute("data-preset");

      if (preset === "all") {
        inputStartDate.value = "";
        inputEndDate.value = "";
      } else {
        const days = preset === "30d" ? 30 : preset === "14d" ? 14 : 7;
        const startDateObj = new Date(endDateObj.getTime() - days * 24 * 60 * 60 * 1000);

        inputStartDate.value = toLocalISOString(startDateObj);
        inputEndDate.value = toLocalISOString(endDateObj);
      }
    });
  });

  function toLocalISOString(date) {
    const pad = (n) => `${n}`.padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  function formatDateDisplay(isoStr) {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
    return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}, ${`${d.getHours()}`.padStart(2, "0")}:${`${d.getMinutes()}`.padStart(2, "0")}`;
  }

  // Handle form submit
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await loadEvaluationData();
  });

  async function loadEvaluationData() {
    hideError();
    btnApply.disabled = true;
    const originalText = btnApply.innerHTML;
    btnApply.innerHTML = '<span class="spinner"></span> <span>Memproses...</span>';

    const payload = {
      location: selectLoc.value,
      pollutant: selectPol.value,
      scenario: selectScen.value,
      algorithm: selectAlgo.value,
      max_chart_points: 1500,
    };

    if (inputStartDate.value) {
      payload.start_datetime = inputStartDate.value;
    }
    if (inputEndDate.value) {
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
      btnApply.disabled = false;
      btnApply.innerHTML = originalText;
    }
  }

  function renderEvaluationDashboard(res) {
    // 1. Hero Card
    heroModelTitle.textContent = `${res.algorithm_label} · ${res.pollutant_label} di ${res.location_name}`;
    heroModelSubtitle.textContent = `${res.scenario_label} · Wilayah: ${res.region}`;
    heroTimeRangeBadge.textContent = `${formatDateDisplay(res.time_range.start)} — ${formatDateDisplay(res.time_range.end)}`;
    heroSamplesBadge.textContent = `Dievaluasi pada ${res.time_range.evaluated_samples.toLocaleString("id-ID")} dari ${res.time_range.total_test_samples.toLocaleString("id-ID")} sampel data uji`;

    // 2. Metric Cards
    valMae.textContent = res.metrics.mae.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    unitMae.textContent = res.pollutant_unit;

    valRmse.textContent = res.metrics.rmse.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    unitRmse.textContent = res.pollutant_unit;

    valMape.textContent = `${res.metrics.mape.toFixed(2)}%`;
    valR2.textContent = res.metrics.r2.toFixed(4);

    // 3. Render Plotly Chart
    renderPlotlyChart(res);

    // 4. Comparison Table
    if (res.comparison) {
      renderComparisonCard(res.comparison, res.metrics, res.pollutant_unit);
    }

    // 5. Update Quick Links
    const queryParams = `location=${encodeURIComponent(res.location)}&pollutant=${encodeURIComponent(res.pollutant)}&scenario=${encodeURIComponent(res.scenario)}&algorithm=${encodeURIComponent(res.algorithm)}`;
    btnGotoPrediction.href = `/pages/prediction.html?${queryParams}`;
    btnGotoInterpretation.href = `/pages/interpretation.html?${queryParams}`;
  }

  function renderPlotlyChart(res) {
    const data = res.chart_data;
    const counterpartAlgo = res.comparison ? res.comparison.counterpart_label : "Model Pembanding";
    labelCounterpartToggle.textContent = counterpartAlgo;

    const traceActual = {
      x: data.timestamps,
      y: data.actual,
      name: "Nilai Aktual",
      type: "scatter",
      mode: "lines",
      line: { color: "#334155", width: 2 },
      hoverinfo: "x+y",
    };

    const tracePredicted = {
      x: data.timestamps,
      y: data.predicted,
      name: `Prediksi ${res.algorithm_label}`,
      type: "scatter",
      mode: "lines",
      line: { color: "#0f766e", width: 2.5 },
      hoverinfo: "x+y",
    };

    const traces = [traceActual, tracePredicted];

    if (data.counterpart_predicted && data.counterpart_predicted.length > 0) {
      const traceCounterpart = {
        x: data.timestamps,
        y: data.counterpart_predicted,
        name: `Prediksi ${counterpartAlgo}`,
        type: "scatter",
        mode: "lines",
        line: { color: "#d97706", width: 1.8, dash: "dot" },
        visible: toggleCounterpart.checked ? true : "legendonly",
        hoverinfo: "x+y",
      };
      traces.push(traceCounterpart);
    }

    const layout = {
      margin: { t: 30, r: 25, l: 60, b: 50 },
      hovermode: "x unified",
      showlegend: true,
      legend: {
        orientation: "h",
        yanchor: "bottom",
        y: 1.02,
        xanchor: "right",
        x: 1,
        font: { family: "Inter, sans-serif", size: 12 },
      },
      xaxis: {
        title: { text: "Waktu Observasi Data Uji", font: { size: 12, color: "#64748b" } },
        showgrid: true,
        gridcolor: "#f1f5f9",
        tickfont: { size: 11, color: "#475569" },
      },
      yaxis: {
        title: { text: `Konsentrasi (${res.pollutant_unit})`, font: { size: 12, color: "#64748b" } },
        showgrid: true,
        gridcolor: "#f1f5f9",
        tickfont: { size: 11, color: "#475569" },
      },
      font: { family: "Inter, sans-serif" },
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
    };

    const config = {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ["lasso2d", "select2d"],
    };

    Plotly.newPlot(chartContainer, traces, layout, config);
  }

  // Toggle Counterpart Trace visibility in Plotly
  toggleCounterpart.addEventListener("change", () => {
    if (!chartContainer.data || chartContainer.data.length < 3) return;
    const isVisible = toggleCounterpart.checked;
    Plotly.restyle(chartContainer, { visible: isVisible }, [2]);
  });

  function renderComparisonCard(comp, priMetrics, unit) {
    thPrimary.textContent = comp.primary_label;
    thCounterpart.textContent = comp.counterpart_label;

    winnerBadge.textContent = `${comp.winner === comp.primary_algorithm ? comp.primary_label : comp.counterpart_label} Unggul`;

    // MAE
    cellPriMae.textContent = `${comp.primary_metrics.mae.toFixed(2)} ${unit}`;
    cellCpMae.textContent = `${comp.counterpart_metrics.mae.toFixed(2)} ${unit}`;
    const maeSign = comp.mae_diff_pct >= 0 ? "+" : "";
    cellDiffMae.textContent = `${maeSign}${comp.mae_diff_pct.toFixed(1)}% (${comp.mae_diff_pct >= 0 ? "lebih rendah" : "lebih tinggi"})`;
    cellDiffMae.className = comp.mae_diff_pct >= 0 ? "diff-positive" : "diff-negative";
    if (comp.primary_metrics.mae <= comp.counterpart_metrics.mae) {
      cellPriMae.className = "winner-cell";
      cellCpMae.className = "";
      cellWinMae.textContent = comp.primary_label;
    } else {
      cellCpMae.className = "winner-cell";
      cellPriMae.className = "";
      cellWinMae.textContent = comp.counterpart_label;
    }

    // RMSE
    cellPriRmse.textContent = `${comp.primary_metrics.rmse.toFixed(2)} ${unit}`;
    cellCpRmse.textContent = `${comp.counterpart_metrics.rmse.toFixed(2)} ${unit}`;
    const rmseSign = comp.rmse_diff_pct >= 0 ? "+" : "";
    cellDiffRmse.textContent = `${rmseSign}${comp.rmse_diff_pct.toFixed(1)}%`;
    cellDiffRmse.className = comp.rmse_diff_pct >= 0 ? "diff-positive" : "diff-negative";
    if (comp.primary_metrics.rmse <= comp.counterpart_metrics.rmse) {
      cellPriRmse.className = "winner-cell";
      cellCpRmse.className = "";
      cellWinRmse.textContent = comp.primary_label;
    } else {
      cellCpRmse.className = "winner-cell";
      cellPriRmse.className = "";
      cellWinRmse.textContent = comp.counterpart_label;
    }

    // MAPE
    cellPriMape.textContent = `${comp.primary_metrics.mape.toFixed(2)}%`;
    cellCpMape.textContent = `${comp.counterpart_metrics.mape.toFixed(2)}%`;
    const mapeSign = comp.mape_diff >= 0 ? "+" : "";
    cellDiffMape.textContent = `${mapeSign}${comp.mape_diff.toFixed(2)}% poin`;
    cellDiffMape.className = comp.mape_diff >= 0 ? "diff-positive" : "diff-negative";
    if (comp.primary_metrics.mape <= comp.counterpart_metrics.mape) {
      cellPriMape.className = "winner-cell";
      cellCpMape.className = "";
      cellWinMape.textContent = comp.primary_label;
    } else {
      cellCpMape.className = "winner-cell";
      cellPriMape.className = "";
      cellWinMape.textContent = comp.counterpart_label;
    }

    // R2
    cellPriR2.textContent = comp.primary_metrics.r2.toFixed(4);
    cellCpR2.textContent = comp.counterpart_metrics.r2.toFixed(4);
    const r2Sign = comp.r2_diff >= 0 ? "+" : "";
    cellDiffR2.textContent = `${r2Sign}${comp.r2_diff.toFixed(4)}`;
    cellDiffR2.className = comp.r2_diff >= 0 ? "diff-positive" : "diff-negative";
    if (comp.primary_metrics.r2 >= comp.counterpart_metrics.r2) {
      cellPriR2.className = "winner-cell";
      cellCpR2.className = "";
      cellWinR2.textContent = comp.primary_label;
    } else {
      cellCpR2.className = "winner-cell";
      cellPriR2.className = "";
      cellWinR2.textContent = comp.counterpart_label;
    }

    // Durations
    const priTrainTime = comp.primary_metrics.training_time_seconds ? `${comp.primary_metrics.training_time_seconds.toFixed(2)}s` : "-";
    const cpTrainTime = comp.counterpart_metrics.training_time_seconds ? `${comp.counterpart_metrics.training_time_seconds.toFixed(2)}s` : "-";
    cellPriTrain.textContent = priTrainTime;
    cellCpTrain.textContent = cpTrainTime;
    cellDiffTrain.textContent = "-";
    cellWinTrain.textContent = (comp.primary_metrics.training_time_seconds || 0) <= (comp.counterpart_metrics.training_time_seconds || 0)
      ? comp.primary_label : comp.counterpart_label;

    // Narrative Summary
    summaryText.textContent = comp.summary;
  }

  function showError(msg) {
    statusContainer.style.display = "block";
    statusContainer.innerHTML = `
      <div class="alert alert-warning" role="alert">
        <div class="alert-icon">⚠️</div>
        <div class="alert-content">
          <h4>Terjadi Kendala Evaluasi</h4>
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
