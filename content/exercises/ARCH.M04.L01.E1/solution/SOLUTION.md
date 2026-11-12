# Reference solution

```python
"""Back-of-the-envelope helpers for design docs."""
import math

SECONDS_PER_DAY = 86_400


def rps(requests_per_day: int, peak_factor: float) -> tuple[int, int]:
    """(average, peak) requests per second, each rounded UP to a whole number.

    peak = average * peak_factor. ValueError if requests_per_day < 0 or peak_factor < 1.
    """
    if requests_per_day < 0 or peak_factor < 1:
        raise ValueError("need requests_per_day >= 0 and peak_factor >= 1")
    average = requests_per_day / SECONDS_PER_DAY
    return math.ceil(average), math.ceil(average * peak_factor)


def storage_bytes(rows_per_day: int, bytes_per_row: int, days: int, overhead: float = 1.0) -> int:
    """Total bytes = rows_per_day * bytes_per_row * days * overhead, rounded UP.

    overhead covers indexes etc. (1.5 means +50%). ValueError if any argument is negative or overhead < 1.
    """
    if min(rows_per_day, bytes_per_row, days) < 0 or overhead < 1:
        raise ValueError("arguments must be >= 0 and overhead >= 1")
    return math.ceil(rows_per_day * bytes_per_row * days * overhead)


def human_bytes(n: int) -> str:
    """Decimal units, one decimal place above bytes: 999 -> '999 B', 1500 -> '1.5 KB', 657_000_000 -> '657.0 MB'.

    Units: B, KB, MB, GB, TB (powers of 1000). Use the largest unit whose value is >= 1; stop at TB.
    """
    if n < 1000:
        return f"{n} B"
    value = n / 1000
    for unit in ("KB", "MB", "GB"):
        if value < 1000:
            return f"{value:.1f} {unit}"
        value /= 1000
    return f"{value:.1f} TB"


def needs_cache(peak_read_rps: float, db_read_capacity_rps: float, headroom: float = 0.5) -> bool:
    """True when the peak read load exceeds the share of database capacity we're willing to use.

    The database should run at most `headroom` (0.5 = 50%) of its measured capacity at peak.
    """
    return peak_read_rps > db_read_capacity_rps * headroom
```

**Why it works**

- **Validate, then compute.** Bad input (negative traffic, a peak factor below 1) fails loudly instead of producing a plausible-looking wrong number in a design doc.
- **`math.ceil` everywhere.** An estimate that rounds down hides load: 0.035 writes per second is still "at least one request in some seconds". `math.ceil` leaves exact values alone (86,400/day is exactly 1 rps).
- **`human_bytes` walks the units** and stops at TB, so a huge number prints as `5000.0 TB` rather than failing or inventing a unit. Values below 1000 print as whole bytes, without a decimal.
- **`needs_cache` is strict.** At exactly 50% of capacity the database is at its planned limit, which is still fine; one request per second more and it isn't.

**How to use these in a design doc:** write the inputs as assumptions ("5,000 members, 20 views each per day, peak x10") and the outputs as conclusions ("12 rps peak reads: one database instance; no cache needed for capacity"). When a reviewer disagrees with a number, they argue with the assumption, which is exactly the conversation you want.
