"use strict";

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
  const chartContainer = document.getElementById("plotly-evaluation-chart");

  const fmt = (n, d = 2) => (n != null && !isNaN(n) ? Number(n).toLocaleString("id-ID", { minimumFractionDigits: d, maximumFractionDigits: d }) : "-");

  function formatDateForInput(dateObj) {
    const year = dateObj.getFullYear();
    const month = String(dateObj.getMonth() + 1).padStart(2, "0");
    const day = String(dateObj.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function formatDateShort(isoStr) {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
    return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
  }

  function formatDateDisplay(isoStr) {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    const months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
    const h = String(d.getHours()).padStart(2, "0");
    const m = String(d.getMinutes()).padStart(2, "0");
    return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()} · ${h}:${m}`;
  }

  function setElText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
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
    const appOptions = await window.NapasLokaApi.getOptions();

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

    const urlParams = new URLSearchParams(window.location.search);
    const initialLoc = urlParams.get("location") || localStorage.getItem("napasloka_selected_location") || "petamburan-perkantoran-transjakarta";
    const initialPol = urlParams.get("pollutant") || localStorage.getItem("napasloka_selected_pollutant") || "co";
    const initialScen = urlParams.get("scenario") || localStorage.getItem("napasloka_selected_scenario") || "scenario_2";
    let initialAlgo = urlParams.get("algorithm") || localStorage.getItem("napasloka_selected_algorithm") || "lightgbm";
    if (initialAlgo === "auto") initialAlgo = "lightgbm";

    if (selectLoc.querySelector(`option[value="${initialLoc}"]`)) selectLoc.value = initialLoc;
    if (selectPol.querySelector(`option[value="${initialPol}"]`)) selectPol.value = initialPol;
    if (selectScen.querySelector(`option[value="${initialScen}"]`)) selectScen.value = initialScen;
    if (selectAlgo.querySelector(`option[value="${initialAlgo}"]`)) selectAlgo.value = initialAlgo;

    const initialStart = urlParams.get("start_date");
    const initialEnd = urlParams.get("end_date");
    let latestDatasetEnd = null;

    try {
      const rangeInfo = await window.NapasLokaApi.getEvaluationRange(selectLoc.value, selectPol.value);
      if (rangeInfo?.end) {
        latestDatasetEnd = new Date(rangeInfo.end);
        if (!initialStart && !initialEnd && inputStartDate && inputEndDate) {
          const defaultStart = new Date(latestDatasetEnd.getTime() - 7 * 24 * 60 * 60 * 1000);
          inputStartDate.value = formatDateForInput(defaultStart);
          inputEndDate.value = formatDateForInput(latestDatasetEnd);
        }
      }
    } catch {
    }

    if (initialStart && inputStartDate) inputStartDate.value = initialStart;
    if (initialEnd && inputEndDate) inputEndDate.value = initialEnd;

    const presetButtons = document.querySelectorAll(".btn-eval-preset");
    const btnResetDates = document.getElementById("btn-reset-dates");

    function setActivePresetButton(activeDays) {
      presetButtons.forEach((btn) => {
        if (btn.getAttribute("data-days") === String(activeDays)) {
          btn.classList.add("active");
        } else {
          btn.classList.remove("active");
        }
      });
    }

    presetButtons.forEach((btn) => {
      btn.addEventListener("click", async () => {
        const days = btn.getAttribute("data-days");
        if (days === "all") {
          if (inputStartDate) inputStartDate.value = "";
          if (inputEndDate) inputEndDate.value = "";
          setActivePresetButton("all");
        } else {
          const numDays = parseInt(days, 10);
          if (latestDatasetEnd && !isNaN(numDays)) {
            const startD = new Date(latestDatasetEnd.getTime() - numDays * 24 * 60 * 60 * 1000);
            if (inputStartDate) inputStartDate.value = formatDateForInput(startD);
            if (inputEndDate) inputEndDate.value = formatDateForInput(latestDatasetEnd);
            setActivePresetButton(days);
          }
        }
        await loadEvaluationData();
      });
    });

    if (btnResetDates) {
      btnResetDates.addEventListener("click", async () => {
        if (inputStartDate) inputStartDate.value = "";
        if (inputEndDate) inputEndDate.value = "";
        setActivePresetButton("all");
        await loadEvaluationData();
      });
    }

    await loadEvaluationData();
  } catch (err) {
    showError("Gagal menginisialisasi parameter evaluasi: " + err.message);
  }

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
      btnApply.innerHTML = "<span>Memproses...</span>";
    }

    const payload = {
      location: selectLoc.value,
      pollutant: selectPol.value,
      scenario: selectScen.value,
      algorithm: selectAlgo.value,
      max_chart_points: 1000,
    };

    if (inputStartDate?.value) payload.start_datetime = `${inputStartDate.value}T00:00:00`;
    if (inputEndDate?.value) payload.end_datetime = `${inputEndDate.value}T23:59:59`;

    localStorage.setItem("napasloka_selected_location", payload.location);
    localStorage.setItem("napasloka_selected_pollutant", payload.pollutant);
    localStorage.setItem("napasloka_selected_scenario", payload.scenario);
    localStorage.setItem("napasloka_selected_algorithm", payload.algorithm);

    try {
      const res = await window.NapasLokaApi.postEvaluation(payload);
      renderEvaluationDashboard(res);
    } catch (err) {
      showError(err.message || "Gagal memproses data evaluasi model.");
    } finally {
      if (btnApply) {
        btnApply.disabled = false;
        btnApply.innerHTML = "<span>Perbarui Tampilan</span>";
      }
    }
  }

  function renderEvaluationDashboard(res) {
    setElText("hero-headline-sub", `Prediksi ${res.pollutant.toUpperCase()} satu jam berikutnya`);

    if (res.chart_data?.predicted?.length > 0) {
      const lastPred = res.chart_data.predicted[res.chart_data.predicted.length - 1];
      setElText("hero-pred-val", fmt(lastPred, 1));
    }
    setElText("hero-pred-unit", res.pollutant_unit);
    setElText("hero-loc-name", res.location_name);

    const algoShortName = res.algorithm === "xgboost" ? "XGBoost" : "LightGBM";
    const scenShortName = res.scenario === "scenario_1" ? "Skenario 1" : "Skenario 2";
    setElText("hero-model-name", `${algoShortName} · ${scenShortName}`);

    try {
      const d = new Date(res.time_range.end);
      d.setHours(d.getHours() + 1);
      setElText("hero-time-stamp", `${formatDateDisplay(d.toISOString())} WIB`);
    } catch {
      setElText("hero-time-stamp", `${formatDateDisplay(res.time_range.end)} WIB`);
    }

    setElText("val-mae", fmt(res.metrics.mae, 2));
    setElText("unit-mae", res.pollutant_unit);
    setElText("val-rmse", fmt(res.metrics.rmse, 2));
    setElText("unit-rmse", res.pollutant_unit);
    setElText("val-mape", fmt(res.metrics.mape, 2));
    setElText("val-r2", fmt(res.metrics.r2, 2));

    const badgeMape = document.getElementById("badge-mape-quality");
    if (badgeMape && res.metrics.mape !== undefined) {
      const isHigh = res.metrics.mape < 10;
      const isGood = res.metrics.mape < 20;
      badgeMape.textContent = isHigh ? "Akurasi Tinggi" : isGood ? "Akurasi Baik" : "Akurasi Cukup";
      badgeMape.className = `badge ${isHigh ? "badge-emerald" : isGood ? "badge-blue" : "badge-gray"}`;
    }

    const badgeR2 = document.getElementById("badge-r2-quality");
    if (badgeR2 && res.metrics.r2 !== undefined) {
      const isStrong = res.metrics.r2 >= 0.85;
      const isGood = res.metrics.r2 >= 0.70;
      badgeR2.textContent = isStrong ? "Korelasi Sangat Kuat" : isGood ? "Korelasi Kuat" : "Korelasi Moderat";
      badgeR2.className = `badge ${isStrong ? "badge-emerald" : isGood ? "badge-blue" : "badge-gray"}`;
    }

    const humanSummary = document.getElementById("eval-human-summary");
    if (humanSummary && res.metrics) {
      const r2Pct = Math.round(res.metrics.r2 * 100);
      const mapeVal = res.metrics.mape.toFixed(1);
      const algoName = res.algorithm_label || "Model terpilih";
      let compNote = "";
      if (res.comparison?.counterpart_metrics) {
        const isBetter = res.metrics.rmse <= res.comparison.counterpart_metrics.rmse;
        const diffRmse = Math.abs(res.metrics.rmse - res.comparison.counterpart_metrics.rmse).toFixed(2);
        compNote = isBetter
          ? `Model ${algoName} lebih unggul dibanding ${res.comparison.counterpart_label} dengan margin RMSE ${diffRmse} ${res.pollutant_unit}.`
          : `Model pembanding (${res.comparison.counterpart_label}) memiliki error lebih rendah sebesar ${diffRmse} ${res.pollutant_unit}.`;
      }
      humanSummary.textContent = `${algoName} berhasil menjelaskan ${r2Pct}% variasi polutan (R² = ${res.metrics.r2.toFixed(2)}) dengan deviasi rata-rata ${mapeVal}%. ${compNote}`;
    }

    const btnGotoInterp = document.getElementById("btn-eval-goto-interp");
    if (btnGotoInterp) {
      const query = `location=${encodeURIComponent(selectLoc.value)}&pollutant=${encodeURIComponent(selectPol.value)}&scenario=${encodeURIComponent(selectScen.value)}&algorithm=${encodeURIComponent(selectAlgo.value)}`;
      btnGotoInterp.href = `/pages/interpretation.html?${query}`;
    }

    setElText("selected-algo-name", res.algorithm_label);
    setElText("selected-algo-rmse", `RMSE ${fmt(res.metrics.rmse, 2)}`);

    if (res.comparison) {
      setElText("counterpart-algo-name", res.comparison.counterpart_label);
      setElText("counterpart-algo-rmse", `RMSE ${fmt(res.comparison.counterpart_metrics.rmse, 2)}`);
    }

    const bestModelPill = document.getElementById("eval-best-model-pill");
    if (bestModelPill && res.best_model_label) {
      bestModelPill.textContent = `⭐ Model Terbaik: ${res.best_model_label}`;
    }

    const sampleBadge = document.getElementById("eval-sample-badge");
    if (sampleBadge && res.time_range) {
      const evalCount = res.time_range.evaluated_samples || res.chart_data?.actual?.length || 0;
      sampleBadge.textContent = `${evalCount.toLocaleString("id-ID")} jam (${formatDateShort(res.time_range.start)} - ${formatDateShort(res.time_range.end)})`;
    }

    renderPlotlyChart(res);
  }

  function renderPlotlyChart(res) {
    if (!chartContainer || !window.Plotly) return;
    const data = res.chart_data;

    const traces = [
      {
        x: data.timestamps,
        y: data.actual,
        name: "Aktual (Observasi)",
        type: "scatter",
        mode: "lines",
        line: { color: "#1e293b", width: 2 },
        hoverinfo: "y",
      },
      {
        x: data.timestamps,
        y: data.predicted,
        name: "Prediksi (Model)",
        type: "scatter",
        mode: "lines",
        line: { color: "#ea580c", width: 2.2, dash: "dash" },
        hoverinfo: "y",
      },
    ];

    const layout = {
      margin: { t: 25, r: 20, l: 50, b: 45 },
      hovermode: "x unified",
      showlegend: false,
      hoverlabel: {
        bgcolor: "#ffffff",
        bordercolor: "#cbd5e1",
        font: { family: "Inter, sans-serif", size: 12, color: "#0f172a" },
      },
      xaxis: {
        showgrid: true,
        gridcolor: "#f1f5f9",
        tickfont: { size: 10, color: "#64748b" },
        rangeslider: {
          visible: true,
          thickness: 0.12,
          bgcolor: "#f8fafc",
          bordercolor: "#e2e8f0",
          borderwidth: 1,
        },
      },
      yaxis: {
        showgrid: true,
        gridcolor: "#f1f5f9",
        tickfont: { size: 10, color: "#64748b" },
        title: {
          text: `${res.pollutant.toUpperCase()} (${res.pollutant_unit})`,
          font: { size: 10, color: "#64748b" },
        },
      },
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
    };

    Plotly.newPlot(chartContainer, traces, layout, { responsive: true, displayModeBar: false });
  }
});
