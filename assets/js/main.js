document.addEventListener('DOMContentLoaded', () => {
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

    // --- HTML INCLUDES ---
    const loadIncludes = async () => {
        const headerPlaceholder = document.getElementById('header-placeholder');
        if (headerPlaceholder) {
            const response = await fetch('_includes/header.html');
            const data = await response.text();
            headerPlaceholder.innerHTML = data;
        }

        const footerPlaceholder = document.getElementById('footer-placeholder');
        if (footerPlaceholder) {
            const response = await fetch('_includes/footer.html');
            const data = await response.text();
            footerPlaceholder.innerHTML = data;
        }

        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    };


    // --- INITIALIZE ---
    const init = async () => {
        await loadIncludes();
        // Re-initialize theme after header is loaded
        initTheme();
        initCopyButtons();
        updateStats();
    };

    init();
});