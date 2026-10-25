import logging
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import (
    init_db, insert_item, get_items, get_active_tickers,
    get_stats, delete_ticker, delete_item
)
from translator import translate_text
from scrapers.news_engine import fetch_official_news
from scrapers.forum_engine import fetch_forum_and_rumors

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("collect")

templates = Jinja2Templates(directory="templates")
scheduler = AsyncIOScheduler()

# Default tickers to seed and monitor continuously
DEFAULT_TICKERS = ["NVDA", "ENI.MI", "RACE.MI", "AAPL", "UCG.MI"]
CURRENT_ACTIVE_TICKER = "NVDA"


async def process_and_save_items(items: list) -> int:
    added = 0
    for it in items:
        try:
            # Automatic translation to Italian before DB insertion
            title_it = await asyncio.to_thread(translate_text, it["title_original"])
            content_it = ""
            if it.get("content_original"):
                content_it = await asyncio.to_thread(translate_text, it["content_original"])

            record = {
                "ticker": it["ticker"],
                "url": it["url"],
                "title_original": it["title_original"],
                "title_it": title_it or it["title_original"],
                "content_original": it.get("content_original", ""),
                "content_it": content_it or it.get("content_original", ""),
                "source": it.get("source", "Web"),
                "category": it.get("category", "NEWS"),
                "published_at": it.get("published_at")
            }

            if insert_item(record):
                added += 1
        except Exception as e:
            logger.error(f"Error saving item {it.get('url')}: {e}")
    return added


async def scrape_ticker_task(ticker: str):
    clean_ticker = ticker.strip().upper()
    logger.info(f"Starting scheduled scrape for ticker: {clean_ticker}")

    # 1. Fetch official news
    try:
        news_items = await asyncio.to_thread(fetch_official_news, clean_ticker)
        news_added = await process_and_save_items(news_items)
        logger.info(f"Official news for {clean_ticker}: {len(news_items)} fetched, {news_added} added to DB.")
    except Exception as e:
        logger.error(f"Error fetching official news for {clean_ticker}: {e}")

    # 2. Fetch forum & rumors
    try:
        forum_items = await asyncio.to_thread(fetch_forum_and_rumors, clean_ticker)
        forum_added = await process_and_save_items(forum_items)
        logger.info(f"Forum & rumors for {clean_ticker}: {len(forum_items)} fetched, {forum_added} added to DB.")
    except Exception as e:
        logger.error(f"Error fetching forum/rumors for {clean_ticker}: {e}")


async def scheduled_crawl_cycle():
    """Continuous background job executed every 5 minutes by APScheduler."""
    logger.info("--- Starting 5-minute APScheduler collection cycle ---")
    tickers = get_active_tickers()
    if not tickers:
        tickers = DEFAULT_TICKERS

    for t in tickers:
        await scrape_ticker_task(t)
        await asyncio.sleep(1.0)
    logger.info("--- Finished 5-minute APScheduler collection cycle ---")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite DB
    logger.info("Initializing SQLite database collect_news.db...")
    init_db()

    # Start APScheduler: 5-minute interval
    scheduler.add_job(scheduled_crawl_cycle, "interval", minutes=5, id="collect_news_job", replace_existing=True)
    scheduler.start()
    logger.info("APScheduler worker started (5-minute continuous cycle).")

    # Run immediate initial scrape for the default ticker in background
    asyncio.create_task(scrape_ticker_task(CURRENT_ACTIVE_TICKER))

    yield

    # Shutdown
    logger.info("Shutting down APScheduler...")
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Collect - Financial News & Rumors Radar",
    description="Real-time news and rumors aggregator for Italian and US stocks with automatic Italian translation",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/", response_class=HTMLResponse)
async def index_view(
    request: Request,
    ticker: Optional[str] = Query(None),
    category: Optional[str] = Query("ALL"),
    q: Optional[str] = Query(None)
):
    global CURRENT_ACTIVE_TICKER
    active_ticker = (ticker or CURRENT_ACTIVE_TICKER).strip().upper()
    CURRENT_ACTIVE_TICKER = active_ticker

    # If this ticker has no items in DB, trigger a background scrape immediately
    items = get_items(ticker=active_ticker, category=category, query=q)
    if not items:
        asyncio.create_task(scrape_ticker_task(active_ticker))

    all_active_tickers = get_active_tickers()
    if active_ticker not in all_active_tickers:
        all_active_tickers.append(active_ticker)

    stats = get_stats()

    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_ticker": active_ticker,
            "items": items,
            "active_tickers": all_active_tickers,
            "selected_category": (category or "ALL").upper(),
            "search_query": q or "",
            "stats": stats
        }
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



@app.get("/api/news")
async def api_get_news(
    ticker: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100
):
    items = get_items(ticker=ticker, category=category, query=q, limit=limit)
    return {"ticker": ticker, "count": len(items), "items": items}


@app.post("/api/scrape")
async def api_trigger_scrape(ticker: str):
    clean = ticker.strip().upper()
    asyncio.create_task(scrape_ticker_task(clean))
    return {"status": "started", "ticker": clean}


@app.post("/api/tickers/delete")
@app.delete("/api/tickers/{ticker}")
async def api_delete_ticker(ticker: str):
    clean = ticker.strip().upper()
    deleted_count = delete_ticker(clean)
    remaining = get_active_tickers()
    next_ticker = remaining[0] if remaining else "NVDA"
    return {"deleted": True, "ticker": clean, "deleted_count": deleted_count, "next_ticker": next_ticker}


@app.post("/api/items/{item_id}/delete")
@app.delete("/api/items/{item_id}")
async def api_delete_item(item_id: int):
    success = delete_item(item_id)
    return {"deleted": success, "id": item_id}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port)

