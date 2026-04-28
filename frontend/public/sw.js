// ReZeb PWA Service Worker
const CACHE = "rezeb-v1";
const PRECACHE = ["/", "/login", "/manifest.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  // API calls — network only, no caching
  if (e.request.url.includes("/api/")) {
    return;
  }
  // Navigation — network first, cache fallback
  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request).catch(() => caches.match("/"))
    );
    return;
  }
  // Static assets — cache first
  e.respondWith(
    caches.match(e.request).then((cached) => cached ?? fetch(e.request))
  );
});
