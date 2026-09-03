"use strict";

window.NapasLokaApi = {
  baseUrl: "http://127.0.0.1:8000/api/v1",

  async request(path, options = {}) {
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
    const payload = await response.json();
    if (!response.ok) {
      const error = new Error(payload.detail?.message || "Permintaan API gagal.");
      error.code = payload.detail?.code || "API_ERROR";
      throw error;
    }
    return payload;
  }
};
