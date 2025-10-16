/**
 * ConfigStream - Shared JavaScript Utilities
 * Common functions used across all pages
 */

// ============================================
// PATH & URL UTILITIES
// ============================================

/**
 * Get the base path for GitHub Pages
 * Handles both project pages and custom domains
 */
function getBasePath() {
    const pathname = window.location.pathname;
    
    // Check if running on GitHub Pages project site
    if (pathname.includes('/ConfigStream/')) {
        return '/ConfigStream/';
    }
    
    // For root domain or localhost
    return pathname.endsWith('/') ? pathname : '/';
}

/**
 * Fetch with cache-busting and proper path resolution
 * @param {string} relativePath - Path relative to base
 * @returns {Promise<Response>}
 */
async function fetchWithPath(relativePath) {
    const BASE_PATH = getBasePath();
    const cacheBust = `_=${new Date().getTime()}`;
    const separator = relativePath.includes('?') ? '&' : '?';
    const fullPath = `${BASE_PATH}${relativePath}${separator}${cacheBust}`;
    
    try {
        const response = await fetch(fullPath);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response;
    } catch (error) {
        console.error(`Failed to fetch ${fullPath}:`, error);
        throw error;
    }
}

/**
 * Build full URL for file downloads
 * @param {string} relativePath - Path relative to base
 * @returns {string}
 */
function getFullUrl(relativePath) {
    const BASE_PATH = getBasePath();
    return `${window.location.origin}${BASE_PATH}${relativePath}`;
}

// ============================================
// DATA FETCHING
// ============================================

/**
 * Fetch metadata with error handling
 * @returns {Promise<Object>}
 */
async function fetchMetadata() {
    try {
        const response = await fetchWithPath('output/metadata.json');
        return await response.json();
    } catch (error) {
        console.error('Error fetching metadata:', error);
        return {
            generated_at: new Date().toISOString(),
            cache_bust: Date.now(),
            version: '1.0.0'
        };
    }
}

/**
 * Fetch statistics with error handling
 * @returns {Promise<Object>}
 */
async function fetchStatistics() {
    try {
        const response = await fetchWithPath('output/statistics.json');
        return await response.json();
    } catch (error) {
        console.error('Error fetching statistics:', error);
        return {
            total_tested: 0,
            working: 0,
            failed: 0,
            success_rate: 0,
            latency: { average: 0 }
        };
    }
}

/**
 * Fetch proxies with error handling
 * @returns {Promise<Array>}
 */
async function fetchProxies() {
    try {
        const response = await fetchWithPath('output/proxies.json');
        const proxies = await response.json();
        return Array.isArray(proxies) ? proxies : [];
    } catch (error) {
        console.error('Error fetching proxies:', error);
        return [];
    }
}

// ============================================
// TIME & DATE UTILITIES
// ============================================

/**
 * Format date to human-readable string
 * @param {Date|string} date - Date object or ISO string
 * @returns {string}
 */
function formatDate(date) {
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
    });
}

// ============================================
// UI UTILITIES
// ============================================

/**
 * Update element with loading state
 * @param {string} elementId - Element ID
 * @param {string|number} value - Value to display
 * @param {Object} options - Options
 */
function updateElement(elementId, value, options = {}) {
    const el = document.getElementById(elementId);
    if (!el) return;

    el.textContent = value;
    el.classList.remove('skeleton', 'loading');

    if (options.removeStyles) {
        el.style.width = 'auto';
        el.style.height = 'auto';
    }

    if (options.addClass) {
        el.classList.add(options.addClass);
    }
}

async function copyToClipboard(text, button = null) {
    try {
        await navigator.clipboard.writeText(text);
        
        if (button) {
            const originalHTML = button.innerHTML;
            button.innerHTML = '<i data-feather="check"></i><span>Copied!</span>';
            button.classList.add('copied');
            
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
            
            setTimeout(() => {
                button.innerHTML = originalHTML;
                button.classList.remove('copied');
                if (typeof feather !== 'undefined') {
                    feather.replace();
                }
            }, 2000);
        }
        
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);

        if (button) {
            const originalHTML = button.innerHTML;
            button.innerHTML = '<i data-feather="x"></i><span>Failed</span>';
            button.classList.add('error');

            if (typeof feather !== 'undefined') {
                feather.replace();
            }

            setTimeout(() => {
                button.innerHTML = originalHTML;
                button.classList.remove('error');
                if (typeof feather !== 'undefined') {
                    feather.replace();
                }
            }, 2000);
        } else {
            alert('Failed to copy. Please try again.');
        }
        return false;
    }
}

function initCopyButtons() {
    document.addEventListener('click', async (e) => {
        const button = e.target.closest('.copy-btn');
        if (!button) return;
        
        const config = button.dataset.config;
        const file = button.dataset.file;
        
        let textToCopy;
        
        if (config) {
            textToCopy = decodeURIComponent(config);
        } else if (file) {
            textToCopy = getFullUrl(file);
        } else {
            return;
        }
        
        await copyToClipboard(textToCopy, button);
    });
}