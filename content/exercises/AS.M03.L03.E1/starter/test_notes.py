import aiosqlite
import httpx
import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "notes.db")


@pytest.fixture
def counted(monkeypatch):
    """Count every aiosqlite connection opened and closed while the test runs."""
    stats = {"opened": 0, "closed": 0}
    real_connect = aiosqlite.connect

    def connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        stats["opened"] += 1
        real_close = conn.close

        async def close():
            stats["closed"] += 1
            await real_close()

        conn.close = close
        return conn

    monkeypatch.setattr(aiosqlite, "connect", connect)
    return stats


async def setup(db_path, monkeypatch):
    import notes
    monkeypatch.setattr(notes, "DB_PATH", db_path)
    await notes.init_db(db_path)
    transport = httpx.ASGITransport(app=notes.app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def rows(db_path):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.execute("SELECT title, body FROM notes ORDER BY id")
        return await cur.fetchall()


@pytest.mark.anyio
async def test_create_then_read(db_path, monkeypatch):
    async with await setup(db_path, monkeypatch) as client:
        r = await client.post("/notes", json={"title": "buy milk", "body": "2 litres"})
        assert r.status_code == 201
        note_id = r.json()["id"]
        r = await client.get(f"/notes/{note_id}")
    assert r.status_code == 200
    assert r.json() == {"id": note_id, "title": "buy milk", "body": "2 litres"}


@pytest.mark.anyio
async def test_created_note_is_committed(db_path, monkeypatch):
    async with await setup(db_path, monkeypatch) as client:
        r = await client.post("/notes", json={"title": "t", "body": "b"})
    assert r.status_code == 201
    assert await rows(db_path) == [("t", "b")], "the insert was not committed"


@pytest.mark.anyio
async def test_missing_note_is_404(db_path, monkeypatch):
    async with await setup(db_path, monkeypatch) as client:
        r = await client.get("/notes/999")
    assert r.status_code == 404
    assert r.json() == {"detail": "note not found"}


@pytest.mark.anyio
async def test_batch_saved(db_path, monkeypatch):
    async with await setup(db_path, monkeypatch) as client:
        r = await client.post("/notes/batch", json=[{"title": "a", "body": "1"}, {"title": "b", "body": "2"}])
    assert r.status_code == 201
    assert await rows(db_path) == [("a", "1"), ("b", "2")]


@pytest.mark.anyio
async def test_failed_batch_saves_nothing(db_path, monkeypatch):
    async with await setup(db_path, monkeypatch) as client:
        await client.post("/notes", json={"title": "keep", "body": "me"})
        r = await client.post("/notes/batch", json=[{"title": "a", "body": "1"}, {"title": "  ", "body": "2"}])
    assert r.status_code == 422
    assert await rows(db_path) == [("keep", "me")], "a failed batch left rows behind"


@pytest.mark.anyio
async def test_every_connection_is_closed(db_path, monkeypatch, counted):
    async with await setup(db_path, monkeypatch) as client:
        await client.post("/notes", json={"title": "x", "body": "y"})
        await client.get("/notes/1")
        await client.get("/notes/2")
        await client.post("/notes/batch", json=[{"title": "", "body": "z"}])
    assert counted["opened"] >= 4
    assert counted["closed"] == counted["opened"], f"{counted['opened'] - counted['closed']} connection(s) never closed"
