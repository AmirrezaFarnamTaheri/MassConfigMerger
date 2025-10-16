// Page-specific logic for the statistics page
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('charts-card')) return;

    async function renderCharts() {
        try {
            const stats = await fetchStatistics();
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
            new Chart(document.getElementById('protoChart'), {
                type: 'doughnut',
                data: {
                    labels: Object.keys(stats.protocols),
                    datasets: [{
                        data: Object.values(stats.protocols),
                        backgroundColor: [
                            style.getPropertyValue('--glow-light'),
                            style.getPropertyValue('--glow-dark'),
                            '#00c6ff',
                            '#6610f2',
                            '#fd7e14'
                        ],
                        borderColor: document.body.classList.contains('dark') ? style.getPropertyValue('--bg-dark') : style.getPropertyValue('--bg-light'),
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
});