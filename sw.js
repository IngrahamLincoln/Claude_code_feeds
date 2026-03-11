// AI Reader — Service Worker
// Caches the app shell for offline use; serves Reddit API calls from network with cache fallback.

const CACHE_NAME = 'ai-reader-v1';
const SHELL = [
  './',
  './index.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './apple-touch-icon.png',
];

// Install: cache the app shell
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      // Add what's available; don't fail install if an asset is missing
      Promise.allSettled(SHELL.map(url => cache.add(url)))
    )
  );
});

// Activate: delete old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch strategy:
//  - Reddit JSON API → Network first, fallback to cache
//  - Everything else  → Cache first, fallback to network
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET and cross-origin non-Reddit requests
  if (request.method !== 'GET') return;

  // Reddit API: network first
  if (url.hostname === 'www.reddit.com' && url.pathname.endsWith('.json')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // App shell: cache first
  if (url.origin === self.location.origin) {
    event.respondWith(cacheFirst(request));
    return;
  }
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(request);
    return cached || new Response(JSON.stringify({ error: 'offline' }), {
      headers: { 'Content-Type': 'application/json' },
      status: 503,
    });
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Return offline fallback for navigation requests
    if (request.mode === 'navigate') {
      const cached = await caches.match('./index.html');
      if (cached) return cached;
    }
    return new Response('Offline', { status: 503 });
  }
}
