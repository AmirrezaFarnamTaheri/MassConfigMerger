/**
 * Cache Manager - Handles browser caching strategy
 */

// For module environments, load the configuration
if (typeof importScripts === 'function') {
  importScripts('/assets/js/cache-config.js');
}

/**
 * Initialize service worker if supported
 */
async function initServiceWorker() {
  if (!('serviceWorker' in navigator)) {
    console.log('Service Worker not supported');
    return;
  }

  try {
    const registration = await navigator.serviceWorker.register('/sw.js', {
      scope: '/'
    });
    console.log('✅ Service Worker registered:', registration);
  } catch (error) {
    console.error('Service Worker registration failed:', error);
  }
}

/**
 * Prefetch critical resources
 */
async function prefetchCriticalResources() {
  if (!('caches' in window)) {
    console.log('Cache API not available');
    return;
  }

  try {
    const cache = await caches.open(CACHE_NAME);
    const resources = [
      '/assets/css/framework.css',
      '/assets/js/utils.js',
      '/index.html'
    ];

    await Promise.all(
      resources.map(url =>
        fetch(url, { credentials: 'same-origin' })
          .then(response => {
            if (response.ok) {
              cache.put(url, response);
              console.log(`✅ Prefetched: ${url}`);
            }
          })
          .catch(error => console.warn(`Failed to prefetch ${url}:`, error))
      )
    );
  } catch (error) {
    console.error('Prefetch failed:', error);
  }
}

/**
 * Clear old caches
 */
async function clearOldCaches() {
  if (!('caches' in window)) return;

  const cacheNames = await caches.keys();
  const oldCaches = cacheNames.filter(name => !name.startsWith('configstream-'));

  await Promise.all(
    oldCaches.map(cacheName => {
      console.log(`🗑️ Deleting old cache: ${cacheName}`);
      return caches.delete(cacheName);
    })
  );
}

/**
 * Check for updates and notify user
 */
async function checkForUpdates() {
  try {
    const response = await fetch('/output/metadata.json', {
      cache: 'no-store',
      method: 'GET'
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const metadata = await response.json();
    const lastCheck = localStorage.getItem('lastUpdateCheck');
    const lastGenerated = localStorage.getItem('lastGenerated');

    localStorage.setItem('lastUpdateCheck', new Date().toISOString());
    localStorage.setItem('lastGenerated', metadata.generated_at);

    if (lastGenerated && lastGenerated !== metadata.generated_at) {
      console.log('🔄 New data available!');
      // Emit custom event that pages can listen to
      window.dispatchEvent(new CustomEvent('dataUpdated', {
        detail: metadata
      }));
    }
  } catch (error) {
    console.error('Update check failed:', error);
  }
}

/**
 * Initialize all cache features
 */
async function initCacheSystem() {
  console.log('🚀 Initializing cache system...');

  await clearOldCaches();
  await initServiceWorker();
  await prefetchCriticalResources();

  // Check for updates periodically (every 5 minutes)
  setInterval(checkForUpdates, 5 * 60 * 1000);

  // Initial check
  await checkForUpdates();

  console.log('✅ Cache system initialized');
}

// Auto-initialize when document is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCacheSystem);
} else {
  initCacheSystem();
}