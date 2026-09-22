document.addEventListener('DOMContentLoaded', async () => {
    const searchBar       = document.getElementById('search-bar');
    const searchBtn       = document.getElementById('search-btn');
    const autocompleteBox = document.getElementById('autocomplete-box');
    const resultsGrid     = document.getElementById('results-grid');
    const resultsTitle    = document.getElementById('results-title');
    const resultsCount    = document.getElementById('results-count');
    const loading         = document.getElementById('loading');
    const chips           = document.querySelectorAll('.chip');

    // Price range elements
    const rangeMin     = document.getElementById('range-min');
    const rangeMax     = document.getElementById('range-max');
    const priceDisplay = document.getElementById('price-display');
    const sliderTrack  = document.getElementById('slider-track');
    const priceToggle  = document.getElementById('price-filter-toggle');

    // DSA panel elements
    const dsaPanel      = document.getElementById('dsa-panel');
    const dsaClose      = document.getElementById('dsa-close');
    const dsaQuery      = document.getElementById('dsa-query');
    const dsaStructures = document.getElementById('dsa-structures');
    const dsaTime       = document.getElementById('dsa-time');
    const dsaCount      = document.getElementById('dsa-count');
    const dsaHitRate    = document.getElementById('dsa-hit-rate');
    const dsaHits       = document.getElementById('dsa-hits');
    const dsaMisses     = document.getElementById('dsa-misses');
    const dsaCacheFill  = document.getElementById('dsa-cache-fill');

    let debounceTimer;
    let activeCategory = 'All';
    let lastQuery      = '';
    let priceMin       = 0;
    let priceMax       = 150000;
    let globalMin      = 0;
    let globalMax      = 150000;

    // ── Fetch price range from server ──────────────────────────────
    try {
        const res  = await fetch('/api/price_range', { cache: 'no-store' });
        const data = await res.json();
        globalMin = data.min;
        globalMax = data.max;
        priceMin  = globalMin;
        priceMax  = globalMax;
        rangeMin.min = globalMin; rangeMin.max = globalMax; rangeMin.value = globalMin;
        rangeMax.min = globalMin; rangeMax.max = globalMax; rangeMax.value = globalMax;
        updatePriceUI();
    } catch (e) { console.warn('Could not load price range:', e); }

    // ── Dual Range Slider ──────────────────────────────────────────
    function updatePriceUI() {
        const minPct = ((priceMin - globalMin) / (globalMax - globalMin)) * 100;
        const maxPct = ((priceMax - globalMin) / (globalMax - globalMin)) * 100;

        // Draw fill segment between thumbs
        sliderTrack.innerHTML = `<div class="fill" style="left:${minPct}%;right:${100-maxPct}%"></div>`;

        priceDisplay.textContent = `₹${priceMin.toLocaleString('en-IN')} — ₹${priceMax.toLocaleString('en-IN')}`;
    }

    rangeMin.addEventListener('input', () => {
        priceMin = Math.min(parseInt(rangeMin.value), priceMax - 100);
        rangeMin.value = priceMin;
        updatePriceUI();
        if (priceToggle.checked) debouncedSearch();
    });

    rangeMax.addEventListener('input', () => {
        priceMax = Math.max(parseInt(rangeMax.value), priceMin + 100);
        rangeMax.value = priceMax;
        updatePriceUI();
        if (priceToggle.checked) debouncedSearch();
    });

    priceToggle.addEventListener('change', () => {
        performSearch(lastQuery);
    });

    function debouncedSearch() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => performSearch(lastQuery), 400);
    }

    // ── DSA Panel close button ──────────────────────────────────────
    dsaClose.addEventListener('click', () => { dsaPanel.style.display = 'none'; });

    // ── Category chips ──────────────────────────────────────────────
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            chips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            activeCategory = chip.dataset.category;
            performSearch(lastQuery);
        });
    });

    // ── Autocomplete (Python Trie index) ────────────────────────────
    searchBar.addEventListener('input', e => {
        const q = e.target.value.trim();
        clearTimeout(debounceTimer);
        if (q.length < 2) { autocompleteBox.classList.add('hidden'); return; }
        debounceTimer = setTimeout(async () => {
            try {
                const res  = await fetch(`/api/autocomplete?q=${encodeURIComponent(q)}`, { cache: 'no-store' });
                const data = await res.json();
                renderAutocomplete(data);
            } catch (err) { console.error('Autocomplete error:', err); }
        }, 150);
    });

    function renderAutocomplete(products) {
        autocompleteBox.innerHTML = '';
        if (!products.length) { autocompleteBox.classList.add('hidden'); return; }
        products.forEach(p => {
            const div = document.createElement('div');
            div.className = 'dropdown-item';
            div.innerHTML = `<span>${p.name}</span><span class="di-price">₹${p.price.toLocaleString('en-IN')}</span>`;
            div.addEventListener('click', () => {
                searchBar.value = p.name;
                autocompleteBox.classList.add('hidden');
                performSearch(p.name);
            });
            autocompleteBox.appendChild(div);
        });
        autocompleteBox.classList.remove('hidden');
    }

    document.addEventListener('click', e => {
        if (!e.target.closest('.search-container')) autocompleteBox.classList.add('hidden');
    });

    // ── Search triggers ─────────────────────────────────────────────
    searchBtn.addEventListener('click', () => { const q = searchBar.value.trim(); if (q) performSearch(q); });
    searchBar.addEventListener('keypress', e => {
        if (e.key === 'Enter') { const q = searchBar.value.trim(); performSearch(q); }
    });

    // ── Core search function ─────────────────────────────────────────
    async function performSearch(query) {
        autocompleteBox.classList.add('hidden');
        lastQuery = query;
        resultsGrid.innerHTML = '';
        loading.classList.remove('hidden');
        resultsCount.textContent = '';

        const label = query
            ? `Results for "${query}"${activeCategory !== 'All' ? ` · ${activeCategory}` : ''}`
            : (activeCategory !== 'All' ? activeCategory : 'Top Products');
        resultsTitle.textContent = label;

        try {
            let res, data;
            if (!query && !priceToggle.checked) {
                // Featured endpoint — no search needed, no price filter applied
                const catParam = activeCategory !== 'All' ? `?category=${encodeURIComponent(activeCategory)}` : '';
                res  = await fetch(`/api/featured${catParam}`, { cache: 'no-store' });
                data = await res.json();
            } else {
                // Search endpoint (handles empty query if price filter is on)
                let url = `/api/search?q=${encodeURIComponent(query)}`;
                if (activeCategory !== 'All') url += `&category=${encodeURIComponent(activeCategory)}`;
                if (priceToggle.checked) url += `&min_price=${priceMin}&max_price=${priceMax}`;
                res  = await fetch(url, { cache: 'no-store' });
                data = await res.json();
            }

            loading.classList.add('hidden');
            let products = data.products || data;

            // ── Smart fallback ──────────────────────────────────────────────
            // The engine returns global Top-10; category post-filter can yield 0.
            // When that happens, show featured products for the selected category.
            if (products.length === 0 && query && activeCategory !== 'All') {
                const fbRes  = await fetch(`/api/featured?category=${encodeURIComponent(activeCategory)}`, { cache: 'no-store' });
                const fbData = await fbRes.json();
                products = fbData.products || fbData;
                resultsTitle.textContent = `Top ${activeCategory} Products`;
                resultsCount.textContent = `No "${query}" results in ${activeCategory}`;
                renderResults(products);
                if (data.meta) updateDsaPanel(data.meta, query);
                return;
            }

            renderResults(products);
            if (data.meta) updateDsaPanel(data.meta, query);
        } catch (err) {
            loading.classList.add('hidden');
            console.error('Search error:', err);
        }
    }

    // ── Render product cards ─────────────────────────────────────────
    const BADGE_CLASS = {
        'Electronics':           'badge-Electronics',
        'Footwear':              'badge-Footwear',
        'Clothing':              'badge-Clothing',
        'Books':                 'badge-Books',
        'Home & Kitchen':        'badge-Home--Kitchen',
        'Sports & Fitness':      'badge-Sports--Fitness',
        'Beauty & Personal Care':'badge-Beauty--Personal-Care',
    };

    function renderResults(products) {
        if (!products.length) {
            resultsGrid.innerHTML = `<div class="empty-state">
                <i class="fa-solid fa-magnifying-glass"></i>
                <p>No products found. Try a different query or adjust the price range.</p>
            </div>`;
            resultsCount.textContent = '';
            return;
        }
        resultsCount.textContent = `${products.length} product${products.length !== 1 ? 's' : ''}`;
        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'card';
            const bc = BADGE_CLASS[p.category] || 'badge-Electronics';
            const score = p.score ?? 0;
            const scoreColor = score >= 7 ? '#16a34a' : score >= 4.5 ? '#d97706' : '#dc2626';
            const scoreDot   = score >= 7 ? '🟢' : score >= 4.5 ? '🟡' : '🔴';
            const formulaTip = `Score = 0.50 × relevance + 0.30 × rating + 0.20 × popularity\n(each term normalized 0–1, scaled to /10)`;
            card.innerHTML = `
                <span class="category-badge ${bc}">${p.category || 'General'}</span>
                <div class="card-title">${p.name}</div>
                <div class="card-price">₹${p.price.toLocaleString('en-IN')}</div>
                <div class="card-stats">
                    <span class="rating"><i class="fa-solid fa-star"></i> ${p.rating}</span>
                    <span><i class="fa-solid fa-fire" style="color:#f97316"></i> ${p.popularity}</span>
                </div>
                <div class="card-score" style="color:${scoreColor}" title="${formulaTip}">
                    ${scoreDot} Rank Score: <strong>${score.toFixed(2)}</strong>
                </div>
            `;
            resultsGrid.appendChild(card);
        });
    }

    // ── DSA Performance Panel ────────────────────────────────────────
    const STRUCT_META = {
        'Token Trie (word match)':        { tag: 'tag-trie',   label: '🔍 Token Trie',     info: 'O(L) word prefix' },
        'Min-Heap (Top-K)':               { tag: 'tag-heap',   label: '🏆 Min-Heap',        info: 'O(M log K) ranking' },
        'LRU Cache':                      { tag: 'tag-lru',    label: '⚡ LRU Cache',        info: 'O(1) avg' },
        'Binary Search (price range)':    { tag: 'tag-binary', label: '🔢 Binary Search',   info: 'O(log N) price filter' },
        'PostgreSQL ORDER BY':            { tag: 'tag-db',     label: '🗄️ PostgreSQL',       info: 'Direct DB query' },
    };

    function updateDsaPanel(meta, query) {
        dsaPanel.style.display = '';
        dsaQuery.textContent = query || '—';

        // Structure list
        dsaStructures.innerHTML = '';
        (meta.structures_used || []).forEach(name => {
            const m = STRUCT_META[name] || { tag: 'tag-db', label: name, info: '' };
            const item = document.createElement('div');
            item.className = 'dsa-struct-item';

            // Special: LRU Cache shows HIT or MISS badge with O(1) avg
            let rightHtml;
            if (name === 'LRU Cache') {
                const cls  = meta.cache_hit ? 'cache-hit' : 'cache-miss';
                const icon = meta.cache_hit ? '✅' : '🔄';
                rightHtml  = `<span class="cache-badge ${cls}">${icon} ${meta.cache_hit ? 'HIT' : 'MISS'} · O(1) avg</span>`;
            } else {
                rightHtml = `<span class="dsa-struct-tag ${m.tag}">${m.info}</span>`;
            }

            item.innerHTML = `<span class="dsa-struct-name">${m.label}</span>${rightHtml}`;
            dsaStructures.appendChild(item);
        });

        // Stats — prefer measured engine time; fallback to API response time
        const engineMs = meta.engine_time_ms ?? meta.response_time_ms ?? '—';
        dsaTime.textContent    = engineMs + (meta.engine_time_ms !== undefined ? ' (Python)' : '');
        dsaCount.textContent   = meta.count ?? '—';
        dsaHitRate.textContent = (meta.hit_rate_pct ?? 0) + '%';
        dsaHits.textContent    = meta.cache_hits_total ?? 0;
        dsaMisses.textContent  = meta.cache_misses_total ?? 0;

        const total = (meta.cache_hits_total ?? 0) + (meta.cache_misses_total ?? 0);
        const pct   = total > 0 ? Math.round((meta.cache_hits_total / total) * 100) : 0;
        dsaCacheFill.style.width = pct + '%';
    }

    // ── Initial load ─────────────────────────────────────────────────
    performSearch('');
});
