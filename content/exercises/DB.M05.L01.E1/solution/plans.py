"""Helpers for reading SQLite query plans in tests and scripts."""

import sqlite3


def explain(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[str]:
    """Return the detail text of every EXPLAIN QUERY PLAN row for `sql`, in order.

    explain(conn, "SELECT * FROM messages WHERE id = ?", (1,))
    -> ['SEARCH messages USING INTEGER PRIMARY KEY (rowid=?)']
    The statement itself must NOT run (a DELETE must not delete anything).
    """
    plan_rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
    return [detail for _node, _parent, _unused, detail in plan_rows]


def full_scans(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[str]:
    """Return the names (as shown in the plan, so aliases stay aliases) of the
    tables the plan reads with a full SCAN, in plan order.

    'SCAN CONSTANT ROW' (a SELECT without a table) is not a table scan.
    full_scans(conn, "SELECT * FROM messages WHERE sender_id = ?", (7,)) -> ['messages']
    """
    scanned = []
    for detail in explain(conn, sql, params):
        words = detail.split()
        if words[0] == "SCAN" and detail != "SCAN CONSTANT ROW":
            scanned.append(words[1])
    return scanned
