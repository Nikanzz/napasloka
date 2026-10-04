"use strict";

/**
 * Controller for Interpretasi Model (Interpretation Page)
 * Implements Local TreeSHAP decomposition, visual feature contribution bars matching Mockup 5,
 * reading guide cards, additivity reconciliation, and global feature importance.
 */
document.addEventListener("DOMContentLoaded", async () => {
  // Form & filter elements
  const form = document.getElementById("interpretation-filter-form");
  const selectLoc = document.getElementById("interp-select-location");
  const selectPol = document.getElementById("interp-select-pollutant");
  const selectScen = document.getElementById("interp-select-scenario");
  const selectAlgo = document.getElementById("interp-select-algorithm");
  const selectTopK = document.getElementById("interp-select-topk");
  const inputDatetime = document.getElementById("interp-input-datetime");
  const btnSubmit = document.getElementById("btn-submit-interp");
  const btnSpinner = document.getElementById("btn-interp-spinner");
  const btnText = document.getElementById("btn-interp-text");
  const btnUseLatest = document.getElementById("btn-use-latest");
  const btnToggleFilters = document.getElementById("btn-toggle-filters");
  const filterInputsGrid = document.getElementById("filter-inputs-grid");

  // Error alert
  const errorBox = document.getElementById("interpretation-error");
  const errorMsg = document.getElementById("interpretation-error-message");

  // Reference banner elements (Mockup 5)
  const refSummaryText = document.getElementById("ref-summary-text");
  const refBaseValuePill = document.getElementById("ref-base-value-pill");
  const refPredVal = document.getElementById("ref-pred-val");
  const refPredUnit = document.getElementById("ref-pred-unit");
  const refModelBadge = document.getElementById("ref-model-badge");

  // Feature bars list & guide elements
  const shapBarsList = document.getElementById("shap-bars-list");
  const badgeTopKCount = document.getElementById("badge-topk-count");
  const highlightFindingDesc = document.getElementById("highlight-finding-desc");

  // Plotly chart accordion
  const btnTogglePlotly = document.getElementById("btn-toggle-plotly");
  const plotlyWrapper = document.getElementById("plotly-shap-wrapper");
  const plotlyContainer = document.getElementById("plotly-shap-chart");
  let lastChartSeries = null;
  let lastPollutantUnit = "µg/m³";

  // Mathematical additivity elements
  const mathBaseVal = document.getElementById("math-base-val");
  const mathPosSum = document.getElementById("math-pos-sum");
  const mathNegSum = document.getElementById("math-neg-sum");
  const mathPredVal = document.getElementById("math-pred-val");
  const additivityStatus = document.getElementById("additivity-status-text") || document.getElementById("additivity-status");

  // Global feature importance elements
  const globalImportanceTbody = document.getElementById("global-importance-tbody");

  // Quick navigation buttons
  const btnGotoPrediction = document.getElementById("btn-goto-prediction") || document.getElementById("btn-interp-goto-prediction");
  const btnGotoEvaluation = document.getElementById("btn-goto-evaluation") || document.getElementById("btn-interp-goto-evaluation");

  let appOptions = null;

  // Helper formatting numbers with Indonesian locale
  function formatNumber(num, fractionDigits = 1) {
    if (num === null || num === undefined || isNaN(num)) return "-";
    return Number(num).toLocaleString("id-ID", {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    });
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
    if (loading && shapBarsList) {
      shapBarsList.innerHTML = `
        <div style="text-align: center; padding: 2.5rem 1rem; color: var(--color-text-muted);">
          <div class="spinner" style="border: 2px solid #cbd5e1; border-top-color: var(--color-primary); width: 1.75rem; height: 1.75rem; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 0.75rem auto;"></div>
          <div>Menghitung dekomposisi TreeSHAP untuk observasi terpilih...</div>
        </div>
      `;
    }
  }

  // 1. Initialize Options and Read URL Search Parameters
  try {
    appOptions = await window.NapasLokaApi.getOptions();

    // Populate Location selector
    if (selectLoc && appOptions.locations) {
      selectLoc.innerHTML = "";
      appOptions.locations.forEach((loc) => {
        const opt = document.createElement("option");
        opt.value = loc.id;
        opt.textContent = `${loc.name} (${loc.region || "Jabodetabek"})`;
        selectLoc.appendChild(opt);
      });
    }

    // Check URL search parameters
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("location") && selectLoc) {
      const loc = urlParams.get("location");
      if (selectLoc.querySelector(`option[value="${loc}"]`)) {
        selectLoc.value = loc;
      }
    }
    if (urlParams.has("pollutant") && selectPol) {
      const p = urlParams.get("pollutant").toLowerCase();
      if (selectPol.querySelector(`option[value="${p}"]`)) selectPol.value = p;
    }
    if (urlParams.has("scenario") && selectScen) {
      const s = urlParams.get("scenario").toLowerCase();
      if (selectScen.querySelector(`option[value="${s}"]`)) selectScen.value = s;
    }
    if (selectAlgo) {
      selectAlgo.value = "auto";
    }
    if (urlParams.has("top_k") && selectTopK) {
      const k = urlParams.get("top_k");
      if (["5", "10", "15"].includes(k)) selectTopK.value = k;
    }
    if (urlParams.has("reference_datetime") && inputDatetime) {
      const rdt = urlParams.get("reference_datetime");
      inputDatetime.value = rdt.includes("T") ? rdt.substring(0, 16) : `${rdt}T23:00`;
    } else if (urlParams.has("datetime") && inputDatetime) {
      const dt = urlParams.get("datetime");
      inputDatetime.value = dt.includes("T") ? dt.substring(0, 16) : `${dt}T23:00`;
    } else if (urlParams.has("end_date") && inputDatetime) {
      const ed = urlParams.get("end_date");
      inputDatetime.value = `${ed}T23:00`;
    }
  } catch (err) {
    showError(err.message || "Gagal menginisialisasi opsi lokasi dari backend.");
    return;
  }

  // 2. Filter toggle accordion
  if (btnToggleFilters && filterInputsGrid) {
    let filtersVisible = true;
    btnToggleFilters.addEventListener("click", () => {
      filtersVisible = !filtersVisible;
      filterInputsGrid.style.display = filtersVisible ? "grid" : "none";
      btnToggleFilters.textContent = filtersVisible ? "Sembunyikan Filter" : "Ubah Parameter";
      btnToggleFilters.setAttribute("aria-expanded", String(filtersVisible));
    });
  }

  // 3. Clear datetime to use latest observation
  if (btnUseLatest) {
    btnUseLatest.addEventListener("click", () => {
      if (inputDatetime) inputDatetime.value = "";
      loadInterpretation();
    });
  }

  // 4. Toggle Plotly interactive chart
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

  // 5. Render Plotly Horizontal Bar Chart
  function renderPlotlyChart(series, unit) {
    if (!window.Plotly || !plotlyContainer || !series || !series.features || series.features.length === 0) return;

    const trace = {
      type: "bar",
      orientation: "h",
      x: series.values,
      y: series.features,
      text: series.values.map((v) => `${v > 0 ? "+" : ""}${formatNumber(v, 2)} ${unit}`),
      textposition: "auto",
      hovertext: series.text,
      hoverinfo: "text",
      marker: {
        color: series.colors,
        line: { width: 0.5, color: "#ffffff" },
      },
    };

    const layout = {
      margin: { l: 150, r: 40, t: 20, b: 50 },
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      xaxis: {
        title: { text: `Kontribusi Marginal SHAP (${unit})`, font: { size: 12, color: "#475569" } },
        zeroline: true,
        zerolinecolor: "#94a3b8",
        zerolinewidth: 2,
        gridcolor: "#e2e8f0",
        tickfont: { size: 11, color: "#64748b" },
      },
      yaxis: {
        automargin: true,
        tickfont: { size: 11, color: "#1e293b", bold: true },
      },
      showlegend: false,
    };

    const config = {
      responsive: true,
      displayModeBar: false,
    };

    Plotly.newPlot(plotlyContainer, [trace], layout, config);
  }

  // 6. Main Data Loading and UI Rendering Function
  async function loadInterpretation() {
    hideError();
    setLoading(true);

    const location = selectLoc ? selectLoc.value : "mustikasari";
    const pollutant = selectPol ? selectPol.value : "co";
    const scenario = selectScen ? selectScen.value : "scenario_2";
    const algorithm = "auto";
    const topK = selectTopK ? (parseInt(selectTopK.value, 10) || 5) : 5;

    let refDatetime = null;
    if (inputDatetime && inputDatetime.value) {
      refDatetime = inputDatetime.value.includes("T") ? inputDatetime.value : `${inputDatetime.value}T23:00`;
    }

    // Update Quick Links query parameters
    const queryParams = `?location=${encodeURIComponent(location)}&pollutant=${encodeURIComponent(pollutant)}&scenario=${encodeURIComponent(scenario)}&algorithm=${encodeURIComponent(algorithm)}`;
    if (btnGotoPrediction) btnGotoPrediction.href = `/pages/prediction.html${queryParams}`;
    if (btnGotoEvaluation) btnGotoEvaluation.href = `/pages/evaluation.html${queryParams}`;

    try {
      const payload = {
        location,
        pollutant,
        scenario,
        algorithm,
        reference_datetime: refDatetime,
        top_k: topK,
      };

      const data = await window.NapasLokaApi.postInterpretation(payload);

      // A. Update Active Prediction Reference Banner (Mockup 4)
      if (refSummaryText) {
        refSummaryText.textContent = `${data.pollutant.toUpperCase()} · ${data.location_name} · ${data.target_time_display}`;
      }
      if (refPredVal) refPredVal.textContent = formatNumber(data.predicted_value, 1);
      if (refPredUnit) refPredUnit.textContent = data.pollutant_unit;
      if (refModelBadge) {
        refModelBadge.textContent = `${data.algorithm_label} · ${data.scenario_label} (${data.model_status})`;
      }
      if (refBaseValuePill) {
        refBaseValuePill.innerHTML = `Base E[f(X)]: <strong>${formatNumber(data.base_value, 1)} ${data.pollutant_unit}</strong>`;
      }

      // B. Update Cara Membaca & Reading Guide
      if (highlightFindingDesc && data.top_contributor) {
        highlightFindingDesc.textContent = `${data.top_contributor.label} menjadi fitur dengan kontribusi terbesar terhadap prediksi yang dipilih.`;
      }
      if (badgeTopKCount && data.local_contributions) {
        badgeTopKCount.textContent = `${data.local_contributions.length} fitur utama`;
      }

      // C. Render Custom Visual Bars (Matching Mockup 4)
      if (shapBarsList) {
        shapBarsList.innerHTML = "";
        const maxMagnitude = Math.max(...data.local_contributions.map((c) => c.impact_magnitude), 0.01);

        data.local_contributions.forEach((item) => {
          const row = document.createElement("div");
          row.className = "shap-item-row";

          const widthPct = Math.min(100, Math.max(6, (item.impact_magnitude / maxMagnitude) * 100));
          const sign = item.shap_value > 0 ? "+" : "";
          const formattedVal = `${sign}${formatNumber(item.shap_value, 1)}`;
          const directionClass = item.direction === "positive" ? "positive" : "negative";

          row.innerHTML = `
            <span class="shap-feature-name">${item.label}</span>
            <div class="shap-bar-track" title="${item.label}: ${item.direction_label} (${formatNumber(item.percentage_impact, 1)}%)">
              <div class="shap-bar-fill ${directionClass}" style="width: ${widthPct.toFixed(1)}%;"></div>
            </div>
            <span class="shap-val ${directionClass}">${formattedVal}</span>
          `;
          shapBarsList.appendChild(row);
        });
      }

      // D. Store Plotly Chart Data & Render if open
      lastChartSeries = data.chart_series;
      lastPollutantUnit = data.pollutant_unit;
      if (plotlyWrapper && plotlyWrapper.style.display !== "none") {
        renderPlotlyChart(lastChartSeries, lastPollutantUnit);
      }

      // E. Update Mathematical Additivity Card (E[f(X)] + sum(phi) = f(x))
      if (data.local_contributions) {
        const posSum = data.local_contributions
          .filter((c) => c.direction === "positive")
          .reduce((sum, c) => sum + c.shap_value, 0);

        const negSum = data.local_contributions
          .filter((c) => c.direction === "negative")
          .reduce((sum, c) => sum + c.shap_value, 0);

        if (mathBaseVal) mathBaseVal.textContent = `${formatNumber(data.base_value, 1)} ${data.pollutant_unit}`;
        if (mathPosSum) mathPosSum.textContent = `+${formatNumber(posSum, 1)} ${data.pollutant_unit}`;
        if (mathNegSum) mathNegSum.textContent = `${formatNumber(negSum, 1)} ${data.pollutant_unit}`;
        if (mathPredVal) mathPredVal.textContent = `${formatNumber(data.predicted_value, 1)} ${data.pollutant_unit}`;

        if (additivityStatus) {
          const reconstructed = data.base_value + posSum + negSum;
          const diff = Math.abs(reconstructed - data.predicted_value);
          if (diff < 1.0) {
            additivityStatus.innerHTML = `
              <strong style="color: #047857;">✓ Konsistensi Aditivitas Terverifikasi:</strong>
              Rekonstruksi matematis (${formatNumber(data.base_value, 1)} + ${formatNumber(posSum, 1)} ${formatNumber(negSum, 1)} = <strong>${formatNumber(reconstructed, 1)} ${data.pollutant_unit}</strong>)
              secara eksak mereproduksi nilai keluaran model f(x) (selisih marjinal: ${diff.toFixed(2)} ${data.pollutant_unit}).
            `;
          } else {
            additivityStatus.innerHTML = `
              <span style="color: #475569;">ℹ️ Ditampilkan untuk ${data.local_contributions.length} fitur teratas dari total fitur skenario.</span>
            `;
          }
        }
      }

      // F. Render Global Feature Importance Table
      if (globalImportanceTbody) {
        globalImportanceTbody.innerHTML = "";
        if (data.global_importance && data.global_importance.length > 0) {
          const maxGain = Math.max(...data.global_importance.map((g) => g.gain_importance), 0.001);

          data.global_importance.forEach((g, idx) => {
            const tr = document.createElement("tr");
            const widthGain = Math.min(100, Math.max(3, (g.gain_importance / maxGain) * 100));
            const meanShapText = g.mean_abs_shap !== null ? formatNumber(g.mean_abs_shap, 3) : "-";

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
        } else {
          globalImportanceTbody.innerHTML = `
            <tr>
              <td colspan="5" style="text-align: center; padding: 1.5rem; color: var(--color-text-muted);">
                Data feature importance global tidak tersedia untuk model ini.
              </td>
            </tr>
          `;
        }
      }
    } catch (err) {
      showError(err.message || "Gagal memproses interpretasi SHAP.");
      if (shapBarsList) {
        shapBarsList.innerHTML = `
          <div style="text-align: center; padding: 2rem; color: #ef4444;">
            Gagal memuat kontribusi fitur. Silakan periksa koneksi backend atau ganti parameter.
          </div>
        `;
      }
    } finally {
      setLoading(false);
    }
  }

  // Form submit handler
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      loadInterpretation();
    });
  }

  // Automatically execute first load on initialization
  loadInterpretation();
});
