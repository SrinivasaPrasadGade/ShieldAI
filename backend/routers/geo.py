"""
Geospatial API router for ShieldAI.

Endpoints:
  GET /api/geo/incidents   — Filtered incident list
  GET /api/geo/heatmap     — Heatmap data points
  GET /api/geo/hotspots    — Detected hotspots
  GET /api/geo/city-stats  — Per-city statistics
"""

from typing import Optional

from fastapi import APIRouter, Query

from models.schemas import (
    GeoIncidentsResponse,
    HeatmapResponse,
    HotspotsResponse,
    CityStatsResponse,
)
from services.geo_service import get_geo_service
from logging_config import get_logger

logger = get_logger("shield_ai.router.geo")

router = APIRouter(prefix="/api/geo", tags=["Geospatial Intelligence"])


@router.get("/incidents", response_model=GeoIncidentsResponse)
async def get_incidents(
    type: Optional[str] = Query(None, description="Filter by type: scam_call, ficn, financial_fraud"),
    days: int = Query(7, ge=1, le=365, description="Days to look back"),
    state: Optional[str] = Query(None, description="Filter by state"),
):
    """
    Get geospatial incidents filtered by type, time window, and state.
    Returns up to 500 incidents ordered by creation time (newest first).
    """
    if type and type not in ("scam_call", "ficn", "financial_fraud"):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Type must be scam_call, ficn, or financial_fraud")

    service = get_geo_service()
    incidents = service.get_incidents(incident_type=type, days=days, state=state)
    return {"incidents": incidents}


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    type: Optional[str] = Query(None, description="Filter by incident type"),
):
    """
    Get heatmap data points for Leaflet.heat visualization.

    Returns weighted lat/lng points bucketed at ~1.1km resolution.
    Weight represents incident count at each location.
    """
    service = get_geo_service()
    points = service.get_heatmap(incident_type=type)
    return {"points": points}


@router.get("/hotspots", response_model=HotspotsResponse)
async def get_hotspots(
    threshold: int = Query(5, ge=1, le=100, description="Minimum incidents to qualify as hotspot"),
):
    """
    Detect crime hotspots — areas with incident concentration above threshold.

    Returns hotspots with location, radius, incident count, dominant crime type,
    and computed risk level.
    """
    service = get_geo_service()
    hotspots = service.get_hotspots(threshold=threshold)
    return {"hotspots": hotspots}


@router.get("/city-stats", response_model=CityStatsResponse)
async def get_city_stats():
    """
    Get per-city aggregated crime statistics.
    Includes total incidents and high-risk count for each city.
    """
    service = get_geo_service()
    cities = service.get_city_stats()
    return {"cities": cities}
