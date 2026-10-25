import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from app.config import DATABASE_PATH, INITIAL_TICKERS, DEFAULT_CRAWL_INTERVAL_MINUTES


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        # Tickers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                market TEXT NOT NULL,
                active BOOLEAN DEFAULT 1,
                last_scraped_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # News items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                guid TEXT UNIQUE NOT NULL,
                title_original TEXT NOT NULL,
                title_it TEXT NOT NULL,
                summary_original TEXT,
                summary_it TEXT,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                url TEXT NOT NULL,
                published_at TIMESTAMP NOT NULL,
                sentiment TEXT DEFAULT 'neutro',
                is_rumor BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_ticker ON news_items(ticker);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_published ON news_items(published_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_is_rumor ON news_items(is_rumor);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_source_type ON news_items(source_type);")

        # System settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Crawl logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawl_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                items_found INTEGER DEFAULT 0,
                items_added INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Set default settings if not exists
        cursor.execute("""
            INSERT OR IGNORE INTO system_settings (key, value)
            VALUES ('crawl_interval_minutes', ?)
        """, (str(DEFAULT_CRAWL_INTERVAL_MINUTES),))

        cursor.execute("""
            INSERT OR IGNORE INTO system_settings (key, value)
            VALUES ('auto_crawl_enabled', 'true')
        """)

        # Populate initial tickers if empty
        cursor.execute("SELECT COUNT(*) FROM tickers")
        if cursor.fetchone()[0] == 0:
            for t in INITIAL_TICKERS:
                cursor.execute("""
                    INSERT OR IGNORE INTO tickers (symbol, name, market, active)
                    VALUES (?, ?, ?, 1)
                """, (t["symbol"], t["name"], t["market"]))


def generate_guid(ticker: str, title: str, url: str) -> str:
    seed = f"{ticker}:{url}:{title.strip().lower()}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def get_tickers(active_only: bool = False) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM tickers"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY symbol ASC"
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]


def add_ticker(symbol: str, name: str, market: str) -> Optional[int]:
    clean_symbol = symbol.strip().upper()
    clean_name = name.strip() or clean_symbol
    clean_market = market.strip() or ("Borsa Italiana" if clean_symbol.endswith(".MI") else "US Market")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickers (symbol, name, market, active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(symbol) DO UPDATE SET active=1, name=excluded.name, market=excluded.market
        """, (clean_symbol, clean_name, clean_market))
        return cursor.lastrowid


def remove_ticker(ticker_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tickers WHERE id = ?", (ticker_id,))
        return cursor.rowcount > 0


def toggle_ticker(ticker_id: int, active: bool) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tickers SET active = ? WHERE id = ?", (1 if active else 0, ticker_id))
        return cursor.rowcount > 0


def update_ticker_last_scraped(symbol: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tickers SET last_scraped_at = CURRENT_TIMESTAMP WHERE symbol = ?
        """, (symbol,))


def add_news_item(item: Dict[str, Any]) -> bool:
    guid = item.get("guid") or generate_guid(item["ticker"], item["title_original"], item["url"])
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM news_items WHERE guid = ?", (guid,))
        if cursor.fetchone():
            return False  # Already exists

        cursor.execute("""
            INSERT INTO news_items (
                ticker, guid, title_original, title_it,
                summary_original, summary_it, source, source_type,
                url, published_at, sentiment, is_rumor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["ticker"],
            guid,
            item["title_original"],
            item.get("title_it", item["title_original"]),
            item.get("summary_original", ""),
            item.get("summary_it", item.get("summary_original", "")),
            item.get("source", "Web"),
            item.get("source_type", "news"),
            item["url"],
            item["published_at"],
            item.get("sentiment", "neutro"),
            1 if item.get("is_rumor") else 0
        ))
        return True


def get_news(
    ticker: Optional[str] = None,
    source_type: Optional[str] = None,
    is_rumor: Optional[bool] = None,
    sentiment: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        conditions = []
        params = []

        if ticker and ticker.upper() != "ALL":
            conditions.append("ticker = ?")
            params.append(ticker.upper())

        if source_type and source_type.lower() != "all":
            conditions.append("source_type = ?")
            params.append(source_type.lower())

        if is_rumor is not None:
            conditions.append("is_rumor = ?")
            params.append(1 if is_rumor else 0)

        if sentiment and sentiment.lower() != "all":
            conditions.append("sentiment = ?")
            params.append(sentiment.lower())

        if query:
            conditions.append("(title_it LIKE ? OR summary_it LIKE ? OR title_original LIKE ? OR source LIKE ?)")
            q_param = f"%{query}%"
            params.extend([q_param, q_param, q_param, q_param])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Total count
        count_query = f"SELECT COUNT(*) FROM news_items {where_clause}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        # Items page
        data_query = f"""
            SELECT * FROM news_items
            {where_clause}
            ORDER BY published_at DESC, id DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(data_query, params + [limit, offset])
        items = [dict(row) for row in cursor.fetchall()]

        return {"total": total, "items": items, "limit": limit, "offset": offset}


def get_stats() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM news_items")
        total_news = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM news_items WHERE is_rumor = 1")
        total_rumors = cursor.fetchone()[0]

        cursor.execute("SELECT sentiment, COUNT(*) FROM news_items GROUP BY sentiment")
        sentiment_dist = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("SELECT source_type, COUNT(*) FROM news_items GROUP BY source_type")
        source_dist = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT ticker, COUNT(*) as count, SUM(is_rumor) as rumors
            FROM news_items
            GROUP BY ticker
            ORDER BY count DESC
            LIMIT 10
        """)
        top_tickers = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) FROM tickers WHERE active = 1")
        active_tickers_count = cursor.fetchone()[0]

        return {
            "total_news": total_news,
            "total_rumors": total_rumors,
            "sentiment_dist": sentiment_dist,
            "source_dist": source_dist,
            "top_tickers": top_tickers,
            "active_tickers_count": active_tickers_count
        }


def get_setting(key: str, default: str = "") -> str:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default


def set_setting(key: str, value: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, str(value)))


def log_crawl(ticker: str, items_found: int, items_added: int, status: str, message: str = ""):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO crawl_logs (ticker, items_found, items_added, status, message)
            VALUES (?, ?, ?, ?, ?)
        """, (ticker, items_found, items_added, status, message))


def get_recent_logs(limit: int = 25) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM crawl_logs
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
