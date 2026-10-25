# 📡 Collect - Stock News & Rumors Radar

**Collect** è una piattaforma autonoma progettata per scansionare continuamente la rete, i siti finanziari specializzati (Investing.it, Yahoo Finance, Milano Finanza, MarketScreener, Teleborsa) e le community/forum economici (Finanzaonline, Reddit, forum Investing), raccogliendo in tempo reale notizie, indiscrezioni (rumors) e analisi sui titoli azionari della **Borsa Italiana** (FTSE MIB) e del **mercato USA** (NASDAQ/NYSE).

Tutte le notizie internazionali vengono automaticamente tradotte in **italiano** ed organizzate cronologicamente in un feed in tempo reale dotato di dashboard web con aggiornamento via WebSocket.

---

## 🌟 Caratteristiche Principali

- 🔄 **Crawler Continuo e Motore di Ricerca**: Scansione automatica e periodica in background (intervallo personalizzabile es. ogni 5-15 min) o su richiesta istantanea ("Aggiorna Ora").
- 🇮🇹 **Traduzione Automatica in Italiano**: Tutte le notizie e i rumor in lingua straniera vengono tradotti fedelmente in italiano, preservando il testo originale consultabile con un click.
- 🔥 **Rilevamento Rumor vs Notizie Ufficiali**: Motore di analisi testuale con classificazione automatica tra:
  - **Rumor & Voci di Mercato** (trattative segrete, OPA, acquisizioni, fughe di notizie, delisting)
  - **Notizie Ufficiali** (comunicati societari, trimestrali, bilanci, dividendi)
  - **Forum & Community** (Finanzaonline, forum Investing.it, thread reddit)
  - **Analisi & Target Price** (consensus analisti, rating, upgrade/downgrade)
- 📊 **Analisi del Sentiment**: Classificazione automatica di ciascun articolo in *Positivo* (Bullish), *Neutro* o *Negativo* (Bearish).
- ⚡ **Feed in Tempo Reale con WebSocket**: Nuove notizie e rumors compaiono immediatamente sulla dashboard senza bisogno di ricaricare la pagina.
- 🎯 **Gestione Dinamica dei Titoli**: Possibilità di aggiungere e monitorare qualsiasi titolo nazionale (es. `RACE.MI`, `ENI.MI`, `UCG.MI`, `ISP.MI`, `STLAM.MI`) o americano (es. `AAPL`, `NVDA`, `TSLA`, `MSFT`, `AMZN`).
- 🗄️ **Database SQLite WAL Integrato**: Archiviazione locale ad alte prestazioni, con deduplicazione automatica per URL e titolo.

---

## 🏗️ Architettura del Progetto

```
collect/
├── app/
│   ├── config.py              # Configurazioni, percorsi, intervalli di default
│   ├── database.py            # Schema SQLite (WAL mode), CRUD notizie, titoli e log
│   ├── models.py              # Schemi Pydantic per validazione API
│   ├── crawler/
│   │   ├── collector.py       # Orchestratore scansioni multi-fonte e deduplicazione
│   │   ├── translator.py      # Servizio di traduzione in italiano con cache
│   │   ├── analyzer.py        # Classificatore rumor/notizia e scoring del sentiment
│   │   ├── scheduler.py       # Daemon asincrono per scansione periodica
│   │   └── sources/
│   │       ├── google_news.py # Scraper RSS multi-query (notizie, rumor, forum)
│   │       ├── yahoo_finance.py
│   │       └── investing_it.py
│   ├── static/
│   │   ├── index.html         # Dashboard reattiva moderna (Tailwind CSS, Lucide)
│   │   ├── css/styles.css     # Stili e animazioni radar
│   │   └── js/app.js          # Controller frontend, gestione filtri e WebSocket
│   └── main.py                # Applicazione FastAPI, API REST e endpoint WebSocket
├── run.py                     # Entry point per avviare il server
├── requirements.txt           # Dipendenze Python
└── README.md
```

---

## 🚀 Guida Rapida all'Avvio

### 1. Prerequisiti
- Python 3.9 o superiore.

### 2. Creazione ambiente virtuale e installazione dipendenze

```bash
# Entra nella directory del progetto
cd /Users/giovannimancini/.gemini/antigravity/scratch/collect

# Crea l'ambiente virtuale
python3 -m venv .venv

# Attiva l'ambiente virtuale
source .venv/bin/activate

# Installa i pacchetti richiesti
pip install -r requirements.txt
```

### 3. Avvio della Piattaforma

```bash
python run.py
```

La dashboard sarà immediatamente accessibile nel tuo browser all'indirizzo:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 💡 Utilizzo della Dashboard

1. **Selezione Titolo**: Clicca sui badge in alto (`TUTTI I TITOLI`, `🇮🇹 RACE.MI`, `🇮🇹 ENI.MI`, `🇺🇸 NVDA`, ecc.) per isolare le news di uno specifico asset.
2. **Filtro Tipologia**: Seleziona `Solo Rumors & Voci`, `Solo Notizie Ufficiali`, `Solo Forum` o `Solo Analisi`.
3. **Filtro Sentiment**: Filtra rapidamente per notizie con impatto positivo o negativo.
4. **Ricerca Testuale**: Digita qualsiasi termine nella barra di ricerca per una ricerca full-text immediata.
5. **Aggiunta Titolo**: Clicca su `+ Aggiungi Titolo` per inserire qualsiasi altro titolo italiano o USA; il crawler avvierà immediatamente una prima scansione per quel titolo.
6. **Aggiornamento Forzato**: Premi `Aggiorna Ora` per lanciare istantaneamente una scansione di tutti i titoli o di quello attualmente selezionato.

---

## 🌐 Fonti Monitorate
- **Investing.it**: Notizie, articoli di opinione, rassegna mercati e discussioni.
- **Finanzaonline**: Notizie e thread del forum economico più frequentato in Italia.
- **Yahoo Finance**: Notizie istituzionali e internazionali su titoli italiani e statunitensi.
- **Google News Finance Aggregator**: Indicizzazione in tempo reale di fonti primarie tra cui Il Sole 24 Ore, Milano Finanza, Teleborsa, MarketScreener, Reuters, Bloomberg, CNBC e Reddit (WallStreetBets / r/stocks).
