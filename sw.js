/**
 * Service Worker for ConfigStream
 * Handles caching, offline support, and background sync
 */

// Step 1: Load the shared cache configuration
// This MUST be the first line of code in this file
importScripts('/assets/js/cache-config.js');

// Step 2: Set up logging helper
const log = {
  info: (msg) => console.log(`[SW INFO] ${msg}`),
  error: (msg) => console.error(`[SW ERROR] ${msg}`),
  warn: (msg) => console.warn(`[SW WARN] ${msg}`)
};

// Step 3: Get configuration from the shared namespace
// The cache-config.js file populates globalThis.ConfigStreamCache
const config = globalThis.ConfigStreamCache;

// Validate that configuration loaded correctly
if (!config || !config.CACHE_NAME) {
  log.error('Cache configuration failed to load! Service Worker will not function properly.');
}

// ============================================================================
// INSTALL EVENT - Pre-cache essential files
// ============================================================================
self.addEventListener('install', (event) => {
  log.info('Service Worker installing...');

  event.waitUntil(
    (async () => {
      try {
        const cache = await caches.open(config.CACHE_NAME);

        // Pre-cache the essential URLs from configuration
        const urlsToCache = config.PRECACHE_URLS || [];

        if (urlsToCache.length === 0) {
          log.warn('No URLs configured for pre-caching');
          return;
        }

        log.info(`Pre-caching ${urlsToCache.length} URLs...`);

        // Use addAll for atomic operation - either all succeed or all fail
        await cache.addAll(urlsToCache);

        log.info('Pre-caching completed successfully');

        // Immediately activate this service worker
        await self.skipWaiting();
      } catch (error) {
        log.error(`Install failed: ${error.message}`);
        throw error;
      }
    })()
  );
});

// ============================================================================
// ACTIVATE EVENT - Clean up old caches
// ============================================================================
self.addEventListener('activate', (event) => {
  log.info('Service Worker activating...');

  event.waitUntil(
    (async () => {
      try {
        // Get all cache names
        const cacheNames = await caches.keys();

        // Delete old caches that don't match the current version
        const cachesToDelete = cacheNames.filter(
          (cacheName) => cacheName !== config.CACHE_NAME && cacheName.startsWith('configstream-')
        );

        if (cachesToDelete.length > 0) {
          log.info(`Cleaning up ${cachesToDelete.length} old cache(s)...`);
          await Promise.all(
            cachesToDelete.map((cacheName) => {
              log.info(`Deleting cache: ${cacheName}`);
              return caches.delete(cacheName);
            })
          );
        }

        // Take control of all clients
        await self.clients.claim();
        log.info('Service Worker activated and now controlling clients');
      } catch (error) {
        log.error(`Activation failed: ${error.message}`);
      }
    })()
  );
});

// ============================================================================
// FETCH EVENT - Handle requests with appropriate caching strategy
// ============================================================================
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip requests for non-GET methods
  if (request.method !== 'GET') {
    return;
  }

  // Skip browser extensions and non-http(s) protocols
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Determine which caching strategy to use based on configuration
  const strategy = getCacheStrategy(url.pathname);

  event.respondWith(handleRequest(request, strategy));
});

/**
 * Determine which caching strategy should be used for a URL
 */
function getCacheStrategy(pathname) {
  const strategies = config.CACHE_STRATEGY || {};

  // Check if URL is in networkOnly list
  if (strategies.networkOnly?.some((path) => pathname === path)) {
    return 'networkOnly';
  }

  // Check if URL is in networkFirst list
  if (strategies.networkFirst?.some((path) => pathname === path)) {
    return 'networkFirst';
  }

  // Check if URL is in cacheFirst list
  if (strategies.cacheFirst?.some((path) => pathname === path)) {
    return 'cacheFirst';
  }

  // Default strategy for everything else
  return 'networkFirst';
}

/**
 * Handle a fetch request based on the selected strategy
 */
async function handleRequest(request, strategy) {
  const cacheName = config.CACHE_NAME;

  try {
    switch (strategy) {
      case 'networkOnly':
        return await networkOnly(request);

      case 'networkFirst':
        return await networkFirst(request, cacheName);

      case 'cacheFirst':
        return await cacheFirst(request, cacheName);

      default:
        return await networkFirst(request, cacheName);
    }
  } catch (error) {
    log.error(`Request failed for ${request.url}: ${error.message}`);

    // Try to return from cache as fallback
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      log.info(`Serving from cache (fallback): ${request.url}`);
      return cachedResponse;
    }

    // Return offline page if available
    return await caches.match('/index.html') || createOfflineResponse();
  }
}

/**
 * Network-only strategy: Always fetch fresh, never use cache
 */
async function networkOnly(request) {
  log.info(`[networkOnly] ${request.url}`);
  return await fetch(request);
}

/**
 * Network-first strategy: Try network first, fall back to cache
 */
async function networkFirst(request, cacheName) {
  const url = request.url;
  const timeout = config.CACHE_CONFIG?.networkTimeout || 5000;

  try {
    // Create a fetch request with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const networkResponse = await fetch(request, {
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    // If successful, cache it and return
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
      log.info(`[networkFirst] Fresh from network: ${url}`);
      return networkResponse;
    }

    // If not ok, try cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      log.warn(`[networkFirst] Network returned ${networkResponse.status}, using cache: ${url}`);
      return cachedResponse;
    }

    return networkResponse;
  } catch (error) {
    // Network failed, try cache
    log.warn(`[networkFirst] Network failed, trying cache: ${url}`);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    throw error;
  }
}

/**
 * Cache-first strategy: Use cache if available, fall back to network
 */
async function cacheFirst(request, cacheName) {
  const url = request.url;

  // Try to get from cache first
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    log.info(`[cacheFirst] From cache: ${url}`);
    return cachedResponse;
  }

  // Cache miss, fetch from network
  log.info(`[cacheFirst] Cache miss, fetching: ${url}`);
  const networkResponse = await fetch(request);

  // Cache successful responses
  if (networkResponse.ok) {
    const cache = await caches.open(cacheName);
    cache.put(request, networkResponse.clone());
  }

  return networkResponse;
}

/**
 * Create a simple offline response
 */
function createOfflineResponse() {
  return new Response(
    '<html><body><h1>You are offline</h1><p>This page is not available while offline.</p></body></html>',
    {
      headers: { 'Content-Type': 'text/html' },
      status: 503,
      statusText: 'Service Unavailable'
    }
  );
}