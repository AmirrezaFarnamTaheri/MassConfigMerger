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

    // --- INITIALIZE ---
    updateStats();
    initHeroParallax();
    initCardGlow();
    initTilt();
    initColorSwitcher();
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
    cards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--x', `${x}px`);
            card.style.setProperty('--y', `${y}px`);
        });
    });
}

function initTilt() {
    const cards = document.querySelectorAll('.card');
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