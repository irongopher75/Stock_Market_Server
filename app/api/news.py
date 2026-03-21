from fastapi import APIRouter, Query, Depends, Request
from app.db import models
from app.core import auth
from app.core.limiter import limiter
from app.services.news_service import news_service
import logging

router = APIRouter(prefix="/api/v1/news", tags=["news"])
logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"ALL", "VESSEL", "AVIATION", "GEOPOLITICS", "COMMODITY", "CRYPTO", "MACRO", "EQUITY", "GEO", "GENERAL"}

@router.get("/feed")
@limiter.limit("20/minute")
async def get_news_feed(
    request: Request,
    category: str = Query("ALL", description="Filter by category"),
    limit: int = Query(40, ge=1, le=100),
    severity: str = Query("ALL", description="Filter: ALL / RED / AMBER / GREEN"),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Returns real, ranked, categorized news from Finnhub and GDELT.
    Sorted by severity score (highest first), then recency.
    """
    try:
        articles = await news_service.get_feed(limit=100)

        if category != "ALL" and category.upper() in VALID_CATEGORIES:
            articles = [a for a in articles if a.get("category") == category.upper()]

        if severity != "ALL" and severity.upper() in {"RED", "AMBER", "GREEN"}:
            articles = [a for a in articles if a.get("severity") == severity.upper()]

        return {
            "count": len(articles[:limit]),
            "articles": articles[:limit],
            "cached": True,
        }
    except Exception as e:
        logger.error(f"News feed error: {e}")
        return {
            "count": 0,
            "articles": [],
            "error": str(e),
            "cached": False
        }

@router.post("/refresh")
@limiter.limit("5/minute")
async def force_refresh(
    request: Request,
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Force refresh the news cache."""
    news_service._last_update = 0
    articles = await news_service.get_feed()
    return {"refreshed": True, "count": len(articles)}
