import re
import logging
from typing import Dict
from deep_translator import GoogleTranslator, MyMemoryTranslator

logger = logging.getLogger(__name__)

# In-memory translation cache to optimize speed and API calls
_CACHE: Dict[str, str] = {}

ITALIAN_INDICATORS = {
    "il", "lo", "la", "i", "gli", "le", "un", "una", "uno",
    "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "del", "dello", "della", "dei", "degli", "delle",
    "è", "sono", "ha", "hanno", "titolo", "azioni", "borsa",
    "trimestrale", "utili", "ricavi", "società", "mercato",
    "prezzo", "notizie", "oggi", "quotazioni", "sale", "scende"
}


def is_italian(text: str) -> bool:
    if not text:
        return True
    tokens = re.findall(r"\b[a-zA-ZàèéìòùÀÈÉÌÒÙ]+\b", text.lower())
    if not tokens:
        return True
    matches = sum(1 for t in tokens if t in ITALIAN_INDICATORS)
    # If >= 10% of tokens are Italian indicators, assume Italian
    return (matches / max(len(tokens), 1)) >= 0.10


def translate_text(text: str) -> str:
    """
    Translates text to Italian using deep-translator (GoogleTranslator).
    Includes in-memory cache and resilient fallback if Google blocks requests.
    """
    if not text or not text.strip():
        return ""

    cleaned = text.strip()

    if cleaned in _CACHE:
        return _CACHE[cleaned]

    if is_italian(cleaned):
        _CACHE[cleaned] = cleaned
        return cleaned

    # Truncate to reasonable snippet if very long
    snippet = cleaned[:500]

    # Primary method: GoogleTranslator from deep-translator as specified
    try:
        translated = GoogleTranslator(source="auto", target="it").translate(snippet)
        if translated and translated.strip():
            _CACHE[cleaned] = translated.strip()
            return translated.strip()
    except Exception as e:
        logger.debug(f"GoogleTranslator primary error ({e}), trying fallback provider...")

    # Secondary fallback: MyMemoryTranslator
    try:
        translated = MyMemoryTranslator(source="english", target="italian").translate(snippet[:400])
        if translated and not translated.startswith("MYMEMORY WARNING:") and "INVALID" not in translated:
            _CACHE[cleaned] = translated.strip()
            return translated.strip()
    except Exception as e:
        logger.debug(f"Fallback translation error: {e}")

    # Return original text if translation service is unavailable
    return cleaned
