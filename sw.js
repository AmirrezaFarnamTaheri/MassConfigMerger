/**
 * Service Worker - Handles offline and caching strategies
 */

importScripts('/assets/js/cache-config.js');

/**
 * Install event - pre-cache essential files
 */
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Pre-caching essential files');
        return cache.addAll(PRECACHE_URLS);
      })
      .then(() => self.skipWaiting())
  );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => cacheName.startsWith('configstream-') && cacheName !== CACHE_NAME)
            .map((cacheName) => {
              console.log(`Deleting old cache: ${cacheName}`);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => self.clients.claimAll())
  );
});

/**
 * Fetch event - implement caching strategy
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip cross-origin requests
  if (url.origin !== location.origin) {
    return;
  }

  // Strategy 1: Network first for API responses (with cache fallback)
  if (url.pathname.startsWith('/output/') && url.pathname.endsWith('.json')) {
    return event.respondWith(networkFirst(request));
  }

  // Strategy 2: Network first for static assets
  if (url.pathname.startsWith('/assets/')) {
    return event.respondWith(networkFirst(request));
  }

  // Strategy 3: Network first for HTML pages
  if (request.method === 'GET') {
    return event.respondWith(networkFirst(request));
  }
});

/**
 * Network first strategy - try network, fallback to cache
 */
async function networkFirst(request) {
  try {
    const response = await fetch(request, {
      cache: 'no-store'
    });

    // Cache successful responses
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.log(`Network failed for ${request.url}, using cache`);

    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }

    // Return offline page if available
    return caches.match('/offline.html')
      .then(response => response || new Response(
        'Offline - Please check your connection',
        { status: 503, statusText: 'Service Unavailable' }
      ));
  }
}

/**
 * Cache first strategy - use cache, fallback to network
 */
async function cacheFirst(request) {
  try {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }

    const response = await fetch(request);

    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.error(`Offline - cannot fetch ${request.url}`);
    return new Response(
      'Offline',
      { status: 503, statusText: 'Service Unavailable' }
    );
  }
}

console.log('Service Worker loaded');