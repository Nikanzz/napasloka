"use strict";

document.addEventListener("DOMContentLoaded", async () => {
  const locationSelect = document.getElementById("home-location-select");
  const pollutantSelect = document.getElementById("home-pollutant-select");
  const scenarioSelect = document.getElementById("home-scenario-select");
  const quickConfigBtn = document.getElementById("btn-quick-config");
  const heroStartBtn = document.getElementById("btn-hero-start");
  const pollutantBtns = document.querySelectorAll(".home-pollutant-btn");

  pollutantBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      pollutantBtns.forEach((b) => {
        b.classList.remove("active");
        b.setAttribute("aria-pressed", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-pressed", "true");
      if (pollutantSelect) {
        pollutantSelect.value = btn.getAttribute("data-pollutant");
      }
    });
  });

  if (heroStartBtn) {
    heroStartBtn.addEventListener("click", () => {
      const card = document.getElementById("quick-config-card");
      if (card) card.scrollIntoView({ behavior: "smooth", block: "center" });
      if (locationSelect) setTimeout(() => locationSelect.focus(), 300);
    });
  }

  try {
    const options = await window.NapasLokaApi.getOptions();

    if (locationSelect && options.locations) {
      locationSelect.innerHTML = "";
      options.locations.forEach((loc) => {
        const opt = document.createElement("option");
        opt.value = loc.id;
        opt.textContent = `${loc.name} (${loc.region || "Jabodetabek"})`;
        locationSelect.appendChild(opt);
      });

      const savedLoc = localStorage.getItem("napasloka_selected_location");
      if (savedLoc && locationSelect.querySelector(`option[value="${savedLoc}"]`)) {
        locationSelect.value = savedLoc;
      }
    }

    if (scenarioSelect && options.scenarios) {
      scenarioSelect.innerHTML = "";
      options.scenarios.forEach((sc) => {
        const opt = document.createElement("option");
        opt.value = sc.id;
        opt.textContent = sc.id === "scenario_2"
          ? "S2 · Polutan + meteorologi"
          : "S1 · Historis polutan saja";
        scenarioSelect.appendChild(opt);
      });

      const savedScen = localStorage.getItem("napasloka_selected_scenario");
      if (savedScen && scenarioSelect.querySelector(`option[value="${savedScen}"]`)) {
        scenarioSelect.value = savedScen;
      } else {
        scenarioSelect.value = "scenario_2";
      }
    }

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
    console.warn("Gagal memuat opsi beranda:", err);
  }

  if (quickConfigBtn) {
    quickConfigBtn.addEventListener("click", () => {
      const loc = locationSelect ? locationSelect.value : "petamburan-perkantoran-transjakarta";
      const pol = pollutantSelect ? pollutantSelect.value : "co";
      const sc = scenarioSelect ? scenarioSelect.value : "scenario_2";

      localStorage.setItem("napasloka_selected_location", loc);
      localStorage.setItem("napasloka_selected_pollutant", pol);
      localStorage.setItem("napasloka_selected_scenario", sc);

      window.location.href = `/pages/prediction.html?location=${encodeURIComponent(loc)}&pollutant=${encodeURIComponent(pol)}&scenario=${encodeURIComponent(sc)}`;
    });
  }
});
