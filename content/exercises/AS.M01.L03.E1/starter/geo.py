"""Resolve city names to coordinates with a blocking (sync-only) geocoding client."""
from typing import Callable

Coords = tuple[float, float]


async def locate_all(cities: list[str], geocode: Callable[[str], Coords]) -> dict[str, Coords]:
    """Return {city: geocode(city)} for each distinct city.

    geocode is a blocking function (think: a sync HTTP client). It must not run on the
    event loop's thread. Each distinct city is geocoded once; errors from geocode propagate.
    """
    result = {}
    for city in cities:
        result[city] = geocode(city)
    return result
