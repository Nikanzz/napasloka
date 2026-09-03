const CACHE_NAME = "napasloka-phase0-v2";
const APP_SHELL = [
  "/",
  "/index.html",
  "/pages/prediction.html",
  "/pages/evaluation.html",
  "/pages/interpretation.html",
  "/pages/information.html",
  "/css/main.css",
  "/css/components.css",
  "/js/app.js",
  "/js/api.js",
  "/js/config.js",
  "/js/prediction.js",
  "/js/evaluation.js",
  "/js/interpretation.js",
  "/assets/icons/icon.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || new URL(event.request.url).origin !== self.location.origin) {
    return;
  }
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
