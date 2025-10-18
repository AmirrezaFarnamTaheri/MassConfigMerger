/**
 * Cache Manager for ConfigStream
 * Manages cache expiry, stale-while-revalidate, and data freshness
 * Runs in the main browser thread (NOT in the service worker)
 */

// Step 1: Verify that cache configuration is available
// This assumes cache-config.js was loaded BEFORE this script in index.html
if (!globalThis.ConfigStreamCache) {
  console.error('[CacheManager] FATAL: Cache configuration not loaded! Make sure cache-config.js is loaded first.');
  throw new Error('Cache configuration unavailable');
}

// Step 2: Get configuration from the shared namespace
const config = globalThis.ConfigStreamCache;

// Step 3: Initialize the cache manager
class CacheManager {
  constructor() {
    this.cacheName = config.CACHE_NAME;
    this.config = config.CACHE_CONFIG;
    this.strategy = config.CACHE_STRATEGY;
    this.log = this.createLogger();
    this.initialized = false;

    this.log.info('CacheManager initialized with cache name: ' + this.cacheName);
  }

  /**
   * Create a logger function for consistent debugging
   */
  createLogger() {
    return {
      info: (msg) => console.log(`[CacheManager] ${msg}`),
      warn: (msg) => console.warn(`[CacheManager] ${msg}`),
      error: (msg) => console.error(`[CacheManager] ${msg}`)
    };
  }

  /**
   * Initialize the cache manager and register service worker
   */
  async init() {
    if (this.initialized) {
      this.log.warn('Already initialized, skipping...');
      return;
    }

    try {
      // Check if service workers are supported
      if (!('serviceWorker' in navigator)) {
        this.log.error('Service Workers not supported in this browser');
        return;
      }

      // Register the service worker
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      });

      this.log.info('Service Worker registered successfully');
      this.swRegistration = registration;

      // Listen for updates to the service worker
      registration.addEventListener('updatefound', () => {
        this.log.info('Service Worker update found');
        const newWorker = registration.installing;

        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            this.log.info('New Service Worker installed, ready to activate');
            this.notifyUpdate();
          }
        });
      });

      // Check for updates periodically
      this.startUpdateCheck();

      this.initialized = true;
    } catch (error) {
      this.log.error('Failed to initialize: ' + error.message);
    }
  }

  /**
   * Start checking for service worker updates periodically
   */
  startUpdateCheck() {
    // Check for updates every 5 minutes
    setInterval(() => {
      if (this.swRegistration) {
        this.swRegistration.update().catch((error) => {
          this.log.warn('Failed to check for updates: ' + error.message);
        });
      }
    }, 5 * 60 * 1000);
  }

  /**
   * Notify the user that an update is available
   */
  notifyUpdate() {
    // Dispatch a custom event that your app can listen for
    window.dispatchEvent(new CustomEvent('sw-update-ready'));
  }

  /**
   * Fetch data with cache-aware behavior
   * This respects the cache expiry times set in configuration
   */
  async fetchWithCache(url, options = {}) {
    const { bypassCache = false, expiry = null } = options;

    if (bypassCache) {
      return this.fetchFresh(url);
    }

    try {
      // Check if we have cached data and if it's still fresh
      const cachedData = await this.getCachedData(url);

      if (cachedData && !this.isExpired(cachedData)) {
        this.log.info(`Using cached data for ${url}`);

        // Determine which expiry period to use
        const expiryMs = expiry || this.getExpiryForUrl(url);

        // If stale-while-revalidate is enabled, fetch fresh data in the background
        if (this.config.staleWhileRevalidate && this.isStale(cachedData, expiryMs)) {
          this.log.info(`Revalidating in background: ${url}`);
          this.fetchFresh(url).catch((error) => {
            this.log.warn(`Background revalidation failed: ${error.message}`);
          });
        }

        return cachedData.data;
      }

      // Cache miss or expired, fetch fresh
      return await this.fetchFresh(url);
    } catch (error) {
      this.log.error(`fetchWithCache failed for ${url}: ${error.message}`);
      throw error;
    }
  }

  /**
   * Fetch fresh data from the network
   */
  async fetchFresh(url) {
    this.log.info(`Fetching fresh data: ${url}`);

    const timeout = this.config.networkTimeout || 5000;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        signal: controller.signal,
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Cache the fresh data
      await this.cacheData(url, data);

      return data;
    } catch (error) {
      clearTimeout(timeoutId);
      this.log.error(`fetchFresh failed for ${url}: ${error.message}`);
      throw error;
    }
  }

  /**
   * Get data from the browser cache
   */
  async getCachedData(url) {
    if (!('caches' in window)) {
      return null;
    }

    try {
      const cache = await caches.open(this.cacheName);
      const response = await cache.match(url);

      if (!response) {
        return null;
      }

      const data = await response.json();
      const timestamp = response.headers.get('X-Cache-Timestamp');

      return {
        data,
        timestamp: timestamp ? parseInt(timestamp) : null
      };
    } catch (error) {
      this.log.warn(`Failed to get cached data for ${url}: ${error.message}`);
      return null;
    }
  }

  /**
   * Store data in the browser cache
   */
  async cacheData(url, data) {
    if (!('caches' in window)) {
      return;
    }

    try {
      const cache = await caches.open(this.cacheName);
      const response = new Response(JSON.stringify(data), {
        status: 200,
        statusText: 'OK',
        headers: new Headers({
          'Content-Type': 'application/json',
          'X-Cache-Timestamp': Date.now().toString()
        })
      });

      await cache.put(url, response);
      this.log.info(`Cached data for ${url}`);
    } catch (error) {
      this.log.error(`Failed to cache data for ${url}: ${error.message}`);
    }
  }

  /**
   * Check if cached data has expired
   */
  isExpired(cachedData) {
    if (!cachedData.timestamp) {
      return true; // No timestamp means it's invalid
    }

    const age = Date.now() - cachedData.timestamp;
    const maxAge = this.config.metadataExpiry || 5 * 60 * 1000; // Default 5 minutes

    return age > maxAge;
  }

  /**
   * Check if cached data is stale (but not expired)
   * Used for stale-while-revalidate
   */
  isStale(cachedData, expiryMs) {
    if (!cachedData.timestamp) {
      return true;
    }

    const age = Date.now() - cachedData.timestamp;
    const staleThreshold = (expiryMs || this.config.metadataExpiry) * 0.75; // 75% of max age

    return age > staleThreshold;
  }

  /**
   * Determine the appropriate cache expiry time for a URL
   */
  getExpiryForUrl(url) {
    if (url.includes('metadata')) {
      return this.config.metadataExpiry || 2 * 60 * 1000;
    } else if (url.includes('proxies')) {
      return this.config.proxiesExpiry || 10 * 60 * 1000;
    } else if (url.includes('statistics')) {
      return this.config.statsExpiry || 5 * 60 * 1000;
    }

    return 5 * 60 * 1000; // Default 5 minutes
  }

  /**
   * Clear all caches
   */
  async clearCache() {
    if (!('caches' in window)) {
      return;
    }

    try {
      const cacheNames = await caches.keys();
      await Promise.all(
        cacheNames.map((name) => {
          this.log.info(`Deleting cache: ${name}`);
          return caches.delete(name);
        })
      );

      this.log.info('All caches cleared');
    } catch (error) {
      this.log.error(`Failed to clear caches: ${error.message}`);
    }
  }

  /**
   * Get cache statistics
   */
  async getCacheStats() {
    if (!('caches' in window)) {
      return null;
    }

    try {
      const cacheNames = await caches.keys();
      const stats = {
        totalCaches: cacheNames.length,
        currentCache: this.cacheName,
        caches: {}
      };

      for (const name of cacheNames) {
        const cache = await caches.open(name);
        const keys = await cache.keys();
        stats.caches[name] = keys.length;
      }

      return stats;
    } catch (error) {
      this.log.error(`Failed to get cache stats: ${error.message}`);
      return null;
    }
  }
}

// Step 4: Create a global instance
const cacheManager = new CacheManager();

// Step 5: Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    cacheManager.init().catch((error) => {
      console.error('Failed to initialize CacheManager:', error);
    });
  });
} else {
  cacheManager.init().catch((error) => {
    console.error('Failed to initialize CacheManager:', error);
  });
}