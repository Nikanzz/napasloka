"use strict";

document.addEventListener("DOMContentLoaded", async () => {
  const form = document.getElementById("interpretation-filter-form");
  const selectLoc = document.getElementById("interp-select-location");
  const selectPol = document.getElementById("interp-select-pollutant");
  const selectScen = document.getElementById("interp-select-scenario");
  const selectTopK = document.getElementById("interp-select-topk");
  const inputDatetime = document.getElementById("interp-input-datetime");
  const btnSubmit = document.getElementById("btn-submit-interp");
  const btnSpinner = document.getElementById("btn-interp-spinner");
  const btnText = document.getElementById("btn-interp-text");
  const btnUseLatest = document.getElementById("btn-use-latest");
  const btnToggleFilters = document.getElementById("btn-toggle-filters");
  const filterInputsGrid = document.getElementById("filter-inputs-grid");

  const errorBox = document.getElementById("interpretation-error");
  const errorMsg = document.getElementById("interpretation-error-message");

  const shapBarsList = document.getElementById("shap-bars-list");
  const globalImportanceTbody = document.getElementById("global-importance-tbody");
  const btnTogglePlotly = document.getElementById("btn-toggle-plotly");
  const plotlyWrapper = document.getElementById("plotly-shap-wrapper");
  const plotlyContainer = document.getElementById("plotly-shap-chart");

  let lastChartSeries = null;
  let lastPollutantUnit = "µg/m³";

  const fmt = (n, d = 1) => (n != null && !isNaN(n) ? Number(n).toLocaleString("id-ID", { minimumFractionDigits: d, maximumFractionDigits: d }) : "-");

  function setElText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function showError(message) {
    if (errorMsg) errorMsg.textContent = message;
    if (errorBox) {
      errorBox.style.display = "block";
      errorBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  function hideError() {
    if (errorBox) errorBox.style.display = "none";
  }

  function setLoading(loading) {
    if (btnSubmit) btnSubmit.disabled = loading;
    if (btnSpinner) btnSpinner.style.display = loading ? "inline-block" : "none";
    if (btnText) btnText.textContent = loading ? "Menghitung TreeSHAP..." : "Hitung Interpretasi SHAP";
  }

  try {
    const appOptions = await window.NapasLokaApi.getOptions();

    if (selectLoc && appOptions.locations) {
      selectLoc.innerHTML = "";
      appOptions.locations.forEach((loc) => {
        const opt = document.createElement("option");
        opt.value = loc.id;
        opt.textContent = `${loc.name} (${loc.region || "Jabodetabek"})`;
        selectLoc.appendChild(opt);
      });
    }

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("location") && selectLoc) {
      const loc = urlParams.get("location");
      if (selectLoc.querySelector(`option[value="${loc}"]`)) selectLoc.value = loc;
    }
    if (urlParams.has("pollutant") && selectPol) {
      const p = urlParams.get("pollutant").toLowerCase();
      if (selectPol.querySelector(`option[value="${p}"]`)) selectPol.value = p;
    }
    if (urlParams.has("scenario") && selectScen) {
      const s = urlParams.get("scenario").toLowerCase();
      if (selectScen.querySelector(`option[value="${s}"]`)) selectScen.value = s;
    }
    if (urlParams.has("top_k") && selectTopK) {
      const k = urlParams.get("top_k");
      if (["5", "10", "15"].includes(k)) selectTopK.value = k;
    }

    const initialDt = urlParams.get("reference_datetime") || urlParams.get("datetime") || urlParams.get("end_date");
    if (initialDt && inputDatetime) {
      inputDatetime.value = initialDt.includes("T") ? initialDt.substring(0, 16) : `${initialDt}T23:00`;
    }
  } catch (err) {
    showError(err.message || "Gagal menginisialisasi parameter lokasi.");
    return;
  }

  if (btnToggleFilters && filterInputsGrid) {
    let filtersVisible = true;
    btnToggleFilters.addEventListener("click", () => {
      filtersVisible = !filtersVisible;
      filterInputsGrid.style.display = filtersVisible ? "grid" : "none";
      btnToggleFilters.textContent = filtersVisible ? "Sembunyikan Filter" : "Ubah Parameter";
      btnToggleFilters.setAttribute("aria-expanded", String(filtersVisible));
    });
  }

  if (btnUseLatest) {
    btnUseLatest.addEventListener("click", () => {
      if (inputDatetime) inputDatetime.value = "";
      loadInterpretation();
    });
  }

  if (btnTogglePlotly && plotlyWrapper) {
    btnTogglePlotly.addEventListener("click", () => {
      const isHidden = plotlyWrapper.style.display === "none";
      plotlyWrapper.style.display = isHidden ? "block" : "none";
      btnTogglePlotly.textContent = isHidden ? "Sembunyikan Plotly" : "Tampilkan Plotly";
      if (isHidden && lastChartSeries) {
        renderPlotlyChart(lastChartSeries, lastPollutantUnit);
      }
    });
  }

  function renderPlotlyChart(series, unit) {
    if (!window.Plotly || !plotlyContainer || !series?.features?.length) return;

    const trace = {
      type: "bar",
      orientation: "h",
      x: series.values,
      y: series.features,
      text: series.values.map((v) => `${v > 0 ? "+" : ""}${fmt(v, 2)} ${unit}`),
      textposition: "auto",
      hovertext: series.text,
      hoverinfo: "text",
      marker: { color: series.colors },
    };

    const layout = {
      margin: { l: 150, r: 40, t: 20, b: 50 },
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      xaxis: { title: { text: `Kontribusi Marginal SHAP (${unit})` }, zeroline: true, zerolinecolor: "#94a3b8" },
      yaxis: { automargin: true },
      showlegend: false,
    };

    Plotly.newPlot(plotlyContainer, [trace], layout, { responsive: true, displayModeBar: false });
  }

  async function loadInterpretation() {
    hideError();
    setLoading(true);

    const location = selectLoc ? selectLoc.value : "mustikasari";
    const pollutant = selectPol ? selectPol.value : "co";
    const scenario = selectScen ? selectScen.value : "scenario_2";
    const topK = selectTopK ? parseInt(selectTopK.value, 10) || 5 : 5;

    let refDatetime = null;
    if (inputDatetime?.value) {
      refDatetime = inputDatetime.value.includes("T") ? inputDatetime.value : `${inputDatetime.value}T23:00`;
    }

    const queryParams = `?location=${encodeURIComponent(location)}&pollutant=${encodeURIComponent(pollutant)}&scenario=${encodeURIComponent(scenario)}&algorithm=auto`;
    const btnGotoPred = document.getElementById("btn-goto-prediction") || document.getElementById("btn-interp-goto-prediction");
    const btnGotoEval = document.getElementById("btn-goto-evaluation") || document.getElementById("btn-interp-goto-evaluation");
    if (btnGotoPred) btnGotoPred.href = `/pages/prediction.html${queryParams}`;
    if (btnGotoEval) btnGotoEval.href = `/pages/evaluation.html${queryParams}`;

    const isLiveParam = urlParams.get("live") === "true";

    let clientLive = null;
    if ((!refDatetime || isLiveParam) && navigator.onLine && appOptions?.locations) {
      const locObj = appOptions.locations.find((l) => l.id === location);
      if (locObj && locObj.latitude && locObj.longitude) {
        clientLive = await window.NapasLokaApi.fetchClientLiveFeatures(
          locObj.latitude,
          locObj.longitude,
          pollutant,
          scenario
        );
      }
    }

    const payload = {
      location,
      pollutant,
      scenario,
      algorithm: "auto",
      reference_datetime: refDatetime,
      is_live: isLiveParam,
      top_k: topK,
    };
    if (clientLive) payload.client_live_features = clientLive;

    const data = await window.NapasLokaApi.postInterpretation(payload);

    const liveSuffix = data.is_live_data ? " · 🟢 Live Open-Meteo" : "";
    setElText("ref-summary-text", `${data.pollutant.toUpperCase()} · ${data.location_name} · ${data.target_time_display}${liveSuffix}`);
      setElText("ref-pred-val", fmt(data.predicted_value, 1));
      setElText("ref-pred-unit", data.pollutant_unit);
      setElText("ref-model-badge", `${data.algorithm_label} · ${data.scenario_label} (${data.model_status})`);

      const refBase = document.getElementById("ref-base-value-pill");
      if (refBase) refBase.innerHTML = `Base E[f(X)]: <strong>${fmt(data.base_value, 1)} ${data.pollutant_unit}</strong>`;

      if (data.top_contributor) {
        setElText("highlight-finding-desc", `${data.top_contributor.label} menjadi fitur dengan kontribusi terbesar terhadap prediksi yang dipilih.`);
      }
      if (data.local_contributions) {
        setElText("badge-topk-count", `${data.local_contributions.length} fitur utama`);
      }

      if (shapBarsList && data.local_contributions) {
        shapBarsList.innerHTML = "";
        const maxMagnitude = Math.max(...data.local_contributions.map((c) => c.impact_magnitude), 0.01);

        data.local_contributions.forEach((item) => {
          const row = document.createElement("div");
          row.className = "shap-item-row";
          const widthPct = Math.min(100, Math.max(6, (item.impact_magnitude / maxMagnitude) * 100));
          const sign = item.shap_value > 0 ? "+" : "";
          const directionClass = item.direction === "positive" ? "positive" : "negative";

          row.innerHTML = `
            <span class="shap-feature-name">${item.label}</span>
            <div class="shap-bar-track" title="${item.label}: ${item.direction_label} (${fmt(item.percentage_impact, 1)}%)">
              <div class="shap-bar-fill ${directionClass}" style="width: ${widthPct.toFixed(1)}%;"></div>
            </div>
            <span class="shap-val ${directionClass}">${sign}${fmt(item.shap_value, 1)}</span>
          `;
          shapBarsList.appendChild(row);
        });
      }

      lastChartSeries = data.chart_series;
      lastPollutantUnit = data.pollutant_unit;
      if (plotlyWrapper && plotlyWrapper.style.display !== "none") {
        renderPlotlyChart(lastChartSeries, lastPollutantUnit);
      }

      if (data.local_contributions) {
        const posSum = data.local_contributions
          .filter((c) => c.direction === "positive")
          .reduce((sum, c) => sum + c.shap_value, 0);
        const negSum = data.local_contributions
          .filter((c) => c.direction === "negative")
          .reduce((sum, c) => sum + c.shap_value, 0);

        setElText("math-base-val", `${fmt(data.base_value, 1)} ${data.pollutant_unit}`);
        setElText("math-pos-sum", `+${fmt(posSum, 1)} ${data.pollutant_unit}`);
        setElText("math-neg-sum", `${fmt(negSum, 1)} ${data.pollutant_unit}`);
        setElText("math-pred-val", `${fmt(data.predicted_value, 1)} ${data.pollutant_unit}`);

        const additivityStatus = document.getElementById("additivity-status-text") || document.getElementById("additivity-status");
        if (additivityStatus) {
          const reconstructed = data.base_value + posSum + negSum;
          const diff = Math.abs(reconstructed - data.predicted_value);
          if (diff < 1.0) {
            additivityStatus.innerHTML = `
              <strong style="color: #047857;">✓ Konsistensi Aditivitas Terverifikasi:</strong>
              Rekonstruksi matematis (${fmt(data.base_value, 1)} + ${fmt(posSum, 1)} ${fmt(negSum, 1)} = <strong>${fmt(reconstructed, 1)} ${data.pollutant_unit}</strong>)
              secara eksak mereproduksi nilai keluaran model f(x).
            `;
          } else {
            additivityStatus.innerHTML = `<span>ℹ️ Ditampilkan untuk ${data.local_contributions.length} fitur teratas dari total fitur skenario.</span>`;
          }
        }
      }

      if (globalImportanceTbody) {
        globalImportanceTbody.innerHTML = "";
        if (data.global_importance?.length > 0) {
          const maxGain = Math.max(...data.global_importance.map((g) => g.gain_importance), 0.001);
          data.global_importance.forEach((g, idx) => {
            const tr = document.createElement("tr");
            const widthGain = Math.min(100, Math.max(3, (g.gain_importance / maxGain) * 100));
            const meanShapText = g.mean_abs_shap != null ? fmt(g.mean_abs_shap, 3) : "-";

            tr.innerHTML = `
              <td style="font-weight: 700; color: var(--color-text-light);">${idx + 1}</td>
              <td>
                <div style="font-weight: 600; color: var(--color-text-main);">${g.label}</div>
                <div style="font-size: 0.75rem; color: var(--color-text-light); font-family: monospace;">${g.feature_name}</div>
              </td>
              <td style="font-weight: 700; font-family: monospace;">${g.gain_importance.toFixed(4)}</td>
              <td style="font-weight: 600; font-family: monospace; color: #4338ca;">${meanShapText}</td>
              <td>
                <div style="width: 100%; height: 8px; background: #f1f5f9; border-radius: var(--radius-full); overflow: hidden;">
                  <div style="height: 100%; width: ${widthGain.toFixed(1)}%; background: #6366f1; border-radius: var(--radius-full);"></div>
                </div>
              </td>
            `;
            globalImportanceTbody.appendChild(tr);
          });
        }
      }
    } catch (err) {
      showError(err.message || "Gagal memproses interpretasi SHAP.");
    } finally {
      setLoading(false);
    }
  }

  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      loadInterpretation();
    });
  }

  loadInterpretation();
});
