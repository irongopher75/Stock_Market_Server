"""
News Intelligence Service
Multi-source scraper: Finnhub News + GDELT
Ranks, deduplicates, and categorizes articles.
"""
import asyncio
import httpx
import os
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

load_dotenv()
logger = logging.getLogger(__name__)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

# ─── RANKING WEIGHTS ──────────────────────────────────────────────────────────
# Each keyword hit adds to the article's severity score (0–100)
SEVERITY_KEYWORDS = {
    # Critical (20 pts each)
    "crash": 20, "collapse": 20, "default": 20, "sanctions": 20,
    "war": 20, "invasion": 20, "nuclear": 20, "crisis": 20,
    # High (12 pts each)
    "recession": 12, "inflation": 12, "rate hike": 12, "rate cut": 12,
    "plunge": 12, "surge": 12, "record high": 12, "record low": 12,
    "bankruptcy": 12, "fed": 10, "fomc": 10, "rbi": 10,
    # Medium (6 pts each)
    "earnings": 6, "guidance": 6, "merger": 6, "acquisition": 6,
    "layoffs": 6, "strike": 6, "supply chain": 6, "shortage": 6,
    "rally": 6, "selloff": 6, "downgrade": 6, "upgrade": 6,
    # Low (2 pts each)
    "market": 2, "stock": 2, "shares": 2, "trade": 2,
}

# ─── CATEGORY RULES ───────────────────────────────────────────────────────────
CATEGORY_RULES = [
    ("VESSEL",     r"\b(vessel|ship|tanker|lng|suez|hormuz|ais|cargo ship|maritime|fleet)\b"),
    ("AVIATION",   r"\b(flight|aircraft|airline|airport|boeing|airbus|cargo jet|ads-b)\b"),
    ("GEOPOLITICS",r"\b(war|sanctions|ceasefire|invasion|nato|conflict|treaty|geopolit)\b"),
    ("COMMODITY",  r"\b(crude|oil|gold|silver|wheat|corn|gas|copper|commodity|brent|wti)\b"),
    ("CRYPTO",     r"\b(bitcoin|ethereum|crypto|blockchain|defi|nft|btc|eth|binance|coinbase)\b"),
    ("MACRO",      r"\b(fed|fomc|central bank|interest rate|inflation|gdp|cpi|ppi|ecb|rbi|boe)\b"),
    ("EQUITY",     r"\b(stock|shares|ipo|earnings|nasdaq|s&p|nifty|sensex|nse|bse|equit)\b"),
    ("GEO",        r"\b(port|congestion|shipping lane|chokepoint|malacca|bosphorus|panama)\b"),
]

SENTIMENT_BULL = {"surge", "rally", "upgrade", "beat", "record high", "strong", "growth", "up"}
SENTIMENT_BEAR = {"crash", "plunge", "collapse", "downgrade", "miss", "record low", "weak", "layoffs", "default"}


from textblob import TextBlob

def _classify(text: str) -> Dict:
    """Returns category, severity (0-100), sentiment, and color for a news headline+summary."""
    lower = text.lower()
    blob = TextBlob(text)
    sentiment_score = blob.sentiment.polarity # -1.0 to 1.0

    # Category
    category = "GENERAL"
    for cat, pattern in CATEGORY_RULES:
        if re.search(pattern, lower):
            category = cat
            break

    # Severity
    score = 0
    for kw, pts in SEVERITY_KEYWORDS.items():
        if kw in lower:
            score += pts
    severity_score = min(score, 100)

    # Label (RED/AMBER/GREEN)
    if severity_score >= 20:
        severity = "RED"
    elif severity_score >= 10:
        severity = "AMBER"
    else:
        severity = "GREEN"

    # Sentiment Mapping
    if sentiment_score > 0.1:
        sentiment = "BULLISH"
        sentiment_color = "#00FF41" # Neon Green
    elif sentiment_score < -0.1:
        sentiment = "BEARISH"
        sentiment_color = "#FF2244" # Neon Red
    else:
        sentiment = "NEUTRAL"
        sentiment_color = "#FFCC00" # Neon Amber/Yellow

    return {
        "category": category, 
        "severity": severity, 
        "severity_score": severity_score, 
        "sentiment": sentiment,
        "sentiment_score": round(sentiment_score, 2),
        "sentiment_color": sentiment_color
    }


class NewsIntelligenceService:
    def __init__(self):
        self._cache: List[Dict] = []
        self._last_update: float = 0
        self._ttl: int = 300  # refresh every 5 minutes

    async def get_feed(self, limit: int = 40) -> List[Dict]:
        now = datetime.now(timezone.utc).timestamp()
        if now - self._last_update > self._ttl or not self._cache:
            await self._refresh()
        return self._cache[:limit]

    async def _refresh(self):
        logger.info("Refreshing news intelligence feed...")
        # Fetch all sources in PARALLEL — reduces cold-start from ~45s to ~8s
        async with httpx.AsyncClient(timeout=8) as client:
            finnhub, gdelt = await asyncio.gather(
                self._fetch_finnhub(client),
                self._fetch_gdelt(client),
                return_exceptions=False
            )
        articles = finnhub + gdelt

        # Classify, deduplicate, rank
        seen_titles = set()
        ranked = []
        for a in articles:
            title_key = a["headline"][:60].lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            classification = _classify(f"{a['headline']} {a.get('summary', '')}")
            ranked.append({
                **a,
                **classification,
            })

        # Sort: by severity_score DESC, then recency
        ranked.sort(key=lambda x: (x["severity_score"], x["published_at"]), reverse=True)

        # Translate all the scraped news in English only
        async def translate_article(a: Dict):
            translator = GoogleTranslator(source='auto', target='en')
            try:
                if a.get("headline"):
                    a["headline"] = await asyncio.to_thread(translator.translate, a["headline"])
                if a.get("summary"):
                    a["summary"] = await asyncio.to_thread(translator.translate, a["summary"])
            except Exception as e:
                logger.warning(f"Translation failed for {a.get('headline', '')[:20]}: {e}")
            return a

        # Translate top articles concurrently (limiting to 60 to avoid Google API rate limits on massive lists)
        translated_ranked = await asyncio.gather(*(translate_article(a) for a in ranked[:60]))
        ranked[:60] = translated_ranked

        self._cache = ranked
        self._last_update = datetime.now(timezone.utc).timestamp()
        logger.info(f"News feed refreshed: {len(ranked)} articles")

    async def _fetch_finnhub(self, client: httpx.AsyncClient) -> List[Dict]:
        results = []
        try:
            # General market news
            resp = await client.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "general", "token": FINNHUB_KEY}
            )
            try:
                items = resp.json() if resp.status_code == 200 else []
            except Exception:
                items = []

            # Also grab crypto news
            resp2 = await client.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "crypto", "token": FINNHUB_KEY}
            )
            try:
                crypto_items = resp2.json() if resp2.status_code == 200 else []
                items += crypto_items
            except Exception:
                pass

            for item in items[:60]:
                ts = item.get("datetime", 0)
                results.append({
                    "headline": item.get("headline", ""),
                    "summary": item.get("summary", ""),
                    "source": item.get("source", "Finnhub"),
                    "url": item.get("url", ""),
                    "published_at": ts,
                    "published_fmt": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M") if ts else "--:--",
                    "data_source": "FINNHUB",
                })
        except Exception as e:
            logger.warning(f"Finnhub news fetch failed: {e}")
        return results

    async def _fetch_gdelt(self, client: httpx.AsyncClient) -> List[Dict]:
        """Fetch all 3 GDELT queries in parallel."""
        queries = [
            "stock market financial",
            "oil crude shipping supply chain",
            "central bank interest rate inflation",
        ]

        async def _one_query(query: str) -> List[Dict]:
            try:
                resp = await client.get(
                    "https://api.gdeltproject.org/api/v2/doc/doc",
                    params={"query": query, "mode": "artlist", "maxrecords": "15", "format": "json", "sort": "DateDesc"}
                )
                if resp.status_code != 200:
                    return []
                try:
                    data = resp.json()
                except Exception:
                    logger.warning(f"GDELT returned non-JSON for '{query}'")
                    return []
                out = []
                for item in (data.get("articles") or []):
                    title = item.get("title", "").strip()
                    if not title:
                        continue
                    raw_date = item.get("seendate", "")
                    try:
                        dt = datetime.strptime(raw_date, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                        ts = int(dt.timestamp())
                        fmt = dt.strftime("%H:%M")
                    except Exception:
                        ts, fmt = 0, "--:--"
                    out.append({
                        "headline": title, "summary": "",
                        "source": item.get("domain", "GDELT"),
                        "url": item.get("url", ""),
                        "published_at": ts, "published_fmt": fmt,
                        "data_source": "GDELT",
                    })
                return out
            except Exception as e:
                logger.warning(f"GDELT fetch failed for '{query}': {e}")
                return []

        batches = await asyncio.gather(*[_one_query(q) for q in queries])
        return [item for batch in batches for item in batch]


# Singleton
news_service = NewsIntelligenceService()
