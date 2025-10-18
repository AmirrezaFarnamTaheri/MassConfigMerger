/**
 * Unified Cache Configuration
 * This file should be imported by both sw.js and cache-manager.js
 */

// Single source of truth for cache version
const CACHE_VERSION = '1.0.2';
const CACHE_NAME = `configstream-v${CACHE_VERSION.replace(/\./g, '-')}`;

// Cache timing configuration
const CACHE_CONFIG = {
  metadataExpiry: 2 * 60 * 1000,        // 2 minutes (reduced for faster updates)
  proxiesExpiry: 10 * 60 * 1000,        // 10 minutes
  statsExpiry: 5 * 60 * 1000,           // 5 minutes
  networkTimeout: 5000,                  // 5 seconds network timeout
  staleWhileRevalidate: true            // Use stale cache while fetching new data
};

// URLs that need special cache handling
const CACHE_STRATEGY = {
  // Always fetch fresh (bypass cache)
  networkOnly: [
    '/output/metadata.json'  // Always get latest metadata
  ],
  // Network first with cache fallback
  networkFirst: [
    '/output/proxies.json',
    '/output/statistics.json'
  ],
  // Cache first with network fallback
  cacheFirst: [
    '/assets/css/framework.css',
    '/assets/js/utils.js',
    '/assets/js/main.js',
    '/index.html',
    '/proxies.html',
    '/statistics.html'
  ]
};

// Pre-cache essential files
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/proxies.html',
  '/statistics.html',
  '/assets/css/framework.css',
  '/assets/js/utils.js',
  '/assets/js/cache-manager.js',
  '/assets/js/main.js'
];

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    CACHE_VERSION,
    CACHE_NAME,
    CACHE_CONFIG,
    CACHE_STRATEGY,
    PRECACHE_URLS
  };
}