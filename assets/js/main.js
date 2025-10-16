function initPreloader() {
    const preloader = document.getElementById('preloader');
    if (!preloader) return;

    window.addEventListener('load', () => {
        setTimeout(() => {
            preloader.classList.add('hidden');
        }, 200); // Small delay to ensure content is rendered
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // Initialize preloader
    initPreloader();

    // Initialize theme
    initTheme();

    // Initialize copy buttons
    initCopyButtons();

    // Initialize feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }


    // --- DATA FETCHING ---
    async function updateStats() {
        const metadata = await fetchMetadata();
        const stats = await fetchStatistics();

        const date = new Date(metadata.generated_at);
        const formatted = formatDate(date);
        updateElement('footerUpdate', formatted, { removeStyles: true });

        if (document.getElementById('totalConfigs')) {
            updateElement('totalConfigs', stats.total_tested || 0, { removeStyles: true });
        }
        if (document.getElementById('workingConfigs')) {
            updateElement('workingConfigs', stats.working || 0, { removeStyles: true });
        }
    }

    async function updateClashFileSize() {
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        const formatSize = (n) => {
            if (!Number.isFinite(n) || n < 0) return 'N/A';
            const i = n > 0 ? Math.min(units.length - 1, Math.floor(Math.log(n) / Math.log(1024))) : 0;
            return `${(n / Math.pow(1024, i)).toFixed(2)} ${units[i]}`;
        };
        const setNA = () => updateElement('clash-filesize', 'N/A');
        try {
            const url = getFullUrl('output/clash.yaml');
            const sameOrigin = new URL(url, window.location.href).origin === window.location.origin;

            // Try HEAD first (avoid CORS failures by allowing opaque, then guard)
            let response = await fetch(url, { method: 'HEAD', mode: sameOrigin ? 'cors' : 'no-cors' });
            let sizeNum = NaN;

            if (response && response.ok && response.type !== 'opaque') {
                const sizeHeader = response.headers.get('Content-Length');
                sizeNum = sizeHeader ? parseInt(sizeHeader, 10) : NaN;
            }

            // If HEAD didn't provide a size, try a safe ranged GET only if same-origin
            if ((!Number.isFinite(sizeNum) || sizeNum < 0) && sameOrigin) {
                response = await fetch(url, { method: 'GET', headers: { Range: 'bytes=0-0' } });
                if (response.status === 206) {
                    const contentRange = response.headers.get('Content-Range'); // "bytes 0-0/12345"
                    const totalMatch = contentRange && contentRange.match(/\/(\d+)$/);
                    sizeNum = totalMatch ? parseInt(totalMatch[1], 10) : NaN;
                }
            }

            if (Number.isFinite(sizeNum) && sizeNum >= 0) {
                updateElement('clash-filesize', formatSize(sizeNum));
            } else {
                setNA();
            }
        } catch (error) {
            console.error('Could not fetch Clash file size:', error);
            setNA();
        }
    }

    // --- INITIALIZE ---
    if(document.getElementById('totalConfigs')) {
        updateStats();
    }
    if(document.getElementById('clash-filesize')) {
        updateClashFileSize();
    }
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