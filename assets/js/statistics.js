// Page-specific logic for the statistics page
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('charts-card')) return;

    const chartsContainer = document.getElementById('chartsContainer');
    const chartsEmptyState = document.getElementById('chartsEmptyState');

    async function renderCharts() {
        try {
            const stats = await fetchStatistics();

            if (!stats || !stats.protocols || Object.keys(stats.protocols).length === 0) {
                chartsContainer.classList.add('hidden');
                chartsEmptyState.classList.remove('hidden');
                return;
            }

            chartsContainer.classList.remove('hidden');
            chartsEmptyState.classList.add('hidden');

            const style = getComputedStyle(document.body);

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
            const protocolChartCanvas = document.getElementById('protocolChart');
            const protocolChartEmpty = document.getElementById('protocolChartEmpty');
            if (stats.protocols && Object.keys(stats.protocols).length > 0) {
                // Calculate fastest protocol
                const proxies = await fetchProxies();
                const protocolLatencies = {};
                proxies.forEach(p => {
                    if (p.latency) {
                        if (!protocolLatencies[p.protocol]) {
                            protocolLatencies[p.protocol] = [];
                        }
                        protocolLatencies[p.protocol].push(p.latency);
                    }
                });

                const avgLatencies = Object.entries(protocolLatencies).map(([protocol, latencies]) => {
                    const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;
                    return { protocol, avg };
                });

                if (avgLatencies.length > 0) {
                    const fastest = avgLatencies.reduce((prev, current) => (prev.avg < current.avg) ? prev : current);
                    const badge = document.getElementById('fastest-protocol-badge');
                    badge.textContent = `Fastest: ${fastest.protocol}`;
                    badge.classList.remove('hidden');
                }

                new Chart(protocolChartCanvas, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(stats.protocols),
                        datasets: [{
                            data: Object.values(stats.protocols),
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.7)',
                                'rgba(54, 162, 235, 0.7)',
                                'rgba(255, 206, 86, 0.7)',
                                'rgba(75, 192, 192, 0.7)',
                                'rgba(153, 102, 255, 0.7)',
                                'rgba(255, 159, 64, 0.7)'
                            ],
                            borderColor: style.getPropertyValue('--bg-secondary-dark'),
                        }]
                    },
                    options: { ...commonOptions, plugins: { legend: { ...commonOptions.plugins.legend, display: true, position: 'bottom' } } }
                });
                protocolChartCanvas.classList.remove('hidden');
                protocolChartEmpty.classList.add('hidden');
            } else {
                protocolChartCanvas.classList.add('hidden');
                protocolChartEmpty.classList.remove('hidden');
            }

            // Country Chart
            const countryChartCanvas = document.getElementById('countryChart');
            const countryChartEmpty = document.getElementById('countryChartEmpty');
            const topCountries = Object.entries(stats.countries || {}).sort((a, b) => b[1] - a[1]).slice(0, 10);
            if (topCountries.length > 0) {
                new Chart(countryChartCanvas, {
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
                countryChartCanvas.classList.remove('hidden');
                countryChartEmpty.classList.add('hidden');
            } else {
                countryChartCanvas.classList.add('hidden');
                countryChartEmpty.classList.remove('hidden');
            }

        } catch (error) {
            console.error('Error rendering charts:', error);
        }
    }
    renderCharts();
});