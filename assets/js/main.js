function initPreloader() {
    const preloader = document.getElementById('preloader');
    if (!preloader) return;

    window.addEventListener('load', () => {
        setTimeout(() => {
            preloader.classList.add('hidden');
            document.body.classList.add('loaded');
        }, 200); // Small delay to ensure content is rendered
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // Initialize preloader
    initPreloader();

    // Initialize theme
    initTheme();

    // Initialize header scroll effect
    initHeaderScroll();

    // Initialize copy buttons
    initCopyButtons();

    // Initialize feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }


    // --- DATA FETCHING & INITIALIZATION ---
    (async () => {
        try {
            // Fetch metadata and statistics in parallel
            const [metadata, stats] = await Promise.all([
                fetchMetadata(),
                fetchStatistics()
            ]);

            // Update footer timestamp
            if (metadata && metadata.generated_at) {
                const date = new Date(metadata.generated_at);
                const formatted = formatTimestamp(date);
                updateElement('footerUpdate', formatted);
            }

            // Update stats card
            if (stats) {
                if (document.getElementById('totalConfigs')) {
                    updateElement('totalConfigs', stats.total_tested || 0);
                }
                if (document.getElementById('workingConfigs')) {
                    updateElement('workingConfigs', stats.working || 0);
                }
            }
        } catch (error) {
            console.error("Failed to initialize page with data:", error);
            // Update UI to show that data loading failed
            updateElement('footerUpdate', 'N/A');
            updateElement('totalConfigs', 'N/A');
            updateElement('workingConfigs', 'N/A');
        }
    })();
});

function initTheme() {
    const themeSwitcher = document.getElementById('theme-switcher');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    let currentTheme = localStorage.getItem('theme');

    const setTheme = (theme, animate = false) => {
        if (animate) {
            document.body.style.transition = 'background-color var(--transition-base), color var(--transition-base)';
        } else {
            document.body.style.transition = 'none';
        }
        document.body.classList.toggle('dark', theme === 'dark');
        localStorage.setItem('theme', theme);

        // Dispatch a custom event to notify other components (like charts)
        window.dispatchEvent(new CustomEvent('themechanged', { detail: { theme } }));

        if (!animate) {
            // Force a reflow to apply the initial state without transition
            void document.body.offsetWidth;
            document.body.style.transition = '';
        }
    };

    if (!currentTheme) {
        currentTheme = prefersDark.matches ? 'dark' : 'light';
    }

    setTheme(currentTheme);

    themeSwitcher.addEventListener('click', () => {
        const newTheme = document.body.classList.contains('dark') ? 'light' : 'dark';
        setTheme(newTheme, true);
    });

    prefersDark.addEventListener('change', (e) => {
        setTheme(e.matches ? 'dark' : 'light', true);
    });
}

/**
 * Global error handler with user-friendly messages
 */

class ErrorBoundary {
  static init() {
    // Handle uncaught errors
    window.addEventListener('error', (event) => {
      console.error('Global error caught:', event.error);
      this.showErrorNotification(
        'An error occurred',
        'Please refresh the page or contact support'
      );
    });

    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason);
      this.showErrorNotification(
        'A request failed',
        'Please refresh and try again'
      );
      event.preventDefault();
    });
  }

  static showErrorNotification(title, message) {
    const notification = document.createElement('div');
    notification.className = 'error-notification';
    notification.innerHTML = `
      <div class="error-content">
        <h3>${title}</h3>
        <p>${message}</p>
        <button onclick="this.parentElement.parentElement.remove()">Dismiss</button>
      </div>
    `;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 8000);
  }

  static async safeAsyncOperation(operation, fallback = null) {
    try {
      return await operation();
    } catch (error) {
      console.error('Operation failed:', error);
      return fallback;
    }
  }
}

// Initialize on page load
ErrorBoundary.init();

function initHeaderScroll() {
    const header = document.querySelector('.header');
    if (!header) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });
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