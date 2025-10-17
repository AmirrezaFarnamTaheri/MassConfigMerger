// Cache configuration
const CACHE_CONFIG = {
  metadataExpiry: 5 * 60 * 1000,        // 5 minutes
  proxiesExpiry: 15 * 60 * 1000,        // 15 minutes
  statsExpiry: 10 * 60 * 1000,          // 10 minutes
};

// Memory cache for API responses
const cache = {
  metadata: { data: null, expiry: 0 },
  proxies: { data: null, expiry: 0 },
  statistics: { data: null, expiry: 0 },
};

/**
 * Generate cache-busting query parameter
 * @returns {string} Cache-bust token with timestamp
 */
function getCacheBust() {
  return `?cb=${Date.now()}`;
}

/**
 * Check if cached data is still valid
 * @param {string} key Cache key
 * @returns {boolean} True if cache is valid
 */
function isCacheValid(key) {
  if (!cache[key] || !cache[key].data) return false;
  return Date.now() < cache[key].expiry;
}

/**
 * Fetch with retry logic
 * @param {string} url URL to fetch
 * @param {number} retries Number of retries (default: 3)
 * @param {number} delay Delay between retries in ms (default: 1000)
 * @returns {Promise<Response>}
 */
async function fetchWithRetry(url, retries = 3, delay = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Cache-Control': 'no-cache'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response;
    } catch (error) {
      if (i < retries - 1) {
        console.warn(`Fetch attempt ${i + 1} failed, retrying in ${delay}ms:`, error.message);
        await new Promise(resolve => setTimeout(resolve, delay));
        delay = Math.min(delay * 2, 8000); // Exponential backoff, max 8s
      } else {
        throw error;
      }
    }
  }
}

/**
 * Fetch metadata with caching
 * @returns {Promise<Object>} Metadata object
 */
async function fetchMetadata() {
  if (isCacheValid('metadata')) {
    console.log('📦 Using cached metadata');
    return cache.metadata.data;
  }

  try {
    const url = `output/metadata.json${getCacheBust()}`;
    const response = await fetchWithRetry(url, 3, 1000);
    const data = await response.json();

    cache.metadata = {
      data,
      expiry: Date.now() + CACHE_CONFIG.metadataExpiry
    };

    return data;
  } catch (error) {
    console.error('❌ Failed to fetch metadata:', error);
    if (cache.metadata.data) {
      console.log('📦 Using stale metadata from cache');
      return cache.metadata.data;
    }
    throw error;
  }
}

/**
 * Fetch all proxies with caching and pagination support
 * @returns {Promise<Array>} Array of proxy objects
 */
async function fetchProxies() {
  if (isCacheValid('proxies')) {
    console.log('📦 Using cached proxies');
    return cache.proxies.data;
  }

  try {
    const url = `output/proxies.json${getCacheBust()}`;
    const response = await fetchWithRetry(url, 3, 1000);
    const data = await response.json();

    // Validate proxy data
    if (!Array.isArray(data)) {
      throw new Error('Invalid proxy data format: expected array');
    }

    // Enrich proxies with calculated fields
    const enrichedProxies = data.map(proxy => ({
      ...proxy,
      location: {
        city: proxy.city || 'Unknown',
        country: proxy.country_code || 'XX',
        flag: getCountryFlag(proxy.country_code)
      },
      latency: proxy.latency || null,
      protocolColor: getProtocolColor(proxy.protocol),
      statusIcon: getStatusIcon(proxy.is_working !== false)
    }));

    cache.proxies = {
      data: enrichedProxies,
      expiry: Date.now() + CACHE_CONFIG.proxiesExpiry
    };

    console.log(`✅ Loaded ${enrichedProxies.length} proxies`);
    return enrichedProxies;
  } catch (error) {
    console.error('❌ Failed to fetch proxies:', error);
    if (cache.proxies.data) {
      console.log('📦 Using stale proxies from cache');
      return cache.proxies.data;
    }
    throw error;
  }
}

/**
 * Fetch statistics with caching
 * @returns {Promise<Object>} Statistics object
 */
async function fetchStatistics() {
  if (isCacheValid('statistics')) {
    console.log('📦 Using cached statistics');
    return cache.statistics.data;
  }

  try {
    const url = `output/statistics.json${getCacheBust()}`;
    const response = await fetchWithRetry(url, 3, 1000);
    const data = await response.json();

    cache.statistics = {
      data,
      expiry: Date.now() + CACHE_CONFIG.statsExpiry
    };

    return data;
  } catch (error) {
    console.error('❌ Failed to fetch statistics:', error);
    if (cache.statistics.data) {
      console.log('📦 Using stale statistics from cache');
      return cache.statistics.data;
    }
    throw error;
  }
}

/**
 * Get color for protocol badge
 * @param {string} protocol Protocol name
 * @returns {string} CSS class or hex color
 */
function getProtocolColor(protocol) {
  const colors = {
    'vmess': '#FF6B6B',
    'vless': '#4ECDC4',
    'shadowsocks': '#45B7D1',
    'trojan': '#96CEB4',
    'hysteria': '#FFEAA7',
    'hysteria2': '#DFE6E9',
    'tuic': '#A29BFE',
    'wireguard': '#74B9FF',
    'naive': '#FD79A8',
    'http': '#FDCB6E',
    'https': '#6C5CE7',
    'socks': '#00B894'
  };
  return colors[protocol?.toLowerCase()] || '#95A5A6';
}

/**
 * Get country flag emoji
 * @param {string} countryCode ISO country code
 * @returns {string} Flag emoji
 */
function getCountryFlag(countryCode) {
  if (!countryCode || countryCode.length !== 2) return '🌍';

  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map(char => 127397 + char.charCodeAt(0));

  return String.fromCodePoint(...codePoints);
}

/**
 * Get status icon
 * @param {boolean} isWorking Working status
 * @returns {string} Status icon emoji
 */
function getStatusIcon(isWorking) {
  return isWorking ? '✅' : '❌';
}

/**
 * Debounce function for expensive operations
 * @param {Function} func Function to debounce
 * @param {number} wait Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function
 * @param {Function} func Function to throttle
 * @param {number} limit Limit time in milliseconds
 * @returns {Function} Throttled function
 */
function throttle(func, limit) {
  let inThrottle;
  return function (...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Update DOM element content safely
 * @param {string} elementId Element ID
 * @param {string|number} content Content to set
 * @param {string} method Method: 'text' or 'html' (default: 'text')
 */
function updateElement(elementId, content, method = 'text') {
  const element = document.getElementById(elementId);
  if (!element) {
    console.warn(`Element with ID "${elementId}" not found`);
    return;
  }

  if (method === 'html') {
    // Only set innerHTML if absolutely necessary and sanitized
    element.innerHTML = sanitizeHTML(content);
  } else {
    element.textContent = content;
  }
}

/**
 * Basic HTML sanitization
 * @param {string} html HTML to sanitize
 * @returns {string} Sanitized HTML
 */
function sanitizeHTML(html) {
  const div = document.createElement('div');
  div.textContent = html;
  return div.innerHTML;
}

/**
 * Clear all caches
 */
function clearCache() {
  Object.keys(cache).forEach(key => {
    cache[key] = { data: null, expiry: 0 };
  });
  console.log('🗑️ Cache cleared');
}

/**
 * Format timestamp for display
 * @param {string} isoString ISO 8601 timestamp
 * @returns {string} Formatted timestamp
 */
function formatTimestamp(isoString) {
  try {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short'
    });
  } catch {
    return isoString;
  }
}

/**
 * Export object as JSON file
 * @param {Object} data Data to export
 * @param {string} filename Filename for export
 */
function exportJSON(data, filename = 'export.json') {
  const jsonString = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    fetchMetadata,
    fetchProxies,
    fetchStatistics,
    debounce,
    throttle,
    updateElement,
    clearCache,
    formatTimestamp,
    exportJSON,
    getProtocolColor,
    getCountryFlag,
    getCacheBust
  };
}

console.log('✅ Utils.js loaded successfully');