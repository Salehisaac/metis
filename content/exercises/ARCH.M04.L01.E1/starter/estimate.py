"""Back-of-the-envelope helpers for design docs."""
import math  # noqa: F401  (you'll need it)

SECONDS_PER_DAY = 86_400


def rps(requests_per_day: int, peak_factor: float) -> tuple[int, int]:
    """(average, peak) requests per second, each rounded UP to a whole number.

    peak = average * peak_factor. ValueError if requests_per_day < 0 or peak_factor < 1.
    """
    raise NotImplementedError


def storage_bytes(rows_per_day: int, bytes_per_row: int, days: int, overhead: float = 1.0) -> int:
    """Total bytes = rows_per_day * bytes_per_row * days * overhead, rounded UP.

    overhead covers indexes etc. (1.5 means +50%). ValueError if any argument is negative or overhead < 1.
    """
    raise NotImplementedError


def human_bytes(n: int) -> str:
    """Decimal units, one decimal place above bytes: 999 -> '999 B', 1500 -> '1.5 KB', 657_000_000 -> '657.0 MB'.

    Units: B, KB, MB, GB, TB (powers of 1000). Use the largest unit whose value is >= 1; stop at TB.
    """
    raise NotImplementedError


def needs_cache(peak_read_rps: float, db_read_capacity_rps: float, headroom: float = 0.5) -> bool:
    """True when the peak read load exceeds the share of database capacity we're willing to use.

    The database should run at most `headroom` (0.5 = 50%) of its measured capacity at peak.
    """
    raise NotImplementedError
