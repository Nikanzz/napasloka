"use strict";

/**
 * Controller for Beranda (Home Page) quick configuration matching Chapter 3 Picture 6 Mockup.
 */
document.addEventListener("DOMContentLoaded", async () => {
  const locationSelect = document.getElementById("home-location-select");
  const pollutantSelect = document.getElementById("home-pollutant-select");
  const scenarioSelect = document.getElementById("home-scenario-select");
  const quickConfigBtn = document.getElementById("btn-quick-config");
  const heroStartBtn = document.getElementById("btn-hero-start");
  const pollutantBtns = document.querySelectorAll(".home-pollutant-btn");

  // Segmented control click handlers for CO / CO2
  pollutantBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      pollutantBtns.forEach((b) => {
        b.classList.remove("active");
        b.setAttribute("aria-pressed", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-pressed", "true");

      const val = btn.getAttribute("data-pollutant");
      if (pollutantSelect) {
        pollutantSelect.value = val;
      }
    });
  });

  // Smooth scroll / focus for hero "Mulai prediksi →" button
  if (heroStartBtn) {
    heroStartBtn.addEventListener("click", () => {
      const card = document.getElementById("quick-config-card");
      if (card) {
        card.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      if (locationSelect) {
        setTimeout(() => locationSelect.focus(), 300);
      }
    });
  }

  // Populate dynamic options from API
  try {
    const options = await window.NapasLokaApi.getOptions();

    // Populate Locations
    if (locationSelect && options.locations && options.locations.length > 0) {
      locationSelect.innerHTML = "";
      options.locations.forEach((loc) => {
        const opt = document.createElement("option");
        opt.value = loc.id;
        opt.textContent = `${loc.name} (${loc.region || "Jabodetabek"})`;
        locationSelect.appendChild(opt);
      });

      // Default to Jakarta Pusat (Petamburan) to match mockup if no prior selection
      const savedLoc = localStorage.getItem("napasloka_selected_location");
      if (savedLoc && locationSelect.querySelector(`option[value="${savedLoc}"]`)) {
        locationSelect.value = savedLoc;
      } else {
        const jakartaPusat = options.locations.find((l) =>
          l.id === "petamburan-perkantoran-transjakarta" ||
          (l.region && l.region.toLowerCase().includes("pusat")) ||
          l.name.toLowerCase().includes("pusat")
        );
        if (jakartaPusat) {
          locationSelect.value = jakartaPusat.id;
        }
      }
    }

    // Populate Scenarios
    if (scenarioSelect && options.scenarios && options.scenarios.length > 0) {
      scenarioSelect.innerHTML = "";
      options.scenarios.forEach((sc) => {
        const opt = document.createElement("option");
        opt.value = sc.id;
        opt.textContent = sc.id === "scenario_2"
          ? "S2 · Polutan + meteorol..."
          : "S1 · Historis polutan saja";
        scenarioSelect.appendChild(opt);
      });

      const savedScen = localStorage.getItem("napasloka_selected_scenario");
      if (savedScen && scenarioSelect.querySelector(`option[value="${savedScen}"]`)) {
        scenarioSelect.value = savedScen;
      } else {
        // Default to S2 matching picture 6 mockup
        scenarioSelect.value = "scenario_2";
      }
    }

    // Sync saved pollutant selection from localStorage if previously set
    const savedPol = localStorage.getItem("napasloka_selected_pollutant");
    if (savedPol) {
      if (pollutantSelect) pollutantSelect.value = savedPol;
      pollutantBtns.forEach((b) => {
        const isMatch = b.getAttribute("data-pollutant") === savedPol;
        b.classList.toggle("active", isMatch);
        b.setAttribute("aria-pressed", isMatch ? "true" : "false");
      });
    }
  } catch (err) {
    console.warn("Could not load dynamic options for home page:", err);
  }

  // Handle "Lanjutkan Konfigurasi" button click
  if (quickConfigBtn) {
    quickConfigBtn.addEventListener("click", () => {
      const loc = locationSelect ? locationSelect.value : "petamburan-perkantoran-transjakarta";
      const pol = pollutantSelect ? pollutantSelect.value : "co";
      const sc = scenarioSelect ? scenarioSelect.value : "scenario_2";

      // Store in localStorage for persistence across pages
      localStorage.setItem("napasloka_selected_location", loc);
      localStorage.setItem("napasloka_selected_pollutant", pol);
      localStorage.setItem("napasloka_selected_scenario", sc);

      // Redirect to prediction configuration page
      window.location.href = `/pages/prediction.html?location=${encodeURIComponent(loc)}&pollutant=${encodeURIComponent(pol)}&scenario=${encodeURIComponent(sc)}`;
    });
  }
});
