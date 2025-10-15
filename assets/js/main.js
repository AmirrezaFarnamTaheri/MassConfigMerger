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
    if (document.getElementById('proxiesTable')) { // Proxies page
        let allProxies = [];
        let currentSort = { key: 'latency', asc: true };

        const protocolFilter = document.getElementById('filterProtocol');
        const locationFilter = document.getElementById('filterLocation');
        const tableBody = document.getElementById('proxiesTBody');
        const loadingContainer = document.getElementById('loading-container');

        const renderTable = () => {
            // Re-trigger animation by resetting the class
            tableBody.classList.remove('visible');

            const protoFilter = protocolFilter.value.toLowerCase();
            const locFilter = locationFilter.value.toLowerCase();

            const filteredProxies = allProxies.filter(p => {
                const protocol = p.protocol.toLowerCase();
                const location = [p.location?.city, p.location?.country].filter(Boolean).join(', ').toLowerCase();
                return protocol.includes(protoFilter) && location.includes(locFilter);
            });

            // Sort
            filteredProxies.sort((a, b) => {
                let valA, valB;
                if (currentSort.key === 'location') {
                    valA = [a.location?.city, a.location?.country].filter(Boolean).join(', ');
                    valB = [b.location?.city, b.location?.country].filter(Boolean).join(', ');
                } else if (currentSort.key === 'asn') {
                    valA = a.location.asn.name;
                    valB = b.location.asn.name;
                } else {
                    valA = a[currentSort.key];
                    valB = b[currentSort.key];
                }

                if (valA < valB) return currentSort.asc ? -1 : 1;
                if (valA > valB) return currentSort.asc ? 1 : -1;
                return 0;
            });

            const escapeHtml = (s) => String(s)
              .replace(/&/g, '&')
              .replace(/</g, '<')
              .replace(/>/g, '>')
              .replace(/"/g, '"')
              .replace(/'/g, ''');
              .replace(/&/g, '&')
              .replace(/</g, '<')
              .replace(/>/g, '>')
              .replace(/"/g, '"')
              .replace(/'/g, ''');

            const escapeAttr = (s) => String(s)
              .replace(/&/g, '&')
              .replace(/"/g, '"')
              .replace(/</g, '<')
              .replace(/>/g, '>');

            tableBody.innerHTML = filteredProxies.map((p, index) => {
              const cityRaw = p.location?.city ?? '—';
              const countryRaw = p.location?.country ?? '—';
              const asnNameRaw = p.location?.asn?.name ?? '—';
              const latencyRaw = (p.latency ?? '') !== '' ? `${p.latency}ms` : '—';
              const protocolRaw = p.protocol ?? '—';
              const configRaw = p.config ?? '';

              const city = escapeHtml(cityRaw);
              const country = escapeHtml(countryRaw);
              const asnName = escapeHtml(asnNameRaw);
              const latency = escapeHtml(latencyRaw);
              const protocol = escapeHtml(protocolRaw);
              const configAttr = escapeAttr(configRaw);

              return `
                <tr style="animation-delay: ${index * 0.03}s">
                  <td>${protocol}</td>
                  <td>${city}${city !== '—' && country !== '—' ? ', ' : ''}${country}</td>
                  <td>${latency}</td>
                  <td>${asnName}</td>
                  <td><button class="btn btn-secondary copy-btn" data-config="${configAttr}"><i data-feather="copy"></i></button></td>
                </tr>
              `;
            }).join('');
            feather.replace();

            // Add class to trigger animation
            setTimeout(() => tableBody.classList.add('visible'), 50);
        };

        protocolFilter.addEventListener('input', renderTable);
        locationFilter.addEventListener('input', renderTable);

        document.querySelectorAll('#proxiesTable th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                const sortKey = th.dataset.sort;
                if (currentSort.key === sortKey) {
                    currentSort.asc = !currentSort.asc;
                } else {
                    currentSort.key = sortKey;
                    currentSort.asc = true;
                }

                document.querySelectorAll('#proxiesTable th[data-sort]').forEach(header => header.classList.remove('asc', 'desc'));
                th.classList.add(currentSort.asc ? 'asc' : 'desc');

                renderTable();
            });
        });

        async function fetchAndRenderProxies() {
            try {
                const response = await fetchWithCacheBust('output/proxies.json');
                allProxies = await response.json();
                loadingContainer.style.display = 'none';
                renderTable();
            } catch (error) {
                console.error('Error fetching proxies:', error);
                loadingContainer.innerHTML = '<p>Failed to load proxy data.</p>';
            }
        }

        fetchAndRenderProxies();
    }

    if (document.getElementById('charts-card')) { // Statistics page
        async function renderCharts() {
            try {
                const response = await fetchWithCacheBust('output/statistics.json');
                const stats = await response.json();
                const style = getComputedStyle(body);

                const commonOptions = {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: style.getPropertyValue('--text-secondary-dark')
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: style.getPropertyValue('--text-secondary-dark') },
                            grid: { color: style.getPropertyValue('--border-dark') }
                        },
                        y: {
                            ticks: { color: style.getPropertyValue('--text-secondary-dark') },
                            grid: { color: style.getPropertyValue('--border-dark') }
                        }
                    }
                };

                // Protocol Chart
                new Chart(document.getElementById('protoChart'), {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(stats.protocols),
                        datasets: [{
                            data: Object.values(stats.protocols),
                            backgroundColor: [
                                'rgba(23, 162, 184, 0.7)',
                                'rgba(102, 16, 242, 0.7)',
                                'rgba(0, 123, 255, 0.7)',
                                'rgba(0, 198, 255, 0.7)',
                                'rgba(245, 54, 92, 0.7)'
                            ],
                            borderColor: style.getPropertyValue('--bg-dark'),
                        }]
                    },
                    options: { ...commonOptions, plugins: { legend: { ...commonOptions.plugins.legend, display: true, position: 'bottom' } } }
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
                            backgroundColor: 'rgba(23, 162, 184, 0.6)',
                            borderColor: 'rgba(23, 162, 184, 1)',
                            borderWidth: 1
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