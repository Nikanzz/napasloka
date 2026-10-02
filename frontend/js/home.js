"use strict";

/**
 * Controller for Beranda (Home Page) quick configuration.
 */
document.addEventListener("DOMContentLoaded", async () => {
  const locationSelect = document.getElementById("home-location-select");
  const pollutantSelect = document.getElementById("home-pollutant-select");
  const scenarioSelect = document.getElementById("home-scenario-select");
  const quickConfigBtn = document.getElementById("btn-quick-config");

  try {
    const options = await window.NapasLokaApi.getOptions();

    // Populate Locations
    if (locationSelect && options.locations) {
      locationSelect.innerHTML = "";
      options.locations.forEach((loc) => {
        const opt = document.createElement("option");
        opt.value = loc.id;
        opt.textContent = `${loc.name} (${loc.region || "Jabodetabek"})`;
        locationSelect.appendChild(opt);
      });
    }

    // Populate Pollutants
    if (pollutantSelect && options.pollutants) {
      pollutantSelect.innerHTML = "";
      options.pollutants.forEach((pol) => {
        const opt = document.createElement("option");
        opt.value = pol.id;
        opt.textContent = `${pol.label} [${pol.unit}]`;
        pollutantSelect.appendChild(opt);
      });
    }

    // Populate Scenarios
    if (scenarioSelect && options.scenarios) {
      scenarioSelect.innerHTML = "";
      options.scenarios.forEach((sc) => {
        const opt = document.createElement("option");
        opt.value = sc.id;
        opt.textContent = `${sc.label} (${sc.feature_count || (sc.id === "scenario_1" ? 3 : 15)} Fitur)`;
        scenarioSelect.appendChild(opt);
      });
    }
  } catch (err) {
    console.warn("Could not load dynamic options for home page:", err);
  }

  // Handle "Lanjutkan Konfigurasi" button click
  if (quickConfigBtn) {
    quickConfigBtn.addEventListener("click", () => {
      const loc = locationSelect ? locationSelect.value : "taman-kamal";
      const pol = pollutantSelect ? pollutantSelect.value : "co";
      const sc = scenarioSelect ? scenarioSelect.value : "scenario_1";

      // Store in localStorage for persistence across pages
      localStorage.setItem("napasloka_selected_location", loc);
      localStorage.setItem("napasloka_selected_pollutant", pol);
      localStorage.setItem("napasloka_selected_scenario", sc);

      // Redirect to prediction configuration page
      window.location.href = `/pages/prediction.html?location=${encodeURIComponent(loc)}&pollutant=${encodeURIComponent(pol)}&scenario=${encodeURIComponent(sc)}`;
    });
  }
});
