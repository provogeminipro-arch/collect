import re
from typing import Tuple

RUMOR_KEYWORDS = {
    # Italian
    "rumor", "rumors", "voci", "voce", "indiscrezioni", "indiscrezione",
    "secondo fonti", "fonti vicine", "si parla di", "ipotesi", "trattative",
    "trattativa", "opa", "acquisizione", "fusione", "m&a", "retroscena",
    "spifferi", "speculazione", "delisting", "possibile accordo", "cessione",
    # English
    "rumour", "rumours", "speculation", "sources say", "sources tell",
    "reportedly", "talks", "takeover", "buyout", "leak", "leaked", "whisper",
    "unconfirmed", "insider", "potential deal", "bid", "secret talks"
}

ANALYSIS_KEYWORDS = {
    "target price", "prezzo obiettivo", "consensus", "upgrade", "downgrade",
    "rating", "outperform", "underperform", "buy", "sell", "hold", "analisi tecnica",
    "report", "prospettive", "valutazione", "guidance"
}

FORUM_KEYWORDS = {
    "forum", "discussione", "commenti", "thread", "utenti", "fol",
    "finanzaonline", "reddit", "wallstreetbets", "stocktwits", "parere"
}

POSITIVE_WORDS = {
    "vola", "balzo", "record", "utile", "utili", "cresce", "crescita", "rialzo",
    "rally", "surge", "gain", "gains", "jump", "jumped", "beat", "beats",
    "profit", "profits", "dividendo", "ricavi", "maxi", "accordo", "boom",
    "ottimismo", "supera", "promosso", "successo", "rialzista", "bullish"
}

NEGATIVE_WORDS = {
    "crollo", "tonfo", "scende", "calo", "perdita", "perdite", "ribasso",
    "slump", "drop", "plunge", "tumble", "miss", "misses", "loss", "losses",
    "warning", "profit warning", "taglio", "sanzione", "indagine", "inchiesta",
    "debito", "rischio", "bocciato", "sfida", "pessimismo", "ribassista", "bearish"
}


def analyze_article(title: str, summary: str = "", source_name: str = "") -> Tuple[bool, str, str]:
    """
    Returns:
        (is_rumor: bool, source_type: str, sentiment: str)
    """
    combined_text = f"{title} {summary} {source_name}".lower()
    
    # 1. Rumor detection
    is_rumor = False
    for kw in RUMOR_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", combined_text):
            is_rumor = True
            break

    # 2. Source type classification
    source_type = "news"
    lower_source = source_name.lower()
    if any(fw in lower_source or fw in combined_text for fw in FORUM_KEYWORDS):
        source_type = "forum"
    elif is_rumor:
        source_type = "rumor"
    elif any(ak in combined_text for ak in ANALYSIS_KEYWORDS):
        source_type = "analisi"

    # 3. Sentiment scoring
    pos_score = 0
    neg_score = 0
    for pw in POSITIVE_WORDS:
        if re.search(r"\b" + re.escape(pw) + r"\b", combined_text):
            pos_score += 1
    for nw in NEGATIVE_WORDS:
        if re.search(r"\b" + re.escape(nw) + r"\b", combined_text):
            neg_score += 1

    if pos_score > neg_score:
        sentiment = "positivo"
    elif neg_score > pos_score:
        sentiment = "negativo"
    else:
        sentiment = "neutro"

    return is_rumor, source_type, sentiment
