"""Indexes for the messenger's hot queries (see test_inbox_indexes.py for the queries).

Each entry is one CREATE INDEX statement. Name them idx_<table>_<columns>.
The tables already have the indexes created by their PRIMARY KEY and UNIQUE constraints.
"""

INDEXES: list[str] = [
]
