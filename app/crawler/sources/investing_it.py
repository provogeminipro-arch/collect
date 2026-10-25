import feedparser
import logging
from typing import List, Dict, Any
from app.crawler.sources.google_news import clean_html, parse_pub_date

logger = logging.getLogger(__name__)

INVESTING_FEEDS = [
    ("https://it.investing.com/rss/news_25.rss", "Investing.it Notizie"),
    ("https://it.investing.com/rss/stock_Opinion.rss", "Investing.it Opinioni"),
    ("https://it.investing.com/rss/market_overview.rss", "Investing.it Mercati"),
]


def fetch_investing_it(symbol: str, company_name: str) -> List[Dict[str, Any]]:
    results = []
    clean_sym = symbol.replace(".MI", "").lower()
    comp_clean = company_name.lower().split()[0] if company_name else clean_sym

    for feed_url, feed_source in INVESTING_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = entry.get("title", "")
                summary = clean_html(entry.get("summary", ""))
                text_to_check = f"{title} {summary}".lower()

                # Check if this article pertains to our ticker or company
                if clean_sym in text_to_check or comp_clean in text_to_check:
                    link = entry.get("link", "")
                    pub_date = parse_pub_date(entry)

                    results.append({
                        "title": title.strip(),
                        "summary": summary,
                        "url": link,
                        "source": feed_source,
                        "published_at": pub_date
                    })
        except Exception as e:
            logger.warning(f"Error fetching Investing.it feed {feed_url}: {e}")

    return results
