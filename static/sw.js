/**
 * Nova 3.0 — Service worker
 * Caches the app shell so the UI loads instantly and works offline;
 * API calls (/api/*) always go to the network since they're dynamic.
 */
const CACHE_NAME = "nova-shell-v1";
const SHELL_ASSETS = [
  "/",
  "/static/css/style.css",
  "/static/js/orb.js",
  "/static/js/voice.js",
  "/static/js/commands.js",
  "/static/js/app.js",
  "/static/icons/favicon.svg",
  "/static/icons/app-icon.svg",
  "/manifest.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/")) {
    return; // always hit the network for live data
  }
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
