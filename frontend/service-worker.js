"use strict";

// Cache version identifier
const CACHE_NAME = "napasloka-v1.0.1";

const APP_SHELL = [
  "/",
  "/app",
  "/index.html",
  "/pages/prediction.html",
  "/pages/evaluation.html",
  "/pages/interpretation.html",
  "/pages/information.html",
  "/css/main.css",
  "/css/components.css",
  "/js/app.js",
  "/js/api.js",
  "/js/home.js",
  "/js/prediction.js",
  "/js/evaluation.js",
  "/js/interpretation.js",
  "/manifest.json",
  "/assets/icons/icon.svg",
  "/assets/icons/icon-192.png",
  "/assets/icons/icon-512.png",
];

// Install Event: Precaching App Shell
self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(APP_SHELL);
    })
  );
});

// Activate Event: Purge old cache versions and claim immediate control
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("[ServiceWorker] Purging outdated cache version:", key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Smart Routing
self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // 1. Never cache non-GET requests or backend API requests
  if (request.method !== "GET" || url.pathname.startsWith("/api/")) {
    return;
  }

  // 2. Network-First Strategy for HTML Navigation Requests (Latest UI and fallback to a cached version if offline)                                        
  if (request.mode === "navigate" || request.headers.get("accept")?.includes("text/html")) {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseToCache));
          }
          return networkResponse;
        })
        .catch(() => {
          // Offline fallback
          return caches.match(request).then((cachedResponse) => {
            return cachedResponse || caches.match("/index.html");
          });
        })
    );
    return;
  }

  // 3. Stale-While-Revalidate / Cache-First for static assets (CSS, JS, Icons)
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      const fetchPromise = fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && networkResponse.type === "basic") {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseToCache));
          }
          return networkResponse;
        })
        .catch(() => {
          // If network fails, return cached response if available
        });

      return cachedResponse || fetchPromise;
    })
  );
});
