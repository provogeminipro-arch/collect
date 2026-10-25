import os
import json
import logging
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import BASE_DIR
from app.database import (
    init_db, get_tickers, add_ticker, remove_ticker, toggle_ticker,
    get_news, get_stats, get_setting, set_setting, get_recent_logs
)
from app.models import TickerCreate, TickerToggle, SettingsUpdate, ManualCrawlRequest
from app.crawler.scheduler import crawler_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


ws_manager = ConnectionManager()


async def on_new_news_item(item: dict):
    await ws_manager.broadcast({
        "type": "new_item",
        "item": item
    })


async def on_crawler_status(status_payload: dict):
    await ws_manager.broadcast(status_payload)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    init_db()

    # Hook up crawler callbacks
    crawler_scheduler.on_new_item_cb = on_new_news_item
    crawler_scheduler.on_status_change_cb = on_crawler_status
    crawler_scheduler.start()

    yield

    # Shutdown
    logger.info("Stopping background crawler...")
    crawler_scheduler.stop()


app = FastAPI(
    title="Collect - Stock News & Rumors Collector",
    description="Continuous web crawler, translator and real-time dashboard for Italian and US stock news & rumors",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
STATIC_DIR = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    index_file = STATIC_DIR / "index.html"
    return FileResponse(str(index_file))


# --- API Routes ---

@app.get("/api/news")
async def api_get_news(
    ticker: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    is_rumor: Optional[bool] = Query(None),
    sentiment: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    data = get_news(
        ticker=ticker,
        source_type=source_type,
        is_rumor=is_rumor,
        sentiment=sentiment,
        query=q,
        limit=limit,
        offset=offset
    )
    return data


@app.get("/api/tickers")
async def api_get_tickers(active_only: bool = False):
    return get_tickers(active_only=active_only)


@app.post("/api/tickers", status_code=status.HTTP_201_CREATED)
async def api_add_ticker(payload: TickerCreate):
    ticker_id = add_ticker(payload.symbol, payload.name, payload.market or "")
    # Trigger an immediate crawl for the newly added ticker in background
    import asyncio
    asyncio.create_task(crawler_scheduler.trigger_manual_crawl(payload.symbol))
    return {"id": ticker_id, "symbol": payload.symbol.upper(), "name": payload.name}


@app.delete("/api/tickers/{ticker_id}")
async def api_remove_ticker(ticker_id: int):
    success = remove_ticker(ticker_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return {"deleted": True}


@app.post("/api/tickers/{ticker_id}/toggle")
async def api_toggle_ticker(ticker_id: int, payload: TickerToggle):
    success = toggle_ticker(ticker_id, payload.active)
    if not success:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return {"updated": True, "active": payload.active}


@app.get("/api/stats")
async def api_get_stats():
    return get_stats()


@app.get("/api/settings")
async def api_get_settings():
    return {
        "crawl_interval_minutes": int(get_setting("crawl_interval_minutes", "10")),
        "auto_crawl_enabled": get_setting("auto_crawl_enabled", "true").lower() == "true",
        "is_crawling": crawler_scheduler.is_crawling,
        "current_ticker": crawler_scheduler.current_ticker_crawling
    }


@app.post("/api/settings")
async def api_update_settings(payload: SettingsUpdate):
    set_setting("crawl_interval_minutes", str(payload.crawl_interval_minutes))
    set_setting("auto_crawl_enabled", "true" if payload.auto_crawl_enabled else "false")
    return {"updated": True}


@app.post("/api/crawl/trigger")
async def api_trigger_crawl(payload: Optional[ManualCrawlRequest] = None):
    ticker = payload.ticker if payload else None
    if crawler_scheduler.is_crawling:
        return {"status": "already_running", "message": "Un processo di scansione è già in corso"}

    import asyncio
    asyncio.create_task(crawler_scheduler.trigger_manual_crawl(ticker))
    return {"status": "started", "message": f"Scansione avviata per {'tutti i titoli' if not ticker else ticker}"}


@app.get("/api/crawl/logs")
async def api_get_logs(limit: int = 25):
    return get_recent_logs(limit=limit)


# WebSocket endpoint for real-time live feed
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send current crawler status immediately upon connection
        await websocket.send_json({
            "type": "crawler_status",
            "is_crawling": crawler_scheduler.is_crawling,
            "ticker": crawler_scheduler.current_ticker_crawling
        })
        while True:
            # Keep connection open and receive any ping from client
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
