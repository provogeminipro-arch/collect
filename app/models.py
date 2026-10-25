from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TickerCreate(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol, e.g. RACE.MI, ENI.MI, AAPL, NVDA")
    name: str = Field(..., description="Company name, e.g. Ferrari N.V., Apple Inc.")
    market: Optional[str] = Field(None, description="Market, e.g. Borsa Italiana or US")


class TickerToggle(BaseModel):
    active: bool


class SettingsUpdate(BaseModel):
    crawl_interval_minutes: int = Field(..., ge=1, le=1440)
    auto_crawl_enabled: bool


class ManualCrawlRequest(BaseModel):
    ticker: Optional[str] = None
