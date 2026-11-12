"""Tiny benchmarking helpers for deciding whether an index earns its place."""

import random
import sqlite3
import timeit
from collections.abc import Callable


def best_time(fn: Callable[[], object], number: int = 10, repeat: int = 5) -> float:
    """Seconds per call of fn(): run it `number` times per round, `repeat` rounds,
    and return the fastest round divided by `number`.

    number and repeat must both be at least 1 (ValueError otherwise).
    """
    if number < 1 or repeat < 1:
        raise ValueError("number and repeat must be >= 1")
    rounds = timeit.repeat(fn, number=number, repeat=repeat)
    return min(rounds) / number


def seed_messages(conn: sqlite3.Connection, n: int, chats: int, seed: int = 0) -> int:
    """Insert n generated rows into messages(chat_id, sender_id, body, created_at)
    in ONE transaction and return n.

    chat_id is in 1..chats, sender_id in 1..1000, created_at is an ISO date in 2026.
    The same seed must always produce the same rows.
    """
    rng = random.Random(seed)
    rows = [
        (
            rng.randint(1, chats),
            rng.randint(1, 1000),
            f"generated message {i}",
            f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
        )
        for i in range(n)
    ]
    with conn:
        conn.executemany(
            "INSERT INTO messages (chat_id, sender_id, body, created_at) VALUES (?, ?, ?, ?)", rows
        )
    return n


def _plan(conn: sqlite3.Connection, sql: str, params: tuple) -> list[str]:
    return [row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql, params)]


def index_report(conn: sqlite3.Connection, sql: str, params: tuple, index_ddl: str, number: int = 20) -> dict:
    """Measure sql before and after running index_ddl (the index stays created).

    Returns {"before": seconds per query, "after": seconds per query,
             "plan_before": [detail, ...], "plan_after": [detail, ...]}
    """
    def run_query():
        conn.execute(sql, params).fetchall()

    report = {"plan_before": _plan(conn, sql, params), "before": best_time(run_query, number=number)}
    conn.execute(index_ddl)
    report["plan_after"] = _plan(conn, sql, params)
    report["after"] = best_time(run_query, number=number)
    return report
