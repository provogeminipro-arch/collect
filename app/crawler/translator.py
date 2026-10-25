import re
import logging
from typing import Dict
from deep_translator import MyMemoryTranslator

logger = logging.getLogger(__name__)

# Cache for already translated titles/snippets in this session
_TRANSLATION_CACHE: Dict[str, str] = {}

ITALIAN_MARKERS = {
    "il", "la", "lo", "i", "gli", "le", "un", "una", "uno",
    "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "del", "dello", "della", "dei", "degli", "delle",
    "al", "allo", "alla", "ai", "agli", "alle",
    "nel", "nello", "nella", "nei", "negli", "nelle",
    "è", "sono", "ha", "hanno", "titolo", "azioni", "borsa",
    "trimestrale", "utili", "ricavi", "società", "mercato", "prezzo",
    "notizie", "oggi", "quotazioni", "chiude", "sale", "scende"
}


def is_already_italian(text: str) -> bool:
    if not text:
        return True
    words = re.findall(r"\b[a-zàèéìòùA-ZÀÈÉÌÒÙ]+\b", text.lower())
    if not words:
        return True
    italian_count = sum(1 for w in words if w in ITALIAN_MARKERS)
    ratio = italian_count / max(len(words), 1)
    # If more than 10% of words are Italian markers, consider it Italian
    return ratio >= 0.10


def translate_to_italian(text: str) -> str:
    if not text or not text.strip():
        return ""

    clean_text = text.strip()

    # If already cached
    if clean_text in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[clean_text]

    # If already recognized as Italian
    if is_already_italian(clean_text):
        _TRANSLATION_CACHE[clean_text] = clean_text
        return clean_text

    # Max length for MyMemory is ~450 chars per request
    truncated = clean_text[:450]

    try:
        translated = MyMemoryTranslator(source="english", target="italian").translate(truncated)
        # Check if response is valid and not an API error banner
        if translated and not translated.startswith("MYMEMORY WARNING:") and "IS AN INVALID SOURCE" not in translated:
            _TRANSLATION_CACHE[clean_text] = translated
            return translated
    except Exception as e:
        logger.warning(f"Translation failed for '{clean_text[:40]}...': {e}")

    # Fallback to original text if translation failed or returned warning
    return clean_text
