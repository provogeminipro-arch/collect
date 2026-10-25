import urllib.parse
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import dateutil.parser
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def parse_pub_date(entry: Any) -> str:
    if hasattr(entry, "published"):
        try:
            dt = dateutil.parser.parse(entry.published)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()


def fetch_google_news(symbol: str, company_name: str, is_italian: bool = True) -> List[Dict[str, Any]]:
    results = []
    seen_links = set()

    # Formulate targeted queries
    queries = []
    
    clean_sym = symbol.replace(".MI", "")
    
    if is_italian:
        # Standard financial news & Italian markets
        queries.append((
            f'"{company_name}" OR "{clean_sym}" (borsa OR azioni OR trimestrale)',
            "it", "IT", "IT:it"
        ))
        # Rumors and M&A speculazioni
        queries.append((
            f'"{company_name}" (rumor OR voci OR opa OR acquisizione OR indiscrezioni)',
            "it", "IT", "IT:it"
        ))
        # Forum specific query
        queries.append((
            f'site:finanzaonline.com OR site:it.investing.com "{clean_sym}" OR "{company_name}"',
            "it", "IT", "IT:it"
        ))
    else:
        # US and international news
        queries.append((
            f'"{clean_sym}" OR "{company_name}" stock (earnings OR rumors OR acquisition)',
            "en-US", "US", "US:en"
        ))
        # International rumors
        queries.append((
            f'"{clean_sym}" (rumor OR rumour OR buyout OR takeover OR speculation)',
            "en-US", "US", "US:en"
        ))

    for query, hl, gl, ceid in queries:
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl={hl}&gl={gl}&ceid={ceid}"
            feed = feedparser.parse(url)

            for entry in feed.entries[:20]:
                link = entry.get("link", "")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                # Source title cleanup
                raw_title = entry.get("title", "")
                source_name = "Google News"
                if " - " in raw_title:
                    parts = raw_title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    source_name = parts[1].strip()
                else:
                    title = raw_title.strip()

                summary = clean_html(entry.get("summary", ""))
                # If summary is identical to title, leave summary empty or minimal
                if summary == title:
                    summary = ""

                pub_date = parse_pub_date(entry)

                results.append({
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "source": source_name,
                    "published_at": pub_date
                })
        except Exception as e:
            logger.warning(f"Error fetching Google News for {symbol} query '{query}': {e}")

    return results
