/**
 * Unified Cache Configuration
 * This file should be imported by both sw.js and cache-manager.js
 */

// Create a namespace to avoid global scope pollution
globalThis.ConfigStreamCache = {
  CACHE_VERSION: '1.0.2',
  CACHE_NAME: 'configstream-v1-0-2',

  // Cache timing configuration
  CACHE_CONFIG: {
    metadataExpiry: 2 * 60 * 1000,        // 2 minutes
    proxiesExpiry: 10 * 60 * 1000,       // 10 minutes
    statsExpiry: 5 * 60 * 1000,          // 5 minutes
    networkTimeout: 5000,                // 5 seconds
    staleWhileRevalidate: true
  },

  // URLs that need special cache handling
  CACHE_STRATEGY: {
    networkOnly: ['/output/metadata.json'],
    networkFirst: ['/output/proxies.json', '/output/statistics.json'],
    cacheFirst: [
      '/assets/css/framework.css',
      '/assets/js/utils.js',
      '/assets/js/main.js',
      '/index.html',
      '/proxies.html',
      '/statistics.html'
    ]
  },

  // Pre-cache essential files
  PRECACHE_URLS: [
    '/',
    '/index.html',
    '/proxies.html',
    '/statistics.html',
    '/assets/css/framework.css',
    '/assets/js/utils.js',
    '/assets/js/cache-manager.js',
    '/assets/js/main.js'
  ]
};

// For environments that support module exports (like Node.js for testing)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = globalThis.ConfigStreamCache;
}