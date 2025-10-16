document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    initTheme();

    // Initialize copy buttons
    initCopyButtons();

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

        // Fetch previous stats and calculate change
        try {
            const historyResponse = await fetchWithPath('output/statistics-history.json');
            const history = await historyResponse.json();
            if (history && history.length > 1) {
                const previousStats = history[1]; // Index 1 is the one before the latest
                const change = stats.working - previousStats.working;
                const changeElement = document.getElementById('workingConfigsChange');
                if (changeElement) {
                    if (change > 0) {
                        changeElement.textContent = `(+${change})`;
                        changeElement.style.color = 'var(--success-color)';
                    } else if (change < 0) {
                        changeElement.textContent = `(${change})`;
                        changeElement.style.color = 'var(--danger-color)';
                    } else {
                        changeElement.textContent = '(~0)';
                    }
                }
            }
        } catch (error) {
            console.error('Could not load statistics history:', error);
        }
    }

    async function updateClashFileSize() {
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        const formatSize = (n) => {
            const i = n > 0 ? Math.floor(Math.log(n) / Math.log(1024)) : 0;
            return `${(n / Math.pow(1024, i)).toFixed(2)} ${units[i]}`;
        };
        const setNA = () => updateElement('clash-filesize', 'N/A');
        try {
            const url = getFullUrl('output/clash.yaml');
            let response = await fetch(url, { method: 'HEAD' });

            let sizeNum = NaN;
            if (response.ok) {
                const sizeHeader = response.headers.get('Content-Length');
                sizeNum = sizeHeader ? parseInt(sizeHeader, 10) : NaN;
            }

            if (!Number.isFinite(sizeNum) || sizeNum < 0) {
                // Fallback to a ranged GET; some servers may not support HEAD
                response = await fetch(url, { method: 'GET', headers: { Range: 'bytes=0-0' } });
                if (response.status === 206) {
                    const contentRange = response.headers.get('Content-Range'); // e.g., "bytes 0-0/12345"
                    const totalMatch = contentRange && contentRange.match(/\/(\d+)$/);
                    sizeNum = totalMatch ? parseInt(totalMatch[1], 10) : NaN;
                } else if (response.ok) {
                    // Range not honored; as a last resort try Content-Length from full GET
                    const len = response.headers.get('Content-Length');
                    sizeNum = len ? parseInt(len, 10) : NaN;
                } else {
                    setNA();
                    return;
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
    updateStats();
    updateClashFileSize();
    initHeroParallax();
    initCardGlow();
    initTilt();
    initColorSwitcher();
    initRippleEffect();
});

function initHeroParallax() {
    const hero = document.querySelector('.hero');
    if (!hero) return;

    window.addEventListener('scroll', () => {
        const scrollY = window.scrollY;
        hero.style.transform = `translateY(${scrollY * 0.1}px)`;
    });
}

function initCardGlow() {
    const cards = document.querySelectorAll('.card');
    if (!cards.length) return;
    if (typeof window.VanillaTilt === 'undefined' || typeof window.VanillaTilt.init !== 'function') {
        return;
    }
    window.VanillaTilt.init(cards, {
        max: 5,
        speed: 400,
        glare: true,
        "max-glare": 0.1
    });
    VanillaTilt.init(cards, {
        max: 5,
        speed: 400,
        glare: true,
        "max-glare": 0.1,
    });
}

function initColorSwitcher() {
    const swatches = document.querySelectorAll('.color-swatch');
    if (!swatches.length) return;

    const root = document.documentElement;
    const savedPrimary = localStorage.getItem('brand-primary');
    const savedSecondary = localStorage.getItem('brand-secondary');

    if (savedPrimary && savedSecondary) {
        root.style.setProperty('--brand-primary', savedPrimary);
        root.style.setProperty('--brand-secondary', savedSecondary);
    }

    swatches.forEach(swatch => {
        swatch.addEventListener('click', () => {
            const primary = swatch.dataset.colorPrimary;
            const secondary = swatch.dataset.colorSecondary;

            root.style.setProperty('--brand-primary', primary);
            root.style.setProperty('--brand-secondary', secondary);

            localStorage.setItem('brand-primary', primary);
            localStorage.setItem('brand-secondary', secondary);

            swatches.forEach(s => s.classList.remove('active'));
            swatch.classList.add('active');
        });

        // Set active state on load
        if (savedPrimary === swatch.dataset.colorPrimary) {
            swatch.classList.add('active');
        }
    });
}

function initRippleEffect() {
    const buttons = document.querySelectorAll('.btn');

    buttons.forEach(button => {
        button.addEventListener('click', function (e) {
            const rect = this.getBoundingClientRect();
            const xInside = e.clientX - rect.left;
            const yInside = e.clientY - rect.top;

            const circle = document.createElement('span');
            circle.classList.add('ripple');
            circle.style.top = yInside + 'px';
            circle.style.left = xInside + 'px';

            this.appendChild(circle);

            setTimeout(() => circle.remove(), 600);
        });
    });
}