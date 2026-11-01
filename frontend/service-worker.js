"use strict";

const CACHE_NAME = "napasloka-v1.0.8";

const APP_SHELL = [
  "/",
  "/app",
  "/index.html",
  "/pages/prediction.html",
  "/pages/evaluation.html",
  "/pages/interpretation.html",
  "/pages/information.html",
  "/pages/about.html",
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

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.pathname.startsWith("/api/") || url.hostname === "localhost" || url.hostname === "127.0.0.1") {
    return;
  }

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
          return caches.match(request).then((cachedResponse) => {
            return cachedResponse || caches.match("/index.html");
          });
        })
    );
    return;
  }

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
        .catch(() => {});

      return cachedResponse || fetchPromise;
    })
  );
});
