import urllib.parse
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from curl_cffi import requests
from bs4 import BeautifulSoup
import feedparser
import dateutil.parser

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def parse_date(date_val: Any) -> str:
    if not date_val:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = dateutil.parser.parse(str(date_val))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def fetch_finanzaonline_forum(ticker: str) -> List[Dict[str, Any]]:
    """
    Extracts forum threads and user rumors from FinanzaOnline using curl_cffi and BeautifulSoup4.
    """
    items = []
    clean_ticker = ticker.strip().upper().replace(".MI", "")
    url = f"https://forum.finanzaonline.com/search/1/?q={urllib.parse.quote(clean_ticker)}&o=date"

    try:
        res = requests.get(
            url,
            impersonate="chrome120",
            headers={"User-Agent": USER_AGENT},
            timeout=12
        )
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select(".contentRow-main")
            for row in rows[:15]:
                title_el = row.select_one(".contentRow-title a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                if href.startswith("/"):
                    href = f"https://forum.finanzaonline.com{href}"

                snippet_el = row.select_one(".contentRow-snippet")
                snippet = snippet_el.get_text(strip=True) if snippet_el else title

                time_el = row.select_one("time")
                pub_date = parse_date(time_el.get("datetime") if time_el else None)

                items.append({
                    "ticker": ticker.strip().upper(),
                    "url": href,
                    "title_original": title,
                    "content_original": snippet,
                    "source": "FinanzaOnline Forum",
                    "category": "RUMOR/FORUM",
                    "published_at": pub_date
                })
    except Exception as e:
        logger.warning(f"Error scraping FinanzaOnline for {clean_ticker}: {e}")

    return items


def fetch_reddit_rumors(ticker: str) -> List[Dict[str, Any]]:
    """
    Extracts rumors and discussions from Reddit (wallstreetbets, stocks, ItaliaPersonalFinance).
    Tries curl_cffi on Reddit public search; falls back to indexed Reddit threads.
    """
    items = []
    clean_ticker = ticker.strip().upper().replace(".MI", "")
    subreddits = ["wallstreetbets", "stocks", "ItaliaPersonalFinance"]

    # 1. Attempt direct curl_cffi for subreddits
    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={clean_ticker}&sort=new&restrict_sr=on&limit=10"
            res = requests.get(
                url,
                impersonate="chrome120",
                headers={"User-Agent": USER_AGENT},
                timeout=8
            )
            if res.status_code == 200:
                data = res.json().get("data", {}).get("children", [])
                for post in data:
                    pdata = post.get("data", {})
                    title = pdata.get("title", "")
                    selftext = pdata.get("selftext", "")
                    permalink = pdata.get("permalink", "")
                    created_utc = pdata.get("created_utc")

                    if title and permalink:
                        items.append({
                            "ticker": ticker.strip().upper(),
                            "url": f"https://reddit.com{permalink}",
                            "title_original": title,
                            "content_original": selftext[:400] if selftext else title,
                            "source": f"Reddit r/{sub}",
                            "category": "RUMOR/FORUM",
                            "published_at": datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat() if created_utc else datetime.now(timezone.utc).isoformat()
                        })
        except Exception as e:
            logger.debug(f"Direct Reddit curl_cffi error for r/{sub}: {e}")

    # 2. Resilient fallback for Reddit discussions
    if not items:
        try:
            q = f"site:reddit.com/r/wallstreetbets OR site:reddit.com/r/stocks OR site:reddit.com/r/ItaliaPersonalFinance {clean_ticker}"
            encoded_q = urllib.parse.quote(q)
            rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:10]:
                link = entry.get("link", "")
                raw_title = entry.get("title", "")
                if not link or not raw_title:
                    continue
                # Clean Reddit title
                title = raw_title.replace(" - Reddit", "").strip()
                summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(separator=" ", strip=True)
                items.append({
                    "ticker": ticker.strip().upper(),
                    "url": link,
                    "title_original": title,
                    "content_original": summary or title,
                    "source": "Reddit Community",
                    "category": "RUMOR/FORUM",
                    "published_at": parse_date(entry.get("published"))
                })
        except Exception as e:
            logger.warning(f"Reddit fallback error for {clean_ticker}: {e}")

    return items


def fetch_investing_forum(ticker: str) -> List[Dict[str, Any]]:
    """
    Extracts forum comments and rumors from Investing.com using curl_cffi and BeautifulSoup4.
    """
    items = []
    clean_ticker = ticker.strip().upper().replace(".MI", "")

    # Query investing.com discussions and opinion forums
    try:
        q = f'site:it.investing.com "{clean_ticker}" (commenti OR forum OR opinioni OR rumors)'
        encoded_q = urllib.parse.quote(q)
        rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=it&gl=IT&ceid=IT:it"
        feed = feedparser.parse(rss_url)

        for entry in feed.entries[:12]:
            link = entry.get("link", "")
            raw_title = entry.get("title", "")
            if not link or not raw_title:
                continue

            title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title
            summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(separator=" ", strip=True)

            items.append({
                "ticker": ticker.strip().upper(),
                "url": link,
                "title_original": title,
                "content_original": summary or title,
                "source": "Investing.com Forum",
                "category": "RUMOR/FORUM",
                "published_at": parse_date(entry.get("published"))
            })
    except Exception as e:
        logger.warning(f"Error fetching Investing forum for {clean_ticker}: {e}")

    return items


def fetch_forum_and_rumors(ticker: str) -> List[Dict[str, Any]]:
    """
    Aggregates rumors and community discussions from Reddit, FinanzaOnline, and Investing.com.
    """
    results = []
    seen = set()

    # 1. FinanzaOnline Forum
    for it in fetch_finanzaonline_forum(ticker):
        if it["url"] not in seen:
            seen.add(it["url"])
            results.append(it)

    # 2. Reddit Discussions
    for it in fetch_reddit_rumors(ticker):
        if it["url"] not in seen:
            seen.add(it["url"])
            results.append(it)

    # 3. Investing.com Forum / Opinions
    for it in fetch_investing_forum(ticker):
        if it["url"] not in seen:
            seen.add(it["url"])
            results.append(it)

    return results
