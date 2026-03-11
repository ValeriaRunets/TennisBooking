"""Geocoding via postcodes.io and distance calculations."""

from __future__ import annotations

import logging
import math

import aiohttp

logger = logging.getLogger(__name__)

_POSTCODES_API = "https://api.postcodes.io"


async def geocode_postcode(postcode: str) -> tuple[float, float] | None:
    """Geocode a single UK postcode. Returns (lat, lon) or None on failure."""
    url = f"{_POSTCODES_API}/postcodes/{postcode.replace(' ', '')}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.warning("postcodes.io returned %d for %s", resp.status, postcode)
                return None
            data = await resp.json()
            result = data.get("result")
            if not result:
                return None
            return (result["latitude"], result["longitude"])


async def bulk_geocode(postcodes: list[str]) -> dict[str, tuple[float, float]]:
    """Bulk geocode postcodes. Returns {postcode: (lat, lon)} for successful lookups."""
    if not postcodes:
        return {}

    # postcodes.io bulk endpoint accepts max 100 at a time
    results: dict[str, tuple[float, float]] = {}
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(postcodes), 100):
            batch = postcodes[i : i + 100]
            async with session.post(
                f"{_POSTCODES_API}/postcodes",
                json={"postcodes": batch},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    logger.warning("Bulk geocode failed with status %d", resp.status)
                    continue
                data = await resp.json()
                for item in data.get("result", []):
                    if item.get("result"):
                        r = item["result"]
                        results[r["postcode"]] = (r["latitude"], r["longitude"])
    return results


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km using the Haversine formula."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest(
    user_coords: tuple[float, float],
    venues: list[dict],
    n: int = 10,
) -> list[dict]:
    """Sort venues by distance from user_coords and return the nearest n.

    Each venue dict must have 'lat' and 'lon' keys.
    Returns venue dicts with an added 'distance_km' key.
    """
    scored = []
    for v in venues:
        if v.get("lat") is None or v.get("lon") is None:
            continue
        dist = haversine_distance(user_coords[0], user_coords[1], v["lat"], v["lon"])
        scored.append({**v, "distance_km": round(dist, 1)})

    scored.sort(key=lambda x: x["distance_km"])
    return scored[:n]
