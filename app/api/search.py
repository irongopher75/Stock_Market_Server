from fastapi import APIRouter, Query, Depends, Request
from app.db import models
from app.core import auth
from app.core.limiter import limiter
import requests
import logging
from typing import List, Dict

router = APIRouter(prefix="/api/v1/search", tags=["Search"])
logger = logging.getLogger(__name__)

@router.get("")
@limiter.limit("30/minute")
async def search_symbols(
    request: Request,
    q: str = Query(..., min_length=1),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Proxy search requests to Yahoo Finance to discover symbols globally.
    Returns normalized objects for the frontend search-suggest UI.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={q}"
        
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("quotes", []):
            # Only include stocks and indices for now
            if item.get("quoteType") not in ["EQUITY", "INDEX", "ETF", "CURRENCY", "CRYPTOCURRENCY"]:
                continue
                
            results.append({
                "symbol": item.get("symbol"),
                "name": item.get("shortname") or item.get("longname"),
                "exchange": item.get("exchange"),
                "type": item.get("quoteType"),
                "typeDisp": item.get("typeDisp"),
            })
            
        return results
        
    except Exception as e:
        logger.error(f"Search API error for query '{q}': {e}")
        return {"error": "Failed to fetch search results", "details": str(e)}
