# 📡 Collect - Financial News & Rumors Radar

**Collect** è un'applicazione web autonoma Full-Stack Python che raccoglie in tempo reale news ufficiali e rumors di mercato su singoli titoli azionari (sia del mercato italiano - Borsa Italiana / Piazza Affari, sia dei mercati USA - NASDAQ/NYSE), scelti dinamicamente dall'utente.

Tutti i contenuti raccolti in lingua straniera vengono tradotti automaticamente in **italiano** prima di essere salvati nel database SQLite con deduplicazione rigorosa e presentati in una dashboard dark-mode ordinata cronologicamente.

---

## 🛠️ Stack Tecnologico & Architettura (Zero-Cost)

- **Backend & Web Server**: Python 3.9+, [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [Jinja2](https://jinja.palletsprojects.com/).
- **Background Worker**: [APScheduler](https://apscheduler.readthedocs.io/) integrato direttamente nel ciclo di vita (`lifespan`) di FastAPI per eseguire la scansione continua ogni 5 minuti.
- **Database**: SQLite (`collect_news.db`) con indice `UNIQUE` su hash del titolo/URL e modalità WAL ad alte prestazioni per prevenire duplicati.
- **Motori di Ricerca (`scrapers/`)**:
  - `news_engine.py`: Estrazione delle notizie ufficiali tramite **yfinance** (Yahoo Finance) e **feedparser** su Google News RSS (paese/lingua IT e US).
  - `forum_engine.py`: Estrazione di rumors e discussioni utenti da **Reddit** (r/wallstreetbets, r/stocks, r/ItaliaPersonalFinance), **FinanzaOnline Forum** e **Investing.com Forum** utilizzando **curl_cffi** (per simulare fingerprint Chrome ed evitare blocchi Cloudflare) e **BeautifulSoup4**.
- **Traduzione Automatica**: `translator.py` basato su **deep-translator** (`GoogleTranslator`) con cache interna in-memory e fallback intelligente per tradurre automaticamente in italiano tutti i titoli e i testi esteri prima del salvataggio nel database.
- **Frontend (`templates/index.html`)**: Dashboard reattiva dark-mode con TailwindCSS (CDN), form per cambiare al volo il Ticker (es. `NVDA`, `ENI.MI`, `RACE.MI`, `AAPL`), filtri rapidi per categoria (`TUTTI`, `SOLO NEWS`, `SOLO RUMOR/FORUM`), ricerca istantanea, badge distintivo e auto-refresh continuo.

---

## 📁 Struttura del Progetto

```
collect/
├── .gitignore
├── requirements.txt
├── README.md
├── main.py
├── database.py
├── translator.py
├── scrapers/
│   ├── __init__.py
│   ├── news_engine.py
│   └── forum_engine.py
└── templates/
    └── index.html
```

---

## 🚀 Avvio Rapido

### 1. Attivazione ambiente virtuale e installazione dipendenze

```bash
cd /Users/giovannimancini/.gemini/antigravity/scratch/collect

# Crea l'ambiente virtuale
python3 -m venv .venv

# Attiva l'ambiente
source .venv/bin/activate

# Installa le dipendenze
pip install -r requirements.txt
```

### 2. Avvio del Server

```bash
python main.py
```
oppure con uvicorn:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Accedi alla dashboard dal browser su:  
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 💡 Funzionalità della Dashboard

1. **Cambio Ticker Istantaneo**: Inserisci qualsiasi simbolo nel form in alto (es. `NVDA`, `TSLA`, `ENI.MI`, `RACE.MI`, `UCG.MI`) e premi *"Analizza Ticker"*.
2. **Badge di Categoria**:
   - `NEWS UFFICIALE`: Notizie verificate e comunicati da Yahoo Finance, Reuters, Teleborsa, Milano Finanza, ecc.
   - `RUMOR / FORUM`: Discussioni, indiscrezioni e speculazioni da FinanzaOnline, Reddit e Investing.com.
3. **Ordinamento Cronologico Decrescente**: I post e le notizie sono presentati in ordine temporale rigoroso dal più recente al più vecchio.
4. **Visualizzazione Testo Originale**: Pulsante per visualizzare il testo originale pre-traduzione a fronte.
5. **Auto-refresh**: Contatore dinamico di 30 secondi che aggiorna la schermata con i nuovi elementi scoperti dal worker di background.
