"""Resolve city names to coordinates with a blocking geocoding client (reference solution)."""
import asyncio
from typing import Callable

Coords = tuple[float, float]


async def locate_all(cities: list[str], geocode: Callable[[str], Coords]) -> dict[str, Coords]:
    """Return {city: geocode(city)} for each distinct city, geocoding in a worker thread."""
    result: dict[str, Coords] = {}
    for city in cities:
        if city not in result:
            result[city] = await asyncio.to_thread(geocode, city)
    return result
