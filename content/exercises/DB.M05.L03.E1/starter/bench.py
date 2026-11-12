"""Tiny benchmarking helpers for deciding whether an index earns its place."""

import sqlite3
from collections.abc import Callable


def best_time(fn: Callable[[], object], number: int = 10, repeat: int = 5) -> float:
    """Seconds per call of fn(): run it `number` times per round, `repeat` rounds,
    and return the fastest round divided by `number`.

    number and repeat must both be at least 1 (ValueError otherwise).
    """
    raise NotImplementedError


def seed_messages(conn: sqlite3.Connection, n: int, chats: int, seed: int = 0) -> int:
    """Insert n generated rows into messages(chat_id, sender_id, body, created_at)
    in ONE transaction and return n.

    chat_id is in 1..chats, sender_id in 1..1000, created_at is an ISO date in 2026.
    The same seed must always produce the same rows.
    """
    raise NotImplementedError


def index_report(conn: sqlite3.Connection, sql: str, params: tuple, index_ddl: str, number: int = 20) -> dict:
    """Measure sql before and after running index_ddl (the index stays created).

    Returns {"before": seconds per query, "after": seconds per query,
             "plan_before": [detail, ...], "plan_after": [detail, ...]}
    """
    raise NotImplementedError
