"use strict";

document.addEventListener("DOMContentLoaded", async () => {
  const form = document.querySelector("#prediction-form");
  const status = document.querySelector("#prediction-status");
  const submit = form.querySelector("button[type='submit']");
  try {
    const options = await window.loadNapasLokaOptions();
    if (!options.locations.length) {
      submit.disabled = true;
      status.textContent = "Lokasi belum dikonfigurasi. Tidak ada prediksi yang dibuat.";
    }
  } catch (error) {
    submit.disabled = true;
    status.textContent = `API belum dapat dimuat: ${error.message}`;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(
      [...new FormData(form).entries()].filter(([, value]) => value !== "")
    );
    try {
      await window.NapasLokaApi.request("/predict", {
        method: "POST",
        body: JSON.stringify(values)
      });
    } catch (error) {
      status.textContent = `${error.code}: ${error.message}`;
    }
  });
});
