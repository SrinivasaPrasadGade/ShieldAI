"""
Geospatial intelligence service for ShieldAI.

Queries SQLite incidents table for filtered incidents,
heatmap data, hotspot detection, and city-level statistics.
"""

from typing import Optional
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from logging_config import get_logger
from models.database import get_sqlite_connection

logger = get_logger("shield_ai.geo")


class GeoService:
    """Geospatial intelligence queries on the incidents table."""

    def get_incidents(
        self,
        incident_type: Optional[str] = None,
        days: int = 7,
        state: Optional[str] = None,
    ) -> list:
        """
        Get filtered incidents within a time window.

        Args:
            incident_type: Optional filter (scam_call, ficn, financial_fraud)
            days: Number of days to look back
            state: Optional state filter

        Returns:
            List of incident dicts
        """
        query = "SELECT * FROM incidents WHERE 1=1"
        params: list = []

        if incident_type:
            query += " AND incident_type = ?"
            params.append(incident_type)

        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query += " AND created_at >= ?"
            params.append(cutoff.isoformat())

        if state:
            query += " AND state = ?"
            params.append(state)

        query += " ORDER BY created_at DESC LIMIT 500"

        with get_sqlite_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        incidents = [
            {
                "lat": row["lat"],
                "lng": row["lng"],
                "type": row["incident_type"],
                "severity": row["severity"],
                "city": row["city"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

        logger.info("incidents_fetched", count=len(incidents), type=incident_type, days=days)
        return incidents

    def get_heatmap(self, incident_type: Optional[str] = None) -> list:
        """
        Get heatmap data points for Leaflet.heat.

        Groups incidents by rounded coordinates and returns weighted points.

        Args:
            incident_type: Optional filter

        Returns:
            List of {lat, lng, weight} dicts
        """
        query = "SELECT lat, lng FROM incidents WHERE 1=1"
        params: list = []

        if incident_type:
            query += " AND incident_type = ?"
            params.append(incident_type)

        with get_sqlite_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        # Spatial bucketing: round to 2 decimal places (~1.1km resolution)
        buckets: dict = defaultdict(int)
        for row in rows:
            key = (round(row["lat"], 2), round(row["lng"], 2))
            buckets[key] += 1

        points = [
            {"lat": lat, "lng": lng, "weight": float(count)}
            for (lat, lng), count in buckets.items()
        ]

        logger.info("heatmap_generated", point_count=len(points))
        return points

    def get_hotspots(self, threshold: int = 5) -> list:
        """
        Detect hotspots — areas with incident concentration above threshold.

        Groups by city, calculates dominant type and risk level.

        Args:
            threshold: Minimum incidents to qualify as a hotspot

        Returns:
            List of hotspot dicts
        """
        with get_sqlite_connection() as conn:
            rows = conn.execute(
                """SELECT city, AVG(lat) as avg_lat, AVG(lng) as avg_lng,
                          COUNT(*) as incident_count,
                          MAX(lat) - MIN(lat) as lat_spread,
                          MAX(lng) - MIN(lng) as lng_spread
                   FROM incidents
                   GROUP BY city
                   HAVING incident_count >= ?
                   ORDER BY incident_count DESC""",
                (threshold,),
            ).fetchall()

            hotspots = []
            for row in rows:
                row_dict = dict(row)

                # Get dominant type for this city
                type_row = conn.execute(
                    """SELECT incident_type, COUNT(*) as cnt
                       FROM incidents WHERE city = ?
                       GROUP BY incident_type
                       ORDER BY cnt DESC LIMIT 1""",
                    (row_dict["city"],),
                ).fetchone()

                # Get severity distribution
                high_count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM incidents WHERE city = ? AND severity IN ('HIGH', 'CRITICAL')",
                    (row_dict["city"],),
                ).fetchone()["cnt"]

                incident_count = row_dict["incident_count"]
                high_ratio = high_count / incident_count if incident_count > 0 else 0

                # Calculate radius from coordinate spread (approximate km)
                lat_spread = row_dict.get("lat_spread", 0) or 0
                lng_spread = row_dict.get("lng_spread", 0) or 0
                radius = max(1.0, ((lat_spread + lng_spread) / 2) * 111)  # ~111km per degree

                hotspots.append({
                    "lat": row_dict["avg_lat"],
                    "lng": row_dict["avg_lng"],
                    "radius": round(radius, 2),
                    "incident_count": incident_count,
                    "dominant_type": type_row["incident_type"] if type_row else "unknown",
                    "risk_level": "HIGH" if high_ratio >= 0.5 else "MEDIUM" if high_ratio >= 0.3 else "LOW",
                })

        logger.info("hotspots_detected", count=len(hotspots), threshold=threshold)
        return hotspots

    def get_city_stats(self) -> list:
        """
        Get per-city aggregated statistics.

        Returns:
            List of city stat dicts
        """
        with get_sqlite_connection() as conn:
            rows = conn.execute(
                """SELECT city,
                          AVG(lat) as lat, AVG(lng) as lng,
                          COUNT(*) as total_incidents,
                          SUM(CASE WHEN severity IN ('HIGH', 'CRITICAL') THEN 1 ELSE 0 END) as high_risk_count
                   FROM incidents
                   GROUP BY city
                   ORDER BY total_incidents DESC"""
            ).fetchall()

        cities = [
            {
                "name": row["city"],
                "lat": row["lat"],
                "lng": row["lng"],
                "total_incidents": row["total_incidents"],
                "high_risk_count": row["high_risk_count"],
            }
            for row in rows
        ]

        logger.info("city_stats_fetched", city_count=len(cities))
        return cities


# Module-level singleton
_geo_service: GeoService | None = None


def get_geo_service() -> GeoService:
    """Get the GeoService singleton."""
    global _geo_service
    if _geo_service is None:
        _geo_service = GeoService()
    return _geo_service
