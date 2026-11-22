/* Service worker: оболочка приложения и пакет дня (IMP-OFF-1, IMP-OFF-2). */
const SHELL = "masya-shell-v1";
const PAGES = "masya-pages-v1";
const SHELL_URLS = [
  "/static/css/app.css",
  "/static/js/app.js",
  "/static/js/htmx.min.js",
  "/static/js/pwa.js",
  "/static/favicon.svg",
  "/manifest.webmanifest",
  "/home/",
  "/start/",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_URLS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== SHELL && k !== PAGES).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname === "/sw.js") return;
  // API пакета и синхронизации — только сеть
  if (url.pathname.startsWith("/offline/")) {
    event.respondWith(fetch(req));
    return;
  }
  if (req.mode === "navigate" || (req.headers.get("accept") || "").includes("text/html")) {
    event.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(PAGES).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req).then((hit) => hit || caches.match("/home/")))
    );
    return;
  }
  event.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (req.method === "GET" && res.ok) {
        const copy = res.clone();
        caches.open(SHELL).then((c) => c.put(req, copy));
      }
      return res;
    }))
  );
});

self.addEventListener("sync", (event) => {
  if (event.tag === "masya-sync") {
    event.waitUntil(self.clients.matchAll({ type: "window" }).then((clients) => {
      clients.forEach((c) => c.postMessage({ type: "sync" }));
    }));
  }
});

self.addEventListener("message", (event) => {
  const data = event.data || {};
  if (data.type === "cache-urls" && Array.isArray(data.urls)) {
    event.waitUntil(caches.open(PAGES).then((c) => Promise.all(data.urls.map((u) => c.add(u).catch(() => {})))));
  }
});
