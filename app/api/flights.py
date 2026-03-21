from fastapi import APIRouter, Query, Depends, Request
from app.db import models
from app.core import auth
from app.core.limiter import limiter
from app.services.aviation_service import get_aviation_service
import logging

router = APIRouter(prefix="/api/v1/flights", tags=["aviation"])
logger = logging.getLogger(__name__)

@router.get("/live")
@limiter.limit("20/minute")
async def get_live_flights(
    request: Request,
    limit: int = Query(200, ge=1, le=2000),
    type: str = Query("ALL", description="ALL / CARGO / PAX"),
    min_altitude_ft: int = Query(0, description="Min altitude filter (feet)"),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Returns live flights from FlightRadar24 (unofficial SDK, no key required).
    Cached for 30 seconds between polls.
    """
    svc = get_aviation_service()
    flights = await svc.get_flights()

    # Filters
    if type != "ALL":
        flights = [f for f in flights if f.get("type") == type.upper()]
    if min_altitude_ft > 0:
        flights = [f for f in flights if f.get("altitude_ft", 0) >= min_altitude_ft]

    # Exclude ground traffic
    flights = [f for f in flights if not f.get("on_ground")]

    return {
        "count": len(flights[:limit]),
        "flights": flights[:limit],
        "source": svc._source,
    }

@router.get("/cargo")
@limiter.limit("20/minute")
async def get_cargo_flights(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Cargo-only feed: FedEx, UPS, DHL, Cargolux etc."""
    svc = get_aviation_service()
    flights = await svc.get_flights()
    cargo = [f for f in flights if f.get("type") == "CARGO" and not f.get("on_ground")]
    return {"count": len(cargo[:limit]), "flights": cargo[:limit]}

@router.get("/stats")
@limiter.limit("10/minute")
async def get_flight_stats(
    request: Request,
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """Summary statistics for the aviation intelligence panel."""
    svc = get_aviation_service()
    return await svc.get_stats()
