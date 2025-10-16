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
    }

    // --- INITIALIZE ---
    updateStats();
    initHeroParallax();
});

function initHeroParallax() {
    const hero = document.querySelector('.hero');
    if (!hero) return;

    window.addEventListener('scroll', () => {
        const scrollY = window.scrollY;
        hero.style.transform = `translateY(${scrollY * 0.1}px)`;
    });
}