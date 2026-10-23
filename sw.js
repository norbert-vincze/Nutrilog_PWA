/* Nutrilog service worker: offline use.
   - ciqual.json and usda.json (the food tables): cache-first, kept in their own cache (DATA) that is NOT renewed with every app version.
     Change the number in DATA only when one of these two files changes.
   - every other own file: network-first (always revalidated), falling back to the cache when offline
   - calls to other sites (Open Food Facts) are left alone */
const CACHE = 'nutrilog-v9';   // keep in step with VERSION in app.js
const DATA = 'nutrilog-data-1';
const DATA_FILES = ['ciqual.json', 'usda.json'];
const SHELL = ['./', 'index.html', 'style.css', 'app.js', 'manifest.webmanifest', 'icon.svg',
  'icon-180.png', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'zxing.min.js'];

self.addEventListener('install', (e) => {
  e.waitUntil(Promise.all([
    caches.open(CACHE).then((c) => c.addAll(SHELL.map((u) => new Request(u, { cache: 'reload' })))),
    caches.open(DATA).then(async (c) => { for (const u of DATA_FILES) if (!(await c.match(u))) await c.add(new Request(u, { cache: 'reload' })); }),
  ]).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE && k !== DATA).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  if (DATA_FILES.some((f) => url.pathname.endsWith('/' + f))) {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(DATA).then((c) => c.put(req, copy));
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
