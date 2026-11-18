const CACHE_NAME = 'weathergpt-shell-v2';
const API_CACHE_NAME = 'weathergpt-api-v1';
const MAX_API_AGE_MS = 12 * 60 * 60 * 1000; // 12 hours bounded age

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.json',
  '/icon-192.svg',
  '/icon-512.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_ASSETS))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME && key !== API_CACHE_NAME) {
            return caches.delete(key);
          }
        })
      )
    )
  );
  self.clients.claim();
});

// Update prompt listener
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Stale-while-revalidate for cacheable read-only API calls (forecast, places, alerts, sources)
  if (url.pathname.startsWith('/v1/')) {
    // Only cache GET queries, not streaming chat or websocket
    if (url.pathname.includes('/chat')) return;

    event.respondWith(
      caches.open(API_CACHE_NAME).then(async (apiCache) => {
        const cachedResponse = await apiCache.match(req);

        // Fetch fresh copy in background
        const networkFetch = fetch(req)
          .then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              const headers = new Headers(networkResponse.headers);
              headers.set('sw-fetched-at', Date.now().toString());
              const stamped = new Response(networkResponse.clone().body, {
                status: networkResponse.status,
                statusText: networkResponse.statusText,
                headers,
              });
              apiCache.put(req, stamped);
            }
            return networkResponse;
          })
          .catch(() => cachedResponse);

        if (cachedResponse) {
          const fetchedAt = Number(cachedResponse.headers.get('sw-fetched-at') || 0);
          const isFresh = Date.now() - fetchedAt < MAX_API_AGE_MS;
          if (isFresh) {
            // Return cached and update background
            return cachedResponse;
          }
        }

        return (await networkFetch) || cachedResponse;
      })
    );
    return;
  }

  // App shell caching
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;

      return fetch(req)
        .then((resp) => {
          if (resp && resp.status === 200) {
            const copy = resp.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          }
          return resp;
        })
        .catch(() => {
          if (req.mode === 'navigate') {
            return caches.match('/offline.html');
          }
        });
    })
  );
});
