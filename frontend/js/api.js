"use strict";

/**
 * NapasLoka API client with auto-detecting base URL.
 */
window.NapasLokaApi = {
  baseUrl: (() => {
    // If the browser is accessing the backend directly on port 8000
    if (window.location.port === "8000") {
      return `${window.location.origin}/api/v1`;
    }
    // Default local backend address
    return "http://127.0.0.1:8000/api/v1";
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
        error.status = response.status;
        throw error;
      }
      return payload;
    } catch (err) {
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        const netErr = new Error("Gagal terhubung ke backend FastAPI NapasLoka (http://127.0.0.1:8000). Pastikan server backend sedang berjalan.");
        netErr.code = "CONNECTION_ERROR";
        throw netErr;
      }
      throw err;
    }
  },

  async getOptions() {
    return this.request("/config/options");
  },

  async getModelsSummary() {
    return this.request("/config/models");
  },

  async getEvaluationRange(location, pollutant) {
    return this.request(`/evaluation/range?location=${encodeURIComponent(location)}&pollutant=${encodeURIComponent(pollutant)}`);
  },

  async postEvaluation(data) {
    return this.request("/evaluation", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async postPrediction(data) {
    return this.request("/predict", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async postInterpretation(data) {
    return this.request("/interpretation", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};
