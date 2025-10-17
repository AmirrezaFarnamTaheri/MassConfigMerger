// Page-specific logic for the proxies page
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('proxiesTable')) return;

    let allProxies = [];
    let currentSort = { key: 'latency', asc: true };

    const protocolFilter = document.getElementById('filterProtocol');
    const locationFilter = document.getElementById('filterLocation');
    const tableBody = document.getElementById('proxiesTableBody');
    const emptyState = document.getElementById('emptyState');
    const proxiesTable = document.getElementById('proxiesTable');

    const renderTable = () => {
        const protoFilter = protocolFilter.value.toLowerCase();
        const locFilter = locationFilter.value.toLowerCase();

        const filteredProxies = allProxies.filter(p => {
            const protocol = p.protocol.toLowerCase();
            const location = p.country_code ? p.country_code.toLowerCase() : '';
            return protocol.includes(protoFilter) && location.includes(locFilter);
        });

        if (filteredProxies.length === 0) {
            proxiesTable.classList.add('hidden');
            emptyState.classList.remove('hidden');
        } else {
            proxiesTable.classList.remove('hidden');
            emptyState.classList.add('hidden');
        }

        // Sort
        filteredProxies.sort((a, b) => {
            let valA, valB;
            if (currentSort.key === 'location') {
                valA = a.country_code || '';
                valB = b.country_code || '';
            } else {
                valA = a[currentSort.key];
                valB = b[currentSort.key];
            }

            if (valA < valB) return currentSort.asc ? -1 : 1;
            if (valA > valB) return currentSort.asc ? 1 : -1;
            return 0;
        });

        tableBody.innerHTML = filteredProxies.map((p, index) => {
            const country = p.country_code || 'Unknown';
            const latency = p.latency ? `${p.latency}ms` : 'N/A';
            const protocol = p.protocol || 'N/A';
            const config = p.config || '';
            return `
                <tr style="--delay: ${index * 0.03}s">
                    <td>${protocol}</td>
                    <td>${country}</td>
                    <td>${latency}</td>
                    <td><button class="btn btn-secondary copy-btn" data-config="${encodeURIComponent(config)}"><i data-feather="copy"></i></button></td>
                </tr>
            `;
        }).join('');
        feather.replace();
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

            document.querySelectorAll('#proxiesTable th[data-sort]').forEach(header => {
                if (header !== th) {
                    header.removeAttribute('aria-sort');
                }
            });
            th.setAttribute('aria-sort', currentSort.asc ? 'ascending' : 'descending');

            renderTable();
        });
    });

    async function fetchAndRenderProxies() {
        const loadingContainer = document.getElementById('loadingContainer');
        const proxiesTable = document.getElementById('proxiesTable');

        loadingContainer.classList.remove('hidden');
        proxiesTable.classList.add('hidden');

        try {
            allProxies = await fetchProxies();
            renderTable();
        } catch (error) {
            window.stateManager.setError('Failed to load proxies.', error);
        } finally {
            loadingContainer.classList.add('hidden');
        }
    }


    fetchAndRenderProxies();
});