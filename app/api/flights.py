from fastapi import APIRouter, Query
from app.services.aviation_service import get_aviation_service
import logging

router = APIRouter(prefix="/api/v1/flights", tags=["aviation"])
logger = logging.getLogger(__name__)

@router.get("/live")
async def get_live_flights(
    limit: int = Query(200, ge=1, le=2000),
    type: str = Query("ALL", description="ALL / CARGO / PAX"),
    min_altitude_ft: int = Query(0, description="Min altitude filter (feet)"),
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
async def get_cargo_flights(limit: int = Query(100, ge=1, le=500)):
    """Cargo-only feed: FedEx, UPS, DHL, Cargolux etc."""
    svc = get_aviation_service()
    flights = await svc.get_flights()
    cargo = [f for f in flights if f.get("type") == "CARGO" and not f.get("on_ground")]
    return {"count": len(cargo[:limit]), "flights": cargo[:limit]}

@router.get("/stats")
async def get_flight_stats():
    """Summary statistics for the aviation intelligence panel."""
    svc = get_aviation_service()
    return await svc.get_stats()
