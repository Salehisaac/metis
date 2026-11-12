"""Runs your revisions with real Alembic commands against a fresh SQLite file."""

import shutil
import sqlite3
from pathlib import Path

ENV_PY = '''
from alembic import context
from sqlalchemy import create_engine

engine = create_engine(context.config.get_main_option("sqlalchemy.url"))
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=None, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
'''


def make_alembic(tmp_path):
    """A throwaway migration environment that contains this folder's rev_*.py files."""
    from alembic.config import Config
    versions = tmp_path / "migrations" / "versions"
    versions.mkdir(parents=True)
    (tmp_path / "migrations" / "env.py").write_text(ENV_PY)
    for rev in sorted(Path(__file__).parent.glob("rev_*.py")):
        shutil.copy(rev, versions / rev.name)
    db = tmp_path / "app.db"
    cfg = Config()
    cfg.set_main_option("script_location", str(tmp_path / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db}")
    return cfg, str(db)


def columns(db, table):
    with sqlite3.connect(db) as conn:
        return {row[1]: {"notnull": bool(row[3]), "default": row[4]}
                for row in conn.execute(f"PRAGMA table_info({table})")}


def current(db):
    with sqlite3.connect(db) as conn:
        return [r[0] for r in conn.execute("SELECT version_num FROM alembic_version")]


def seed(db):
    with sqlite3.connect(db) as conn:
        conn.executemany("INSERT INTO users (id, username) VALUES (?, ?)", [(1, "ali"), (2, "sara"), (3, "omid")])
        conn.executemany("INSERT INTO chats (id, title) VALUES (?, ?)", [(1, "general"), (2, "backend"), (3, "empty")])
        conn.executemany("INSERT INTO chat_members VALUES (?, ?)", [(1, 1), (1, 2), (1, 3), (2, 1)])


def test_upgrade_on_an_empty_database(tmp_path):
    from alembic import command
    cfg, db = make_alembic(tmp_path)
    command.upgrade(cfg, "head")
    assert current(db) == ["0002"]
    assert columns(db, "chats")["member_count"]["notnull"] is True


def test_upgrade_backfills_existing_chats(tmp_path):
    from alembic import command
    cfg, db = make_alembic(tmp_path)
    command.upgrade(cfg, "0001")
    seed(db)
    command.upgrade(cfg, "head")
    with sqlite3.connect(db) as conn:
        counts = dict(conn.execute("SELECT title, member_count FROM chats"))
    assert counts == {"general": 3, "backend": 1, "empty": 0}


def test_new_chats_start_at_zero(tmp_path):
    from alembic import command
    cfg, db = make_alembic(tmp_path)
    command.upgrade(cfg, "head")
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO chats (title) VALUES ('fresh')")
        assert conn.execute("SELECT member_count FROM chats").fetchone()[0] == 0


def test_downgrade_removes_the_column_and_keeps_the_data(tmp_path):
    from alembic import command
    cfg, db = make_alembic(tmp_path)
    command.upgrade(cfg, "0001")
    seed(db)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "-1")
    assert current(db) == ["0001"]
    assert "member_count" not in columns(db, "chats")
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM chats").fetchone()[0] == 3
        assert conn.execute("SELECT count(*) FROM chat_members").fetchone()[0] == 4


def test_round_trip_upgrade_downgrade_upgrade(tmp_path):
    from alembic import command
    cfg, db = make_alembic(tmp_path)
    command.upgrade(cfg, "0001")
    seed(db)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0001")
    command.upgrade(cfg, "head")
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT member_count FROM chats WHERE title = 'general'").fetchone()[0] == 3


def test_downgrade_to_base_leaves_no_tables(tmp_path):
    from alembic import command
    cfg, db = make_alembic(tmp_path)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    with sqlite3.connect(db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert tables <= {"alembic_version"}
