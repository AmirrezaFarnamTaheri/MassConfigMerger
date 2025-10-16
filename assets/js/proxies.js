// Page-specific logic for the proxies page
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('proxiesTable')) return;

    let allProxies = [];
    let currentSort = { key: 'latency', asc: true };

    const protocolFilter = document.getElementById('filterProtocol');
    const locationFilter = document.getElementById('filterLocation');
    const tableBody = document.getElementById('proxiesTableBody');
    const loadingContainer = document.getElementById('loadingContainer');
    const emptyState = document.getElementById('emptyState');
    const proxiesTable = document.getElementById('proxiesTable');

    const renderTable = () => {
        const protoFilter = protocolFilter.value.toLowerCase();
        const locFilter = locationFilter.value.toLowerCase();

        const filteredProxies = allProxies.filter(p => {
            const protocol = p.protocol.toLowerCase();
            const location = [p.location?.city, p.location?.country].filter(Boolean).join(', ').toLowerCase();
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
                valA = [a.location?.city, a.location?.country].filter(Boolean).join(', ');
                valB = [b.location?.city, b.location?.country].filter(Boolean).join(', ');
            } else {
                valA = a[currentSort.key];
                valB = b[currentSort.key];
            }

            if (valA < valB) return currentSort.asc ? -1 : 1;
            if (valA > valB) return currentSort.asc ? 1 : -1;
            return 0;
        });

        tableBody.innerHTML = filteredProxies.map((p, index) => {
            const city = p.location?.city || '—';
            const country = p.location?.country || '—';
            const latency = (p.latency ?? '') !== '' ? `${p.latency}ms` : '—';
            const protocol = p.protocol || '—';
            const config = p.config || '';
            return `
                <tr style="--delay: ${index * 0.03}s">
                    <td>${protocol}</td>
                    <td>${city}${city !== '—' && country !== '—' ? ', ' : ''}${country}</td>
                    <td>${latency}</td>
                    <td><button class="btn btn-secondary copy-btn" data-config="${config}"><i data-feather="copy"></i></button></td>
                </tr>
            `;
        }).join('');
        feather.replace();
        initCopyButtons(); // Re-initialize copy buttons for the new rows
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
        try {
            allProxies = await fetchProxies();
            loadingContainer.style.display = 'none';
            renderTable();
        } catch (error) {
            console.error('Error fetching proxies:', error);
            loadingContainer.innerHTML = '<p>Failed to load proxy data.</p>';
        }
    }

    fetchAndRenderProxies();
});