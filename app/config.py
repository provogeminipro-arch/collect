import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = os.getenv("COLLECT_DB_PATH", str(DATA_DIR / "collect.db"))

DEFAULT_CRAWL_INTERVAL_MINUTES = 10
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

INITIAL_TICKERS = [
    {"symbol": "RACE.MI", "name": "Ferrari N.V.", "market": "Borsa Italiana"},
    {"symbol": "ENI.MI", "name": "Eni S.p.A.", "market": "Borsa Italiana"},
    {"symbol": "UCG.MI", "name": "UniCredit S.p.A.", "market": "Borsa Italiana"},
    {"symbol": "STM.MI", "name": "STMicroelectronics", "market": "Borsa Italiana"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "market": "US - NASDAQ"},
    {"symbol": "AAPL", "name": "Apple Inc.", "market": "US - NASDAQ"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "market": "US - NASDAQ"},
]
