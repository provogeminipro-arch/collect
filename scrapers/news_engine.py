import urllib.parse
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import feedparser
import yfinance as yf
from bs4 import BeautifulSoup
import dateutil.parser

logger = logging.getLogger(__name__)


def clean_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def parse_date(date_str: Any) -> str:
    if not date_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        if isinstance(date_str, (int, float)):
            # Timestamp in seconds
            return datetime.fromtimestamp(date_str, tz=timezone.utc).isoformat()
        dt = dateutil.parser.parse(str(date_str))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def fetch_from_yfinance(ticker: str) -> List[Dict[str, Any]]:
    items = []
    clean_ticker = ticker.strip().upper()
    try:
        search = yf.Search(clean_ticker, news_count=15)
        raw_news = getattr(search, "news", []) or []
        for n in raw_news:
            title = n.get("title", "").strip()
            link = n.get("link", "").strip()
            if not title or not link:
                continue

            pub_time = parse_date(n.get("providerPublishTime"))
            publisher = n.get("publisher", "Yahoo Finance")

            items.append({
                "ticker": clean_ticker,
                "url": link,
                "title_original": title,
                "content_original": title,
                "source": publisher or "Yahoo Finance",
                "category": "NEWS",
                "published_at": pub_time
            })
    except Exception as e:
        logger.warning(f"yfinance news error for {clean_ticker}: {e}")

    # Fallback to Ticker object news if search was empty
    if not items:
        try:
            t = yf.Ticker(clean_ticker)
            for n in getattr(t, "news", []) or []:
                title = n.get("title", "").strip()
                link = n.get("link", "").strip()
                if not title or not link:
                    continue
                pub_time = parse_date(n.get("providerPublishTime"))
                publisher = n.get("publisher", "Yahoo Finance")
                items.append({
                    "ticker": clean_ticker,
                    "url": link,
                    "title_original": title,
                    "content_original": title,
                    "source": publisher or "Yahoo Finance",
                    "category": "NEWS",
                    "published_at": pub_time
                })
        except Exception as e:
            logger.debug(f"yfinance Ticker news fallback error: {e}")

    return items


def fetch_from_google_news(ticker: str) -> List[Dict[str, Any]]:
    items = []
    clean_ticker = ticker.strip().upper()
    is_italian = clean_ticker.endswith(".MI")

    queries = []
    if is_italian:
        sym = clean_ticker.replace(".MI", "")
        queries.append((f"{clean_ticker} OR {sym} borsa OR trimestrale OR azioni", "it", "IT", "IT:it"))
    else:
        queries.append((f"{clean_ticker} stock OR earnings OR market", "en-US", "US", "US:en"))
        queries.append((f"{clean_ticker} borsa OR azioni", "it", "IT", "IT:it"))

    seen_urls = set()

    for q, hl, gl, ceid in queries:
        try:
            encoded_q = urllib.parse.quote(q)
            rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl={hl}&gl={gl}&ceid={ceid}"
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:25]:
                link = entry.get("link", "").strip()
                raw_title = entry.get("title", "").strip()
                if not link or not raw_title or link in seen_urls:
                    continue
                seen_urls.add(link)

                # Extract source name
                source_name = "Google News"
                title = raw_title
                if " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    source_name = parts[1].strip()

                summary = clean_html(entry.get("summary", ""))
                pub_date = parse_date(entry.get("published"))

                items.append({
                    "ticker": clean_ticker,
                    "url": link,
                    "title_original": title,
                    "content_original": summary or title,
                    "source": source_name,
                    "category": "NEWS",
                    "published_at": pub_date
                })
        except Exception as e:
            logger.warning(f"Google News RSS error for {clean_ticker} query '{q}': {e}")

    return items


def fetch_official_news(ticker: str) -> List[Dict[str, Any]]:
    """
    Combines yfinance and Google News RSS (IT & US) for official stock news.
    """
    clean_ticker = ticker.strip().upper()
    results = []
    seen = set()

    # 1. Fetch yfinance
    yf_items = fetch_from_yfinance(clean_ticker)
    for it in yf_items:
        if it["url"] not in seen:
            seen.add(it["url"])
            results.append(it)

    # 2. Fetch Google News RSS
    gn_items = fetch_from_google_news(clean_ticker)
    for it in gn_items:
        if it["url"] not in seen:
            seen.add(it["url"])
            results.append(it)

    return results
