/**
 * Collect - Real-time Stock News & Rumors Collector
 * Front-end controller
 */

const state = {
    selectedTicker: 'ALL',
    selectedType: 'all',
    selectedSentiment: 'all',
    searchQuery: '',
    offset: 0,
    limit: 30,
    total: 0,
    tickers: [],
    news: [],
    isCrawling: false,
    ws: null
};

// DOM Elements
const newsFeed = document.getElementById('newsFeed');
const tickerPillsContainer = document.getElementById('tickerPillsContainer');
const searchInput = document.getElementById('searchInput');
const typeFilter = document.getElementById('typeFilter');
const sentimentFilter = document.getElementById('sentimentFilter');
const btnResetFilters = document.getElementById('btnResetFilters');
const btnManualCrawl = document.getElementById('btnManualCrawl');
const refreshIcon = document.getElementById('refreshIcon');
const btnLoadMore = document.getElementById('btnLoadMore');
const paginationWrapper = document.getElementById('paginationWrapper');
const streamCounter = document.getElementById('streamCounter');
const activeFilterLabel = document.getElementById('activeFilterLabel');

// Metrics
const statTotalNews = document.getElementById('statTotalNews');
const statTotalRumors = document.getElementById('statTotalRumors');
const statActiveTickers = document.getElementById('statActiveTickers');
const statPos = document.getElementById('statPos');
const statNeg = document.getElementById('statNeg');
const statNeu = document.getElementById('statNeu');

// Status Badges
const crawlerStatusBadge = document.getElementById('crawlerStatusBadge');
const crawlerStatusText = document.getElementById('crawlerStatusText');
const crawlerPing = document.getElementById('crawlerPing');
const crawlerDot = document.getElementById('crawlerDot');

// Modals
const modalAddTicker = document.getElementById('modalAddTicker');
const btnOpenAddModal = document.getElementById('btnOpenAddModal');
const btnCloseAddModal = document.getElementById('btnCloseAddModal');
const btnCancelAddTicker = document.getElementById('btnCancelAddTicker');
const formAddTicker = document.getElementById('formAddTicker');

const modalSettings = document.getElementById('modalSettings');
const btnOpenSettingsModal = document.getElementById('btnOpenSettingsModal');
const btnCloseSettingsModal = document.getElementById('btnCloseSettingsModal');
const settingIntervalInput = document.getElementById('settingIntervalInput');
const settingAutoCrawlCheckbox = document.getElementById('settingAutoCrawlCheckbox');
const btnSaveSettings = document.getElementById('btnSaveSettings');
const tickersTableBody = document.getElementById('tickersTableBody');
const crawlLogsContainer = document.getElementById('crawlLogsContainer');


// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    initLucide();
    setupEventListeners();
    loadStats();
    loadTickers().then(() => {
        loadNews(true);
    });
    initWebSocket();
});

function initLucide() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
}


// --- API & Data Loading ---

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const stats = await res.json();
        statTotalNews.textContent = stats.total_news.toLocaleString('it-IT');
        statTotalRumors.textContent = stats.total_rumors.toLocaleString('it-IT');
        statActiveTickers.textContent = stats.active_tickers_count;

        const pos = stats.sentiment_dist?.positivo || 0;
        const neg = stats.sentiment_dist?.negativo || 0;
        const neu = stats.sentiment_dist?.neutro || 0;
        statPos.textContent = `${pos}+`;
        statNeg.textContent = `${neg}-`;
        statNeu.textContent = `${neu}=`;
    } catch (err) {
        console.error('Failed to load stats:', err);
    }
}

async function loadTickers() {
    try {
        const res = await fetch('/api/tickers');
        if (!res.ok) return;
        state.tickers = await res.json();
        renderTickerPills();
    } catch (err) {
        console.error('Failed to load tickers:', err);
    }
}

function renderTickerPills() {
    tickerPillsContainer.innerHTML = '';

    // "TUTTI" Pill
    const allBtn = document.createElement('button');
    allBtn.className = `px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1.5 ${
        state.selectedTicker === 'ALL'
            ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 ring-1 ring-emerald-400'
            : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-darkborder'
    }`;
    allBtn.innerHTML = `<span>TUTTI I TITOLI</span>`;
    allBtn.onclick = () => selectTicker('ALL');
    tickerPillsContainer.appendChild(allBtn);

    // Individual Tickers
    state.tickers.forEach(t => {
        if (!t.active) return;
        const btn = document.createElement('button');
        const isSelected = state.selectedTicker === t.symbol;
        const isBorsaIt = t.symbol.endsWith('.MI') || t.market.includes('Borsa Italiana');

        btn.className = `px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 ${
            isSelected
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 ring-1 ring-emerald-400'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700 border border-darkborder'
        }`;

        const flag = isBorsaIt ? '🇮🇹' : '🇺🇸';
        btn.innerHTML = `
            <span>${flag}</span>
            <span class="font-bold">${t.symbol}</span>
            <span class="text-[11px] text-slate-400 font-normal">(${t.name.split(' ')[0]})</span>
        `;
        btn.onclick = () => selectTicker(t.symbol);
        tickerPillsContainer.appendChild(btn);
    });
}

function selectTicker(symbol) {
    state.selectedTicker = symbol;
    activeFilterLabel.textContent = symbol === 'ALL' ? 'Mostrati tutti' : `Filtrato per: ${symbol}`;
    renderTickerPills();
    loadNews(true);
}

async function loadNews(reset = false) {
    if (reset) {
        state.offset = 0;
        state.news = [];
        newsFeed.innerHTML = `
            <div id="feedLoading" class="py-16 text-center">
                <i data-lucide="loader-2" class="w-8 h-8 text-emerald-400 animate-spin mx-auto mb-3"></i>
                <p class="text-sm text-slate-400">Scansione del database e caricamento in corso...</p>
            </div>
        `;
        initLucide();
    }

    const params = new URLSearchParams({
        limit: state.limit.toString(),
        offset: state.offset.toString()
    });

    if (state.selectedTicker !== 'ALL') {
        params.append('ticker', state.selectedTicker);
    }
    if (state.selectedType !== 'all') {
        params.append('source_type', state.selectedType);
    }
    if (state.selectedSentiment !== 'all') {
        params.append('sentiment', state.selectedSentiment);
    }
    if (state.searchQuery.trim()) {
        params.append('q', state.searchQuery.trim());
    }

    try {
        const res = await fetch(`/api/news?${params.toString()}`);
        if (!res.ok) throw new Error('API error');
        const data = await res.json();

        state.total = data.total;
        streamCounter.textContent = `${data.total} elementi trovati`;

        if (reset) {
            state.news = data.items;
        } else {
            state.news = [...state.news, ...data.items];
        }

        renderNewsFeed(state.news);

        // Manage Load More button
        if (state.news.length < data.total) {
            paginationWrapper.classList.remove('hidden');
        } else {
            paginationWrapper.classList.add('hidden');
        }
    } catch (err) {
        console.error('Failed to load news:', err);
        newsFeed.innerHTML = `
            <div class="py-12 text-center text-rose-400 text-sm">
                Errore nel recupero delle notizie. Riprova tra poco.
            </div>
        `;
    }
}

function renderNewsFeed(items) {
    if (!items || items.length === 0) {
        newsFeed.innerHTML = `
            <div class="py-16 text-center bg-darkcard rounded-xl border border-darkborder p-8">
                <div class="w-12 h-12 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center mx-auto mb-3">
                    <i data-lucide="inbox" class="w-6 h-6"></i>
                </div>
                <h4 class="text-base font-semibold text-white mb-1">Nessuna notizia o rumor trovato</h4>
                <p class="text-xs text-slate-400 max-w-sm mx-auto mb-4">
                    Non ci sono al momento elementi con i filtri attuali. Puoi cliccare su "Aggiorna Ora" per scansionare la rete.
                </p>
                <button onclick="triggerManualCrawl()" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold">
                    Lancia Scansione Immediata
                </button>
            </div>
        `;
        initLucide();
        return;
    }

    newsFeed.innerHTML = items.map(item => createNewsCardHTML(item)).join('');
    initLucide();
}

function createNewsCardHTML(item) {
    // Badges logic
    const isRumor = item.is_rumor;
    const typeLabel = getTypeBadge(item.source_type, isRumor);
    const sentimentBadge = getSentimentBadge(item.sentiment);
    const formattedDate = formatDateTime(item.published_at);
    const flag = item.ticker.endsWith('.MI') ? '🇮🇹' : '🇺🇸';

    const cardId = `news-${item.id}`;

    return `
        <article id="${cardId}" class="news-card bg-darkcard border border-darkborder rounded-xl p-4 sm:p-5 shadow-sm space-y-3">
            <!-- Header Badges & Meta -->
            <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div class="flex flex-wrap items-center gap-1.5">
                    <!-- Ticker Pill -->
                    <span class="px-2.5 py-1 rounded-md font-bold tracking-wide bg-slate-800 text-white border border-slate-700 flex items-center space-x-1">
                        <span>${flag}</span>
                        <span>${escapeHtml(item.ticker)}</span>
                    </span>

                    <!-- Type Badge -->
                    ${typeLabel}

                    <!-- Sentiment Badge -->
                    ${sentimentBadge}

                    <!-- Source -->
                    <span class="text-slate-400 text-xs px-2 py-0.5 rounded bg-slate-900 border border-darkborder">
                        ${escapeHtml(item.source)}
                    </span>
                </div>

                <!-- Date & Time -->
                <div class="text-slate-400 text-xs flex items-center space-x-1 font-mono">
                    <i data-lucide="calendar" class="w-3.5 h-3.5 text-slate-500"></i>
                    <span>${formattedDate}</span>
                </div>
            </div>

            <!-- News Title in Italian -->
            <div>
                <h3 class="text-base sm:text-lg font-bold text-slate-100 hover:text-emerald-400 transition-colors leading-snug">
                    <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" class="hover:underline flex items-start gap-1.5">
                        <span>${escapeHtml(item.title_it || item.title_original)}</span>
                    </a>
                </h3>
            </div>

            <!-- Summary in Italian -->
            ${item.summary_it ? `
                <p class="text-xs sm:text-sm text-slate-300 leading-relaxed">
                    ${escapeHtml(item.summary_it)}
                </p>
            ` : ''}

            <!-- Bottom Actions: Toggle Original & Open Source -->
            <div class="pt-2 border-t border-darkborder/60 flex flex-wrap items-center justify-between gap-2 text-xs">
                ${item.title_original && item.title_original !== item.title_it ? `
                    <button onclick="toggleOriginal('${item.id}')" class="text-slate-400 hover:text-slate-200 flex items-center space-x-1 transition-colors">
                        <i data-lucide="languages" class="w-3.5 h-3.5"></i>
                        <span id="btn-orig-text-${item.id}">Mostra originale</span>
                    </button>
                ` : `<span></span>`}

                <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" class="text-emerald-400 hover:text-emerald-300 font-semibold flex items-center space-x-1 hover:underline">
                    <span>Leggi fonte originale</span>
                    <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                </a>
            </div>

            <!-- Collapsible Original Content -->
            <div id="orig-box-${item.id}" class="hidden p-3 rounded-lg bg-slate-900/90 border border-darkborder text-xs text-slate-400 space-y-1">
                <p class="font-semibold text-slate-300">Testo Originale:</p>
                <p class="italic text-slate-300">${escapeHtml(item.title_original)}</p>
                ${item.summary_original ? `<p class="text-[11px] text-slate-400">${escapeHtml(item.summary_original)}</p>` : ''}
            </div>
        </article>
    `;
}

function getTypeBadge(sourceType, isRumor) {
    if (isRumor || sourceType === 'rumor') {
        return `<span class="px-2 py-0.5 rounded-md font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center space-x-1">
            <i data-lucide="flame" class="w-3 h-3"></i>
            <span>RUMOR / VOCE</span>
        </span>`;
    }
    if (sourceType === 'forum') {
        return `<span class="px-2 py-0.5 rounded-md font-medium bg-purple-500/15 text-purple-300 border border-purple-500/30 flex items-center space-x-1">
            <i data-lucide="messages-square" class="w-3 h-3"></i>
            <span>FORUM / COMMUNITY</span>
        </span>`;
    }
    if (sourceType === 'analisi') {
        return `<span class="px-2 py-0.5 rounded-md font-medium bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 flex items-center space-x-1">
            <i data-lucide="pie-chart" class="w-3 h-3"></i>
            <span>ANALISI</span>
        </span>`;
    }
    return `<span class="px-2 py-0.5 rounded-md font-medium bg-blue-500/15 text-blue-300 border border-blue-500/30 flex items-center space-x-1">
        <i data-lucide="file-text" class="w-3 h-3"></i>
        <span>NOTIZIA</span>
    </span>`;
}

function getSentimentBadge(sentiment) {
    if (sentiment === 'positivo') {
        return `<span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            ▲ POSITIVO
        </span>`;
    }
    if (sentiment === 'negativo') {
        return `<span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            ▼ NEGATIVO
        </span>`;
    }
    return `<span class="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-700/50 text-slate-300 border border-slate-700">
        • NEUTRO
    </span>`;
}

function toggleOriginal(id) {
    const box = document.getElementById(`orig-box-${id}`);
    const btnText = document.getElementById(`btn-orig-text-${id}`);
    if (box) {
        if (box.classList.contains('hidden')) {
            box.classList.remove('hidden');
            if (btnText) btnText.textContent = 'Nascondi originale';
        } else {
            box.classList.add('hidden');
            if (btnText) btnText.textContent = 'Mostra originale';
        }
    }
}

function formatDateTime(isoString) {
    if (!isoString) return '';
    try {
        const d = new Date(isoString);
        return d.toLocaleString('it-IT', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch {
        return isoString;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}


// --- WebSocket Live Stream ---

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = () => {
        console.log('WebSocket connected to live news radar');
    };

    state.ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'crawler_status') {
                updateCrawlerUI(data.is_crawling, data.ticker);
            } else if (data.type === 'new_item') {
                handleNewIncomingItem(data.item);
            }
        } catch (e) {
            console.error('Error handling WS message:', e);
        }
    };

    state.ws.onclose = () => {
        console.warn('WebSocket closed, attempting reconnect in 3s...');
        setTimeout(initWebSocket, 3000);
    };

    state.ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        state.ws.close();
    };
}

function updateCrawlerUI(isCrawling, ticker) {
    state.isCrawling = isCrawling;
    if (isCrawling) {
        crawlerStatusBadge.classList.remove('hidden');
        crawlerStatusText.textContent = ticker && ticker !== 'ALL' ? `Scansione ${ticker}...` : 'Scansione in corso...';
        crawlerPing.classList.add('animate-ping');
        crawlerDot.className = 'relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-400';
        refreshIcon.classList.add('animate-spin-fast');
    } else {
        crawlerStatusText.textContent = 'Crawler attivo (In attesa)';
        crawlerPing.classList.remove('animate-ping');
        crawlerDot.className = 'relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500';
        refreshIcon.classList.remove('animate-spin-fast');
    }
}

function handleNewIncomingItem(item) {
    // Check if matches current active filters
    if (state.selectedTicker !== 'ALL' && state.selectedTicker !== item.ticker) {
        loadStats();
        return;
    }
    if (state.selectedType !== 'all' && state.selectedType !== item.source_type) {
        loadStats();
        return;
    }
    if (state.selectedSentiment !== 'all' && state.selectedSentiment !== item.sentiment) {
        loadStats();
        return;
    }

    // Prepend to current feed with animation
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = createNewsCardHTML(item);
    const newCard = tempDiv.firstElementChild;
    newCard.classList.add('ring-2', 'ring-emerald-500', 'bg-emerald-950/20');

    // Remove empty state if present
    const emptyState = newsFeed.querySelector('.bg-darkcard');
    if (emptyState && !emptyState.classList.contains('news-card')) {
        newsFeed.innerHTML = '';
    }

    newsFeed.insertBefore(newCard, newsFeed.firstChild);
    initLucide();

    // Remove glow after 4 seconds
    setTimeout(() => {
        newCard.classList.remove('ring-2', 'ring-emerald-500', 'bg-emerald-950/20');
    }, 4000);

    loadStats();
}


// --- Event Listeners ---

function setupEventListeners() {
    // Filter controls
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            state.searchQuery = e.target.value;
            loadNews(true);
        }, 300);
    });

    typeFilter.addEventListener('change', (e) => {
        state.selectedType = e.target.value;
        loadNews(true);
    });

    sentimentFilter.addEventListener('change', (e) => {
        state.selectedSentiment = e.target.value;
        loadNews(true);
    });

    btnResetFilters.addEventListener('click', () => {
        searchInput.value = '';
        typeFilter.value = 'all';
        sentimentFilter.value = 'all';
        state.searchQuery = '';
        state.selectedType = 'all';
        state.selectedSentiment = 'all';
        selectTicker('ALL');
    });

    // Manual Crawl
    btnManualCrawl.addEventListener('click', triggerManualCrawl);

    // Load More
    btnLoadMore.addEventListener('click', () => {
        state.offset += state.limit;
        loadNews(false);
    });

    // Modal: Add Ticker
    btnOpenAddModal.addEventListener('click', () => {
        modalAddTicker.classList.remove('hidden');
    });
    btnCloseAddModal.addEventListener('click', () => {
        modalAddTicker.classList.add('hidden');
    });
    btnCancelAddTicker.addEventListener('click', () => {
        modalAddTicker.classList.add('hidden');
    });

    // Quick suggestions in Add Modal
    document.querySelectorAll('.quick-suggest').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('inputTickerSymbol').value = btn.dataset.sym;
            document.getElementById('inputTickerName').value = btn.dataset.name;
            document.getElementById('inputTickerMarket').value = btn.dataset.m;
        });
    });

    // Form Add Ticker Submit
    formAddTicker.addEventListener('submit', async (e) => {
        e.preventDefault();
        const symbol = document.getElementById('inputTickerSymbol').value.trim().toUpperCase();
        const name = document.getElementById('inputTickerName').value.trim();
        const market = document.getElementById('inputTickerMarket').value;

        try {
            const res = await fetch('/api/tickers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol, name, market })
            });

            if (res.ok) {
                modalAddTicker.classList.add('hidden');
                formAddTicker.reset();
                await loadTickers();
                selectTicker(symbol);
                loadStats();
            } else {
                alert('Errore durante il salvataggio del titolo.');
            }
        } catch (err) {
            console.error('Failed to add ticker:', err);
        }
    });

    // Modal: Settings & Management
    btnOpenSettingsModal.addEventListener('click', openSettingsModal);
    btnCloseSettingsModal.addEventListener('click', () => {
        modalSettings.classList.add('hidden');
    });
    btnSaveSettings.addEventListener('click', saveSettings);
}

async function triggerManualCrawl() {
    if (state.isCrawling) return;
    updateCrawlerUI(true, state.selectedTicker !== 'ALL' ? state.selectedTicker : null);

    try {
        const body = state.selectedTicker !== 'ALL' ? { ticker: state.selectedTicker } : {};
        const res = await fetch('/api/crawl/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        console.log('Manual crawl started:', data);
    } catch (err) {
        console.error('Trigger crawl error:', err);
    }
}

async function openSettingsModal() {
    modalSettings.classList.remove('hidden');
    try {
        const [settingsRes, tickersRes, logsRes] = await Promise.all([
            fetch('/api/settings'),
            fetch('/api/tickers'),
            fetch('/api/crawl/logs')
        ]);

        if (settingsRes.ok) {
            const settings = await settingsRes.json();
            settingIntervalInput.value = settings.crawl_interval_minutes;
            settingAutoCrawlCheckbox.checked = settings.auto_crawl_enabled;
        }

        if (tickersRes.ok) {
            const tickers = await tickersRes.json();
            renderTickersTable(tickers);
        }

        if (logsRes.ok) {
            const logs = await logsRes.json();
            renderLogs(logs);
        }
    } catch (err) {
        console.error('Error opening settings modal:', err);
    }
}

function renderTickersTable(tickers) {
    tickersTableBody.innerHTML = tickers.map(t => `
        <tr class="hover:bg-slate-900/50 transition-colors">
            <td class="p-3 font-bold text-white">${escapeHtml(t.symbol)}</td>
            <td class="p-3 text-slate-300">${escapeHtml(t.name)}</td>
            <td class="p-3 text-slate-400">${escapeHtml(t.market)}</td>
            <td class="p-3 text-slate-400 font-mono">${formatDateTime(t.last_scraped_at) || 'Mai'}</td>
            <td class="p-3 text-right space-x-2">
                <button onclick="deleteTicker(${t.id})" class="text-rose-400 hover:text-rose-300 transition-colors">
                    Elimina
                </button>
            </td>
        </tr>
    `).join('');
}

function renderLogs(logs) {
    if (!logs || logs.length === 0) {
        crawlLogsContainer.innerHTML = '<p class="text-slate-500">Nessun log recente.</p>';
        return;
    }
    crawlLogsContainer.innerHTML = logs.map(l => `
        <div class="flex items-start justify-between">
            <span class="text-slate-500">${formatDateTime(l.timestamp)}</span>
            <span class="text-emerald-400 font-bold ml-2">${escapeHtml(l.ticker || 'GLOBAL')}</span>
            <span class="text-slate-300 ml-2 flex-1 truncate">${escapeHtml(l.message || '')}</span>
            <span class="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 ml-2">${escapeHtml(l.status)}</span>
        </div>
    `).join('');
}

async function saveSettings() {
    const crawl_interval_minutes = parseInt(settingIntervalInput.value, 10);
    const auto_crawl_enabled = settingAutoCrawlCheckbox.checked;

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ crawl_interval_minutes, auto_crawl_enabled })
        });
        if (res.ok) {
            btnSaveSettings.textContent = 'Salvate!';
            setTimeout(() => {
                btnSaveSettings.textContent = 'Salva Impostazioni';
            }, 2000);
        }
    } catch (err) {
        console.error('Error saving settings:', err);
    }
}

async function deleteTicker(id) {
    if (!confirm('Sei sicuro di voler rimuovere questo titolo?')) return;
    try {
        const res = await fetch(`/api/tickers/${id}`, { method: 'DELETE' });
        if (res.ok) {
            await loadTickers();
            openSettingsModal();
            loadStats();
        }
    } catch (err) {
        console.error('Error deleting ticker:', err);
    }
}

window.deleteTicker = deleteTicker;
window.toggleOriginal = toggleOriginal;
window.triggerManualCrawl = triggerManualCrawl;
