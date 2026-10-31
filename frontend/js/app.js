"use strict";

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch((err) => {
      console.warn("Service Worker registration failed:", err);
    });
  });
}

document.querySelectorAll("[data-current-year]").forEach((el) => {
  el.textContent = new Date().getFullYear();
});

function updateNetworkStatus(isOnline) {
  document.querySelectorAll(".header-status, .status-indicator").forEach((badge) => {
    badge.innerHTML = isOnline
      ? '<span class="status-dot" style="background-color: var(--color-success, #10b981);"></span><span>Sistem aktif</span>'
      : '<span class="status-dot" style="background-color: var(--color-danger, #ef4444);"></span><span>Mode Offline</span>';
  });
}
window.addEventListener("offline", () => updateNetworkStatus(false));
window.addEventListener("online", () => updateNetworkStatus(true));

let deferredPrompt = null;
const installButtons = () => document.querySelectorAll(".btn-install-pwa, #btn-install-pwa");

function initPwaInstall() {
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone;
  if (isStandalone) {
    installButtons().forEach((btn) => (btn.style.display = "none"));
    return;
  }

  installButtons().forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === "accepted") {
          installButtons().forEach((b) => (b.style.display = "none"));
        }
        deferredPrompt = null;
      } else {
        alert("Gunakan menu browser untuk memasang aplikasi NapasLoka ke layar utama.");
      }
    });
  });
}

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  installButtons().forEach((btn) => (btn.style.display = "inline-flex"));
});

window.addEventListener("appinstalled", () => {
  deferredPrompt = null;
  installButtons().forEach((btn) => (btn.style.display = "none"));
});

function initMobileNav() {
  const toggleBtn = document.getElementById("btn-nav-toggle");
  const nav = document.getElementById("primary-nav") || document.querySelector(".nav");
  if (!toggleBtn || !nav) return;

  function setNavOpen(isOpen) {
    toggleBtn.setAttribute("aria-expanded", String(isOpen));
    nav.classList.toggle("is-open", isOpen);
  }

  toggleBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const isOpen = toggleBtn.getAttribute("aria-expanded") === "true";
    setNavOpen(!isOpen);
  });

  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => setNavOpen(false));
  });

  document.addEventListener("click", (e) => {
    if (!nav.contains(e.target) && !toggleBtn.contains(e.target)) {
      setNavOpen(false);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setNavOpen(false);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initPwaInstall();
    initMobileNav();
  });
} else {
  initPwaInstall();
  initMobileNav();
}
