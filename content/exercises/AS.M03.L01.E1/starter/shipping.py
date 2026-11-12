"""A shipping-quote API. The carrier SDK is sync-only and blocks while it waits on the network."""
import asyncio
import time

from fastapi import FastAPI, HTTPException

app = FastAPI()

RATES = {"DE": 12, "IR": 30, "US": 25}


def carrier_quote(country: str) -> int | None:
    """Blocking call into the carrier's sync SDK (the tests replace it with a fake)."""
    time.sleep(0.2)
    return RATES.get(country)


async def exchange_rate(currency: str) -> float:
    """An async call to the exchange-rate service (already async: keep awaiting it)."""
    await asyncio.sleep(0.01)
    return {"EUR": 1.0, "USD": 1.1}[currency]


@app.get("/quote/{country}")
async def quote(country: str):
    """Shipping price in EUR for a country; 404 if the carrier doesn't ship there."""
    price = carrier_quote(country)
    if price is None:
        raise HTTPException(status_code=404, detail="no service")
    return {"country": country, "eur": price}


@app.get("/quote/{country}/{currency}")
async def quote_in(country: str, currency: str):
    """Shipping price converted to EUR or USD; 404 if the carrier doesn't ship there."""
    price = carrier_quote(country)
    if price is None:
        raise HTTPException(status_code=404, detail="no service")
    rate = await exchange_rate(currency)
    return {"country": country, currency.lower(): round(price * rate, 2)}
