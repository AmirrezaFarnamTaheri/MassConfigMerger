function initPreloader() {
    const preloader = document.getElementById('preloader');
    const logo = document.querySelector('.logo-svg');
    if (!preloader) return;

    window.addEventListener('load', () => {
        setTimeout(() => {
            preloader.classList.add('hidden');
            document.body.classList.add('loaded');
            if (logo) {
                logo.classList.add('loading-animation');
            }
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
        if (!window.stateManager) {
            console.error("StateManager not found!");
            return;
        }
        window.stateManager.setLoading(true, 'Fetching latest data...');
        try {
            // Fetch metadata and statistics in parallel
            const [metadata, stats] = await Promise.all([
                fetchMetadata(),
                fetchStatistics()
            ]);

            // Store protocol colors globally
            if (metadata && metadata.protocol_colors) {
                window.PROTOCOL_COLORS = metadata.protocol_colors;
            }

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
            window.stateManager.setError('Failed to initialize page data.', error);
            // Update UI to show that data loading failed
            updateElement('footerUpdate', 'N/A');
            updateElement('totalConfigs', 'N/A');
            updateElement('workingConfigs', 'N/A');
        } finally {
            window.stateManager.setLoading(false);
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