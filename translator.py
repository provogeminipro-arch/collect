import re
import urllib.parse
import logging
from typing import Dict
from curl_cffi import requests
from deep_translator import GoogleTranslator, MyMemoryTranslator

logger = logging.getLogger(__name__)

# In-memory translation cache
_CACHE: Dict[str, str] = {}

# Strong Italian indicators (words that DO NOT exist in English)
DISTINCT_ITALIAN_WORDS = {
    "delle", "degli", "della", "dello", "degli", "sono",
    "nella", "nelle", "nello", "nei", "agli", "alle", "allo",
    "perché", "perche", "perche'", "trimestrale", "utili", "ricavi",
    "società", "societa", "quotazione", "quotazioni", "rialzo", "ribasso",
    "borsa", "piazza", "affari", "chiusura", "fatturato", "cedola",
    "dividendi", "dividendo", "governo", "titolo", "notizie"
}

# Strong English indicators
ENGLISH_WORDS = {
    "the", "is", "are", "was", "were", "this", "that", "with",
    "from", "for", "stock", "stocks", "shares", "buy", "sell",
    "why", "what", "how", "after", "before", "earnings", "market",
    "markets", "quarter", "report", "reports", "growth", "revenue",
    "price", "target", "analyst", "analysts", "investors", "wall",
    "street", "new", "will", "could", "may", "here", "today",
    "billion", "million", "shares", "dividend", "yield", "rate"
}


def is_already_italian(text: str) -> bool:
    if not text:
        return True
    tokens = set(re.findall(r"\b[a-zA-ZàèéìòùÀÈÉÌÒÙ']+\b", text.lower()))
    if not tokens:
        return True

    # If any strong English words appear, it is NOT Italian!
    if tokens & ENGLISH_WORDS:
        return False

    # If it contains distinctive Italian words
    if tokens & DISTINCT_ITALIAN_WORDS:
        return True

    # Default: if unsure, do not assume Italian, let the translator handle it
    return False


def translate_text(text: str) -> str:
    """
    Translates text to Italian using Google Translate (gtx via curl_cffi & deep-translator).
    Always ensures English and foreign headlines are translated into Italian.
    """
    if not text or not text.strip():
        return ""

    cleaned = text.strip()

    if cleaned in _CACHE:
        return _CACHE[cleaned]

    if is_already_italian(cleaned):
        _CACHE[cleaned] = cleaned
        return cleaned

    # Truncate to reasonable size
    snippet = cleaned[:500]

    # Provider 1: Direct Google gtx via curl_cffi (Fastest, zero captcha, no 429)
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=it&dt=t&q={urllib.parse.quote(snippet)}"
        res = requests.get(url, impersonate="chrome120", timeout=6)
        if res.status_code == 200:
            data = res.json()
            translated = "".join([part[0] for part in data[0] if part and part[0]])
            if translated and translated.strip():
                _CACHE[cleaned] = translated.strip()
                return translated.strip()
    except Exception as e:
        logger.debug(f"Direct gtx translation error: {e}")

    # Provider 2: deep-translator GoogleTranslator
    try:
        translated = GoogleTranslator(source="auto", target="it").translate(snippet)
        if translated and translated.strip():
            _CACHE[cleaned] = translated.strip()
            return translated.strip()
    except Exception as e:
        logger.debug(f"deep_translator GoogleTranslator error: {e}")

    # Provider 3: deep-translator MyMemoryTranslator
    try:
        translated = MyMemoryTranslator(source="english", target="italian").translate(snippet[:400])
        if translated and not translated.startswith("MYMEMORY WARNING:") and "INVALID" not in translated:
            _CACHE[cleaned] = translated.strip()
            return translated.strip()
    except Exception as e:
        logger.debug(f"MyMemory fallback error: {e}")

    # If all fail, return original
    return cleaned
