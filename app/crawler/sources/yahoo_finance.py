import feedparser
import logging
from typing import List, Dict, Any
from app.crawler.sources.google_news import clean_html, parse_pub_date

logger = logging.getLogger(__name__)


def fetch_yahoo_finance(symbol: str) -> List[Dict[str, Any]]:
    results = []
    # e.g., NVDA, AAPL, RACE.MI, ENI.MI
    url = f"https://finance.yahoo.com/rss/headline?s={symbol}"
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            if not title or not link:
                continue

            summary = clean_html(entry.get("summary", ""))
            pub_date = parse_pub_date(entry)

            results.append({
                "title": title,
                "summary": summary,
                "url": link,
                "source": "Yahoo Finance",
                "published_at": pub_date
            })
    except Exception as e:
        logger.warning(f"Error fetching Yahoo Finance for {symbol}: {e}")

    return results
