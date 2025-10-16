document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    initTheme();

    // Initialize mobile navigation
    initMobileNav();

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
    const moonIcon = document.querySelector('.moon-icon');
    const sunIcon = document.querySelector('.sun-icon');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    let currentTheme = localStorage.getItem('theme');

    const setTheme = (theme) => {
        console.log(`Setting theme to: ${theme}`);
        document.body.classList.toggle('dark', theme === 'dark');
        console.log(`Body class list after toggle: ${document.body.classList}`);
        moonIcon.classList.toggle('hidden', theme === 'dark');
        sunIcon.classList.toggle('hidden', theme !== 'dark');
        localStorage.setItem('theme', theme);
    };

    if (!currentTheme) {
        currentTheme = prefersDark.matches ? 'dark' : 'light';
    }

    setTheme(currentTheme);

    themeSwitcher.addEventListener('click', () => {
        console.log('Theme switcher clicked');
        const newTheme = document.body.classList.contains('dark') ? 'light' : 'dark';
        setTheme(newTheme);
    });

    prefersDark.addEventListener('change', (e) => {
        setTheme(e.matches ? 'dark' : 'light');
    });
}

function initMobileNav() {
    const toggleBtn = document.getElementById('mobile-nav-toggle');
    const nav = document.getElementById('main-nav');
    const overlay = document.querySelector('.nav-overlay');

    if (!toggleBtn || !nav || !overlay) return;

    toggleBtn.addEventListener('click', () => {
        const isActive = nav.classList.toggle('active');
        toggleBtn.setAttribute('aria-expanded', isActive);
        overlay.classList.toggle('active', isActive);
        document.body.style.overflow = isActive ? 'hidden' : '';

        toggleBtn.querySelector('.menu-icon').classList.toggle('hidden', isActive);
        toggleBtn.querySelector('.x-icon').classList.toggle('hidden', !isActive);
    });

    overlay.addEventListener('click', () => {
        nav.classList.remove('active');
        toggleBtn.setAttribute('aria-expanded', 'false');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
        toggleBtn.querySelector('.menu-icon').classList.remove('hidden');
        toggleBtn.querySelector('.x-icon').classList.add('hidden');
    });
}