/* Nutrilog service worker: offline use.
   - ciqual.json, usda.json and dmbio.json (the food tables): cache-first, each kept in a cache of its own that is NOT renewed with every app version.
     Change the number of a cache only when its file changes (ciqual.json and usda.json share nutrilog-data-1, dmbio.json has nutrilog-dmbio-1).
   - every other own file: network-first (always revalidated), falling back to the cache when offline
   - calls to other sites (Open Food Facts) are left alone */
const CACHE = 'nutrilog-v13';   // keep in step with VERSION in app.js
const DATA = { 'ciqual.json': 'nutrilog-data-1', 'usda.json': 'nutrilog-data-1', 'dmbio.json': 'nutrilog-dmbio-1' };
const SHELL = ['./', 'index.html', 'style.css', 'app.js', 'manifest.webmanifest', 'icon.svg',
  'icon-180.png', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'zxing.min.js'];
const dataCacheOf = (pathname) => { const f = Object.keys(DATA).find((n) => pathname.endsWith('/' + n)); return f ? DATA[f] : null; };

self.addEventListener('install', (e) => {
  e.waitUntil(Promise.all([
    caches.open(CACHE).then((c) => c.addAll(SHELL.map((u) => new Request(u, { cache: 'reload' })))),
    ...Object.entries(DATA).map(([file, name]) => caches.open(name).then(async (c) => { if (!(await c.match(file))) await c.add(new Request(file, { cache: 'reload' })); })),
  ]).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  const keep = new Set([CACHE, ...Object.values(DATA)]);
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !keep.has(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  const dataCache = dataCacheOf(url.pathname);
  if (dataCache) {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(dataCache).then((c) => c.put(req, copy));
        return res;
      }))
    );
    return;
  }

  e.respondWith(
    fetch(req, { cache: 'no-cache' }).then((res) => {   // no-cache = always ask the server if the file changed (GitHub Pages keeps files in the browser cache for 10 minutes otherwise)
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy));
      return res;
    }).catch(() => caches.match(req).then((hit) => hit || caches.match('index.html')))
  );
});
