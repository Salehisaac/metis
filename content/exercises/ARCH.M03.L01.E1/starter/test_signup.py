import asyncio
import importlib
import logging
import sqlite3
import sys
import warnings

warnings.simplefilter("ignore")


class FakeMailer:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def send_welcome(self, email):
        if self.fail:
            raise ConnectionError("smtp down")
        self.sent.append(email)


def fresh_app():
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def new_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("CREATE TABLE users (email TEXT PRIMARY KEY)")
    return conn


def client(app_module, mailer, conn):
    from fastapi.testclient import TestClient
    app_module.app.dependency_overrides[app_module.get_mailer] = lambda: mailer
    app_module.app.dependency_overrides[app_module.get_conn] = lambda: conn
    return TestClient(app_module.app)


def users(conn):
    return [row[0] for row in conn.execute("SELECT email FROM users")]


def test_signup_saves_user_and_returns_201():
    m, conn = FakeMailer(), new_conn()
    r = client(fresh_app(), m, conn).post("/signups", json={"email": " Ana@X.io "})
    assert (r.status_code, r.json()) == (201, {"email": "ana@x.io"})
    assert users(conn) == ["ana@x.io"]


def test_email_is_deferred_not_sent_inline():
    from fastapi import BackgroundTasks
    app = fresh_app()
    m, conn, tasks = FakeMailer(), new_conn(), BackgroundTasks()
    app.signup(app.SignupIn(email="bo@x.io"), tasks, conn, m)
    assert m.sent == [], "the email must not be sent while the request is being handled"
    assert len(tasks.tasks) == 1, "queue exactly one background task"
    asyncio.run(tasks())  # what the framework does after sending the response
    assert m.sent == ["bo@x.io"]


def test_email_is_sent_after_the_request():
    m, conn = FakeMailer(), new_conn()
    client(fresh_app(), m, conn).post("/signups", json={"email": "cy@x.io"})
    assert m.sent == ["cy@x.io"]


def test_mail_failure_does_not_break_signup(caplog):
    m, conn = FakeMailer(fail=True), new_conn()
    with caplog.at_level(logging.WARNING, logger="signup"):
        r = client(fresh_app(), m, conn).post("/signups", json={"email": "dee@x.io"})
    assert r.status_code == 201
    assert users(conn) == ["dee@x.io"]
    assert any("dee@x.io" in rec.getMessage() for rec in caplog.records if rec.name == "signup")


def test_send_welcome_safely_logs_instead_of_raising(caplog):
    app = fresh_app()
    with caplog.at_level(logging.WARNING, logger="signup"):
        app.send_welcome_safely(FakeMailer(fail=True), "eve@x.io")  # must not raise
    assert any(rec.levelno >= logging.WARNING and "eve@x.io" in rec.getMessage() for rec in caplog.records)


def test_duplicate_signup_is_409_and_sends_nothing():
    m, conn = FakeMailer(), new_conn()
    c = client(fresh_app(), m, conn)
    c.post("/signups", json={"email": "fay@x.io"})
    r = c.post("/signups", json={"email": "FAY@x.io"})
    assert (r.status_code, r.json()) == (409, {"detail": "email already registered"})
    assert m.sent == ["fay@x.io"], "no welcome email for a failed signup"
