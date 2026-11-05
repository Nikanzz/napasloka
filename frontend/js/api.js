"use strict";

window.NapasLokaApi = {
  baseUrl: (() => {
    if ((window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") &&
      window.location.port && window.location.port !== "8000") {
      return "http://127.0.0.1:8000/api/v1";
    }
    return `${window.location.origin}/api/v1`;
  })(),

  async request(path, options = {}) {
    const url = `${this.baseUrl}${path.startsWith("/") ? "" : "/"}${path}`;
    try {
      const response = await fetch(url, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
      });
      const payload = await response.json();
      if (!response.ok) {
        const error = new Error(payload.detail?.message || "Permintaan API gagal.");
        error.code = payload.detail?.code || "API_ERROR";
        throw error;
      }
      return payload;
    } catch (err) {
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        throw new Error("Gagal terhubung ke backend FastAPI NapasLoka. Pastikan server backend sedang aktif.");
      }
      throw err;
    }
  },

  getOptions() {
    return this.request("/config/options");
  },

  getModelsSummary() {
    return this.request("/config/models");
  },

  getBestModels() {
    return this.request("/config/best-models");
  },

  getEvaluationRange(location, pollutant) {
    return this.request(`/evaluation/range?location=${encodeURIComponent(location)}&pollutant=${encodeURIComponent(pollutant)}`);
  },

  postEvaluation(data) {
    return this.request("/evaluation", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  postPrediction(data) {
    return this.request("/predict", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  postInterpretation(data) {
    return this.request("/interpretation", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async fetchClientLiveFeatures(lat, lon, pollutant, scenario) {
    try {
      const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&hourly=temperature_2m,relative_humidity_2m,rain,wind_speed_100m&past_days=2&forecast_days=1&timezone=Asia%2FBangkok`;
      const airUrl = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&hourly=carbon_monoxide,carbon_dioxide&past_days=2&forecast_days=1&domains=cams_global&timezone=Asia%2FBangkok`;

      const [wResp, aResp] = await Promise.all([
        fetch(weatherUrl),
        fetch(airUrl),
      ]);

      if (!wResp.ok || !aResp.ok) return null;

      const wJson = await wResp.json();
      const aJson = await aResp.json();

      const times = wJson.hourly?.time || [];
      const polCol = pollutant.toLowerCase() === "co" ? "carbon_monoxide" : "carbon_dioxide";
      const polVals = aJson.hourly?.[polCol] || [];

      if (!times.length || !polVals.length) return null;

      const now = new Date();
      const utcTime = now.getTime() + now.getTimezoneOffset() * 60000;
      const wibDate = new Date(utcTime + 7 * 3600000);
      const yr = wibDate.getFullYear();
      const mo = String(wibDate.getMonth() + 1).padStart(2, "0");
      const da = String(wibDate.getDate()).padStart(2, "0");
      const hr = String(wibDate.getHours()).padStart(2, "0");
      const currentWibHourStr = `${yr}-${mo}-${da}T${hr}:00`;

      let validIndices = [];
      for (let i = 0; i < times.length; i++) {
        if (times[i] <= currentWibHourStr && polVals[i] !== null && polVals[i] !== undefined) {
          validIndices.push(i);
        }
      }

      if (validIndices.length < 3) {
        validIndices = [times.length - 3, times.length - 2, times.length - 1];
      }

      const idx_t2 = validIndices[validIndices.length - 3];
      const idx_t1 = validIndices[validIndices.length - 2];
      const idx_t0 = validIndices[validIndices.length - 1];

      const t0_time = times[idx_t0];
      const t0_val = Number(polVals[idx_t0]);

      // Compute target prediction time (+1 hour) preserving Western Indonesia Time (WIB, UTC+7).
      const d0 = new Date(`${t0_time}:00+07:00`);
      const d1 = new Date(d0.getTime() + 3600000);
      const d1Wib = new Date(d1.getTime() + 7 * 3600000);
      const y1 = d1Wib.getUTCFullYear();
      const m1 = String(d1Wib.getUTCMonth() + 1).padStart(2, "0");
      const day1 = String(d1Wib.getUTCDate()).padStart(2, "0");
      const h1 = String(d1Wib.getUTCHours()).padStart(2, "0");
      const target_time = `${y1}-${m1}-${day1}T${h1}:00:00+07:00`;

      const feature_values = {
        [`${polCol}_lag_3h`]: Number(polVals[idx_t2]),
        [`${polCol}_lag_2h`]: Number(polVals[idx_t1]),
        [`${polCol}_lag_1h`]: Number(polVals[idx_t0]),
      };

      if (scenario === "scenario_2") {
        const meteoVars = ["temperature_2m", "relative_humidity_2m", "rain", "wind_speed_100m"];
        meteoVars.forEach((mv) => {
          const vals = wJson.hourly?.[mv] || [];
          feature_values[`${mv}_lag_3h`] = Number(vals[idx_t2] ?? 0);
          feature_values[`${mv}_lag_2h`] = Number(vals[idx_t1] ?? 0);
          feature_values[`${mv}_lag_1h`] = Number(vals[idx_t0] ?? 0);
        });
      }

      return {
        latest_observation_time: `${t0_time}:00+07:00`,
        latest_observation_value: t0_val,
        target_prediction_time: target_time,
        feature_values: feature_values,
      };
    } catch (err) {
      console.warn("Client live fetch error (will fallback to backend/dataset):", err);
      return null;
    }
  },
};
