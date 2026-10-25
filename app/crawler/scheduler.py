import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from app.database import get_setting, get_tickers
from app.crawler.collector import crawl_all_active_tickers, crawl_ticker

logger = logging.getLogger(__name__)


class BackgroundCrawlerScheduler:
    def __init__(self):
        self.is_running = False
        self.is_crawling = False
        self.current_ticker_crawling: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.on_new_item_cb: Optional[Callable[[Dict[str, Any]], Any]] = None
        self.on_status_change_cb: Optional[Callable[[Dict[str, Any]], Any]] = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Background crawler scheduler started.")

    def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Background crawler scheduler stopped.")

    async def notify_status(self, status: str, details: Optional[Dict[str, Any]] = None):
        if self.on_status_change_cb:
            try:
                payload = {
                    "type": "crawler_status",
                    "status": status,
                    "is_crawling": self.is_crawling,
                    "ticker": self.current_ticker_crawling,
                    "details": details or {}
                }
                if asyncio.iscoroutinefunction(self.on_status_change_cb):
                    await self.on_status_change_cb(payload)
                else:
                    self.on_status_change_cb(payload)
            except Exception as e:
                logger.warning(f"Error in crawler status notification callback: {e}")

    async def trigger_manual_crawl(self, ticker_symbol: Optional[str] = None) -> Dict[str, Any]:
        async with self._lock:
            self.is_crawling = True
            try:
                if ticker_symbol:
                    self.current_ticker_crawling = ticker_symbol.upper()
                    await self.notify_status("crawling", {"ticker": self.current_ticker_crawling})
                    all_tickers = get_tickers()
                    match = next((t for t in all_tickers if t["symbol"].upper() == ticker_symbol.upper()), None)
                    if not match:
                        match = {"symbol": ticker_symbol.upper(), "name": ticker_symbol.upper(), "market": "Auto"}
                    result = await crawl_ticker(match, on_new_item=self.on_new_item_cb)
                    return {"success": True, "results": [result]}
                else:
                    self.current_ticker_crawling = "ALL"
                    await self.notify_status("crawling", {"ticker": "ALL"})
                    results = await crawl_all_active_tickers(on_new_item=self.on_new_item_cb)
                    return {"success": True, "results": results}
            finally:
                self.is_crawling = False
                self.current_ticker_crawling = None
                await self.notify_status("idle")

    async def _run_loop(self):
        # Initial short pause on startup before first check
        await asyncio.sleep(5)

        while self.is_running:
            try:
                auto_enabled = get_setting("auto_crawl_enabled", "true").lower() == "true"
                interval_minutes = int(get_setting("crawl_interval_minutes", "10"))

                if auto_enabled:
                    logger.info("Executing scheduled crawl cycle...")
                    async with self._lock:
                        self.is_crawling = True
                        self.current_ticker_crawling = "ALL"
                        await self.notify_status("crawling", {"ticker": "ALL"})
                        try:
                            await crawl_all_active_tickers(on_new_item=self.on_new_item_cb)
                        except Exception as e:
                            logger.error(f"Error during scheduled crawl: {e}")
                        finally:
                            self.is_crawling = False
                            self.current_ticker_crawling = None
                            await self.notify_status("idle")

                # Sleep in increments of 5 seconds to respond quickly to shutdown or changes
                wait_seconds = max(interval_minutes * 60, 30)
                for _ in range(wait_seconds // 5):
                    if not self.is_running:
                        break
                    await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in background crawler loop: {e}")
                await asyncio.sleep(15)


crawler_scheduler = BackgroundCrawlerScheduler()
