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
function updateNetworkStatus(isOnline) {
  document.querySelectorAll(".header-status, .status-indicator").forEach((badge) => {
    if (isOnline) {
      badge.innerHTML = '<span class="status-dot" style="background-color: var(--color-success, #10b981);"></span><span>Sistem aktif</span>';
    } else {
      badge.innerHTML = '<span class="status-dot" style="background-color: var(--color-danger, #ef4444);"></span><span>Mode Offline</span>';
    }
  });
}
window.addEventListener("offline", () => updateNetworkStatus(false));
window.addEventListener("online", () => updateNetworkStatus(true));

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

// 5. Mobile Navigation Hamburger Menu
function initMobileNav() {
  const toggleBtn = document.getElementById("btn-nav-toggle");
  const nav = document.getElementById("primary-nav") || document.querySelector(".nav");
  if (!toggleBtn || !nav) return;

  function setNavOpen(isOpen) {
    toggleBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    toggleBtn.setAttribute("aria-label", isOpen ? "Tutup menu navigasi" : "Buka menu navigasi");
    if (isOpen) {
      nav.classList.add("is-open");
    } else {
      nav.classList.remove("is-open");
    }
  }

  toggleBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const isCurrentlyOpen = toggleBtn.getAttribute("aria-expanded") === "true";
    setNavOpen(!isCurrentlyOpen);
  });

  // Close when clicking any nav link
  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      setNavOpen(false);
    });
  });

  // Close when clicking outside header / nav
  document.addEventListener("click", (e) => {
    if (!nav.contains(e.target) && !toggleBtn.contains(e.target)) {
      setNavOpen(false);
    }
  });

  // Close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && toggleBtn.getAttribute("aria-expanded") === "true") {
      setNavOpen(false);
      toggleBtn.focus();
    }
  });

  // Reset if resized to desktop
  window.addEventListener("resize", () => {
    if (window.innerWidth > 640 && toggleBtn.getAttribute("aria-expanded") === "true") {
      setNavOpen(false);
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initMobileNav);
} else {
  initMobileNav();
}
