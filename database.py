import sqlite3
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager

DB_NAME = "collect_news.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def generate_title_hash(ticker: str, title: str, url: str) -> str:
    clean_str = f"{ticker.upper()}:{url.strip()}:{title.strip().lower()}"
    return hashlib.sha256(clean_str.encode("utf-8")).hexdigest()


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                url TEXT NOT NULL,
                title_original TEXT NOT NULL,
                title_it TEXT NOT NULL,
                content_original TEXT,
                content_it TEXT,
                source TEXT NOT NULL,
                category TEXT NOT NULL, -- 'NEWS' or 'RUMOR/FORUM'
                published_at TIMESTAMP NOT NULL,
                title_hash TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON news_items(ticker);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_published ON news_items(published_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON news_items(category);")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_url_ticker ON news_items(ticker, url);")


def insert_item(item: Dict[str, Any]) -> bool:
    ticker = item["ticker"].strip().upper()
    title_orig = item["title_original"].strip()
    url = item["url"].strip()
    title_hash = item.get("title_hash") or generate_title_hash(ticker, title_orig, url)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM news_items WHERE title_hash = ? OR (ticker = ? AND url = ?)", (title_hash, ticker, url))
        if cursor.fetchone():
            return False  # Duplicate found, skip

        cursor.execute("""
            INSERT INTO news_items (
                ticker, url, title_original, title_it,
                content_original, content_it, source, category,
                published_at, title_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            url,
            title_orig,
            item.get("title_it") or title_orig,
            item.get("content_original", ""),
            item.get("content_it", ""),
            item.get("source", "Web"),
            item.get("category", "NEWS"),
            item.get("published_at", datetime.utcnow().isoformat()),
            title_hash
        ))
        return True


def get_items(
    ticker: Optional[str] = None,
    category: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        conditions = []
        params = []

        if ticker and ticker.upper() != "ALL":
            conditions.append("ticker = ?")
            params.append(ticker.upper())

        if category and category.upper() != "ALL":
            conditions.append("category = ?")
            params.append(category.upper())

        if query and query.strip():
            conditions.append("(title_it LIKE ? OR content_it LIKE ? OR title_original LIKE ? OR source LIKE ?)")
            q_param = f"%{query.strip()}%"
            params.extend([q_param, q_param, q_param, q_param])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query_sql = f"""
            SELECT * FROM news_items
            {where_clause}
            ORDER BY published_at DESC, id DESC
            LIMIT ?
        """
        cursor.execute(query_sql, params + [limit])
        return [dict(row) for row in cursor.fetchall()]


def get_active_tickers() -> List[str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT ticker FROM news_items ORDER BY ticker ASC")
        return [row[0] for row in cursor.fetchall()]


def get_stats() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM news_items")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM news_items WHERE category = 'NEWS'")
        total_news = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM news_items WHERE category = 'RUMOR/FORUM'")
        total_rumors = cursor.fetchone()[0]

        cursor.execute("SELECT DISTINCT ticker FROM news_items")
        tickers = [row[0] for row in cursor.fetchall()]

        return {
            "total": total,
            "total_news": total_news,
            "total_rumors": total_rumors,
            "tickers_count": len(tickers)
        }


def delete_ticker(ticker: str) -> int:
    clean_ticker = ticker.strip().upper()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM news_items WHERE ticker = ?", (clean_ticker,))
        return cursor.rowcount


def delete_item(item_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM news_items WHERE id = ?", (item_id,))
        return cursor.rowcount > 0

