document.addEventListener('DOMContentLoaded', () => {
    // --- THEME SWITCHER ---
    const themeSwitcher = document.getElementById('theme-switcher');
    const body = document.body;
    const logo = document.getElementById('logo');
    const moonIcon = document.querySelector('.theme-icon-moon');
    const sunIcon = document.querySelector('.theme-icon-sun');

    const setTheme = (theme) => {
        if (theme === 'dark') {
            body.classList.add('dark');
            logo.classList.add('dark');
            if (moonIcon) moonIcon.style.display = 'none';
            if (sunIcon) sunIcon.style.display = 'block';
        } else {
            body.classList.remove('dark');
            logo.classList.remove('dark');
            if (moonIcon) moonIcon.style.display = 'block';
            if (sunIcon) sunIcon.style.display = 'none';
        }
        localStorage.setItem('theme', theme);
    };

    themeSwitcher.addEventListener('click', () => {
        const currentTheme = localStorage.getItem('theme') || 'light';
        setTheme(currentTheme === 'dark' ? 'light' : 'dark');
    });

    // Apply theme on initial load
    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    setTheme(savedTheme);

    // --- FEATHER ICONS ---
    feather.replace();

    // --- CARD GLOW EFFECT ---
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });

    // --- DATA FETCHING ---
    const fetchWithCacheBust = (url) => fetch(`${url}?_=${new Date().getTime()}`);

    const updateElementText = (id, value, loadingClass = 'loading') => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = value;
            el.classList.remove(loadingClass);
        }
    };

    async function fetchMetadata() {
        try {
            const response = await fetchWithCacheBust('output/metadata.json');
            const metadata = await response.json();
            const date = new Date(metadata.generated_at);
            const formatted = date.toLocaleString('en-US', {
                year: 'numeric', month: 'long', day: 'numeric',
                hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
            });
            updateElementText('footerUpdate', formatted);
        } catch (error) {
            console.error('Error fetching metadata:', error);
            updateElementText('footerUpdate', 'Recently');
        }
    }

    async function fetchStatistics() {
        const statsEl = document.getElementById('stats-card');
        if (!statsEl) return;
        try {
            const response = await fetchWithCacheBust('output/statistics.json');
            const stats = await response.json();
            updateElementText('totalConfigs', stats.total_tested || 0);
            updateElementText('workingConfigs', stats.working || 0);
        } catch (error) {
            console.error('Error fetching statistics:', error);
            document.querySelectorAll('.stat-number.loading').forEach(el => el.classList.remove('loading'));
        }
    }

    // --- PAGE-SPECIFIC LOGIC ---
    if (document.getElementById('proxiesTBody')) { // Proxies page
        async function fetchProxies() {
            try {
                const response = await fetchWithCacheBust('output/proxies.json');
                const proxies = await response.json();
                const tbody = document.getElementById('proxiesTBody');
                const loadingEl = document.getElementById('loading-proxies');

                if (!proxies.length) {
                    loadingEl.textContent = "No working proxies found in the last run.";
                    return;
                }

                tbody.innerHTML = ''; // Clear loading state
                proxies.forEach(p => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${p.protocol}</td>
                        <td>${p.location.city}, ${p.location.country}</td>
                        <td>${p.latency}ms</td>
                        <td>${p.location.asn.name}</td>
                        <td><button class="btn btn-secondary copy-btn" data-config="${p.config}">Copy</button></td>
                    `;
                    tbody.appendChild(tr);
                });
                loadingEl.style.display = 'none';
                feather.replace();
            } catch (error) {
                console.error('Error fetching proxies:', error);
                 document.getElementById('loading-proxies').textContent = 'Failed to load proxy data.';
            }
        }
        fetchProxies();
    }

    if (document.getElementById('charts-card')) { // Statistics page
        async function renderCharts() {
            try {
                const response = await fetchWithCacheBust('output/statistics.json');
                const stats = await response.json();

                const commonOptions = {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: getComputedStyle(body).getPropertyValue('--text-secondary-light') } },
                        y: { ticks: { color: getComputedStyle(body).getPropertyValue('--text-secondary-light') } }
                    }
                };

                // Protocol Chart
                new Chart(document.getElementById('protoChart'), {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(stats.protocols),
                        datasets: [{
                            data: Object.values(stats.protocols),
                            backgroundColor: ['#825ee4', '#5e72e4', '#2dce89', '#fb6340', '#f5365c'],
                        }]
                    },
                    options: { ...commonOptions, plugins: { legend: { display: true, position: 'bottom' } } }
                });

                // Country Chart
                const topCountries = Object.entries(stats.countries).sort((a, b) => b[1] - a[1]).slice(0, 10);
                new Chart(document.getElementById('countryChart'), {
                    type: 'bar',
                    data: {
                        labels: topCountries.map(c => c[0]),
                        datasets: [{
                            label: 'Proxy Count',
                            data: topCountries.map(c => c[1]),
                            backgroundColor: '#5e72e4',
                        }]
                    },
                    options: commonOptions
                });

            } catch (error) {
                console.error('Error rendering charts:', error);
            }
        }
        renderCharts();
    }

    function setupCopyButtons() {
        document.body.addEventListener('click', async (e) => {
            if (e.target.matches('.copy-btn') || e.target.closest('.copy-btn')) {
                const button = e.target.closest('.copy-btn');
                let contentToCopy;

                if(button.dataset.file) {
                    const file = button.dataset.file;
                    contentToCopy = `${window.location.origin}${window.location.pathname.replace(/\/$/, '')}/${file}`;
                } else if (button.dataset.config) {
                    contentToCopy = button.dataset.config;
                }

                if (!contentToCopy) return;

                try {
                    await navigator.clipboard.writeText(contentToCopy);
                    const originalHTML = button.innerHTML;
                    button.innerHTML = '<i data-feather="check"></i>Copied!';
                    button.disabled = true;
                    feather.replace();

                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.disabled = false;
                        feather.replace();
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy:', err);
                    alert('Failed to copy. Please try again.');
                }
            }
        });
    }

    // --- INITIALIZE ---
    fetchMetadata();
    fetchStatistics();
    setupCopyButtons();
});