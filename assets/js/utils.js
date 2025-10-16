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

/**
 * Get relative time string (e.g., "2h ago")
 * @param {Date|string} date - Date object or ISO string
 * @returns {string}
 */
function getTimeAgo(date) {
    const d = typeof date === 'string' ? new Date(date) : date;
    const now = new Date();
    const diff = now - d;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    const months = Math.floor(days / 30);
    const years = Math.floor(days / 365);
    
    if (years > 0) return `${years}y ago`;
    if (months > 0) return `${months}mo ago`;
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    if (seconds > 10) return `${seconds}s ago`;
    return 'Just now';
}

// ============================================
// THEME MANAGEMENT
// ============================================

/**
 * Initialize theme system
 */
function initTheme() {
    const themeToggle = document.getElementById('theme-switcher');
    if (!themeToggle) return;

    const body = document.body;
    const sunIcon = themeToggle.querySelector('[data-feather="sun"]');
    const moonIcon = themeToggle.querySelector('[data-feather="moon"]');

    const savedTheme = localStorage.getItem('theme') || 
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

    const applyTheme = (theme) => {
        if (theme === 'dark') {
            body.classList.add('dark');
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'inline-block';
        } else {
            body.classList.remove('dark');
            sunIcon.style.display = 'inline-block';
            moonIcon.style.display = 'none';
        }
        // Re-initialize feather icons to ensure they are rendered correctly.
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    };

    applyTheme(savedTheme);

    themeToggle.addEventListener('click', () => {
        const newTheme = body.classList.contains('dark') ? 'light' : 'dark';
        localStorage.setItem('theme', newTheme);

        // Add animation class
        themeToggle.classList.add('theme-changing');

        applyTheme(newTheme);

        // Remove animation class after animation completes
        setTimeout(() => {
            themeToggle.classList.remove('theme-changing');
        }, 500);

        // Trigger theme change event for charts
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
    });
}

// ============================================
// CLIPBOARD UTILITIES
// ============================================

/**
 * Copy text to clipboard with visual feedback
 * @param {string} text - Text to copy
 * @param {HTMLElement} button - Button element to show feedback
 * @returns {Promise<boolean>}
 */
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
        alert('Failed to copy. Please try again.');
        return false;
    }
}

/**
 * Setup copy buttons for elements with data-copy attribute
 */
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

/**
 * Show/hide loading state
 * @param {string} containerId - Container ID
 * @param {boolean} show - Show or hide
 */
function setLoading(containerId, show) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.style.display = show ? 'flex' : 'none';
}

/**
 * Display error message
 * @param {string} containerId - Container ID
 * @param {string} message - Error message
 */
function showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = `
        <div style="text-align: center; padding: var(--space-20);">
            <div style="font-size: 3em; margin-bottom: var(--space-4); color: var(--danger);">⚠️</div>
            <h3 style="font-size: var(--text-2xl); margin-bottom: var(--space-3); color: var(--text-primary);">
                Error Loading Data
            </h3>
            <p style="color: var(--text-secondary); margin-bottom: var(--space-6);">
                ${message}
            </p>
            <button class="btn btn-primary" onclick="location.reload()">
                <i data-feather="refresh-cw"></i>
                <span>Retry</span>
            </button>
        </div>
    `;
    
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

// ============================================
// COUNTRY & FLAG UTILITIES
// ============================================

/**
 * Get country flag emoji from country code
 * @param {string} countryCode - ISO 3166-1 alpha-2 country code
 * @returns {string}
 */
function getCountryFlag(countryCode) {
    if (!countryCode || countryCode === 'XX' || countryCode.length !== 2) {
        return '🌐';
    }
    
    const codePoints = countryCode
        .toUpperCase()
        .split('')
        .map(char => 127397 + char.charCodeAt(0));
    
    return String.fromCodePoint(...codePoints);
}

// ============================================
// EXPORT UTILITIES
// ============================================

/**
 * Export data as JSON file
 * @param {Object|Array} data - Data to export
 * @param {string} filename - Filename (without extension)
 */
function exportJSON(data, filename) {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    downloadBlob(blob, `${filename}.json`);
}

/**
 * Export data as CSV file
 * @param {Array} data - Array of objects
 * @param {string} filename - Filename (without extension)
 * @param {Array} columns - Column names (optional)
 */
function exportCSV(data, filename, columns = null) {
    if (!data || data.length === 0) return;
    
    const cols = columns || Object.keys(data[0]);
    const header = cols.join(',');
    const rows = data.map(row => 
        cols.map(col => {
            let value = row[col];
            if (value === null || value === undefined) value = '';
            if (typeof value === 'object') value = JSON.stringify(value);
            if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
                value = `"${value.replace(/"/g, '""')}"`;
            }
            return value;
        }).join(',')
    );
    
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    downloadBlob(blob, `${filename}.csv`);
}

/**
 * Download blob as file
 * @param {Blob} blob - Blob to download
 * @param {string} filename - Filename
 */
function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================
// VALIDATION UTILITIES
// ============================================

/**
 * Validate proxy data structure
 * @param {Object} proxy - Proxy object
 * @returns {boolean}
 */
function isValidProxy(proxy) {
    return proxy 
        && typeof proxy === 'object'
        && typeof proxy.protocol === 'string'
        && typeof proxy.config === 'string'
        && proxy.location
        && typeof proxy.location === 'object';
}

/**
 * Sanitize HTML to prevent XSS
 * @param {string} html - HTML string
 * @returns {string}
 */
function sanitizeHTML(html) {
    const div = document.createElement('div');
    div.textContent = html;
    return div.innerHTML;
}

// ============================================
// PERFORMANCE UTILITIES
// ============================================

/**
 * Debounce function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function}
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
 * Throttle function calls
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in ms
 * @returns {Function}
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ============================================
// INITIALIZATION
// ============================================

/**
 * Initialize all utilities on DOM ready
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    initTheme();
    
    // Initialize copy buttons
    initCopyButtons();
    
    // Initialize feather icons if available
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
    
    // Log initialization
    console.log('✅ ConfigStream utilities initialized');
});

// ============================================
// GLOBAL ERROR HANDLER
// ============================================

window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});