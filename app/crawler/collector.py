import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from app.database import (
    get_tickers, add_news_item, log_crawl,
    update_ticker_last_scraped
)
from app.crawler.sources.google_news import fetch_google_news
from app.crawler.sources.yahoo_finance import fetch_yahoo_finance
from app.crawler.sources.investing_it import fetch_investing_it
from app.crawler.translator import translate_to_italian
from app.crawler.analyzer import analyze_article

logger = logging.getLogger(__name__)


async def crawl_ticker(
    ticker_info: Dict[str, Any],
    on_new_item: Optional[Callable[[Dict[str, Any]], Any]] = None
) -> Dict[str, Any]:
    symbol = ticker_info["symbol"]
    name = ticker_info["name"]
    market = ticker_info.get("market", "")
    is_italian = symbol.endswith(".MI") or "Borsa Italiana" in market or "Milano" in market

    logger.info(f"Starting crawl for {symbol} ({name})...")
    raw_items = []

    # 1. Fetch from Google News (Multi-query: news, rumors, forums)
    try:
        gn_items = await asyncio.to_thread(fetch_google_news, symbol, name, is_italian)
        raw_items.extend(gn_items)
    except Exception as e:
        logger.error(f"Error fetching Google News for {symbol}: {e}")

    # 2. Fetch from Yahoo Finance
    try:
        yf_items = await asyncio.to_thread(fetch_yahoo_finance, symbol)
        raw_items.extend(yf_items)
    except Exception as e:
        logger.error(f"Error fetching Yahoo Finance for {symbol}: {e}")

    # 3. Fetch from Investing.it
    try:
        inv_items = await asyncio.to_thread(fetch_investing_it, symbol, name)
        raw_items.extend(inv_items)
    except Exception as e:
        logger.error(f"Error fetching Investing.it for {symbol}: {e}")

    # Deduplicate within this batch
    unique_items = []
    seen = set()
    for item in raw_items:
        key = item["url"] or item["title"]
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    items_found = len(unique_items)
    items_added = 0

    # Process and translate each item
    for item in unique_items:
        title_orig = item["title"]
        summary_orig = item.get("summary", "")
        source = item.get("source", "Web")

        # Classify and analyze sentiment & rumor
        is_rumor, source_type, sentiment = analyze_article(title_orig, summary_orig, source)

        # Translate to Italian (with caching and language detection)
        title_it = await asyncio.to_thread(translate_to_italian, title_orig)
        summary_it = ""
        if summary_orig:
            summary_it = await asyncio.to_thread(translate_to_italian, summary_orig)

        news_record = {
            "ticker": symbol,
            "title_original": title_orig,
            "title_it": title_it or title_orig,
            "summary_original": summary_orig,
            "summary_it": summary_it or summary_orig,
            "source": source,
            "source_type": source_type,
            "url": item["url"],
            "published_at": item["published_at"],
            "sentiment": sentiment,
            "is_rumor": is_rumor
        }

        # Save to DB (returns True only if new)
        was_added = add_news_item(news_record)
        if was_added:
            items_added += 1
            if on_new_item:
                try:
                    if asyncio.iscoroutinefunction(on_new_item):
                        await on_new_item(news_record)
                    else:
                        on_new_item(news_record)
                except Exception as cb_err:
                    logger.warning(f"Callback error on new item: {cb_err}")

    # Update state & logs
    update_ticker_last_scraped(symbol)
    log_crawl(
        ticker=symbol,
        items_found=items_found,
        items_added=items_added,
        status="success",
        message=f"Scanned {items_found} items, added {items_added} new items"
    )

    logger.info(f"Completed crawl for {symbol}: {items_found} found, {items_added} new.")
    return {
        "symbol": symbol,
        "items_found": items_found,
        "items_added": items_added
    }


async def crawl_all_active_tickers(
    on_new_item: Optional[Callable[[Dict[str, Any]], Any]] = None
) -> List[Dict[str, Any]]:
    active_tickers = get_tickers(active_only=True)
    results = []
    for ticker_info in active_tickers:
        res = await crawl_ticker(ticker_info, on_new_item=on_new_item)
        results.append(res)
        # Small delay between tickers to avoid hammering network
        await asyncio.sleep(1.0)
    return results
