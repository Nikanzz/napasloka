"use strict";

// 1. Service Worker Registration
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/service-worker.js")
      .then((reg) => {
        // Check for updates
        reg.onupdatefound = () => {
          const installingWorker = reg.installing;
          if (installingWorker) {
            installingWorker.onstatechange = () => {
              if (installingWorker.state === "installed" && navigator.serviceWorker.controller) {
                console.info("NapasLoka PWA: Versi baru telah tersedia di latar belakang.");
              }
            };
          }
        };
      })
      .catch((error) => {
        console.warn("NapasLoka Service Worker registration failed:", error);
      });
  });
}

// 2. Dynamic Year in Footer
document.querySelectorAll("[data-current-year]").forEach((element) => {
  element.textContent = new Date().getFullYear();
});

// 3. Online/Offline Network Status Indicator
window.addEventListener("offline", () => {
  const badge = document.querySelector(".status-indicator");
  if (badge) {
    badge.innerHTML = '<span style="color: #ef4444;">●</span> Mode Offline';
  }
});

window.addEventListener("online", () => {
  const badge = document.querySelector(".status-indicator");
  if (badge) {
    badge.innerHTML = '<span style="color: #10b981;">●</span> Sistem aktif';
  }
});

// 4. PWA Installation Prompt Stashing
let deferredPrompt = null;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const installBtn = document.getElementById("btn-install-pwa");
  if (installBtn) {
    installBtn.style.display = "inline-flex";
    installBtn.addEventListener("click", async () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === "accepted") {
          installBtn.style.display = "none";
        }
        deferredPrompt = null;
      }
    });
  }
});
