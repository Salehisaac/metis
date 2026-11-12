"""YOUR tests for the unit of work in app.py. Replace each pytest.fail(...) with a test.

Tests may take any of these fixtures (conftest.py): client, db, engine, connections.
test_meta.py runs your tests against five broken copies of app.py; each must make
at least one of your tests fail. Read the mutants only after your first run.
"""

import pytest


def test_send_saves_message_count_and_audit(client, db):
    """Normal path: one message is sent. Check the response AND all three tables,
    reading them through db (committed data only)."""
    pytest.fail("write this test")


def test_duplicate_client_id_is_409_and_changes_nothing(client, db):
    """Error path: the same client_id twice. The second request must answer 409,
    and the database must look exactly as it did after the first request."""
    pytest.fail("write this test")


def test_audit_failure_rolls_back_everything(client, db):
    """Error path: the audit log is down. Override get_audit (on client.app) with an
    object whose record() raises AuditUnavailable. Expect 503 and NO new rows, and an
    unchanged message_count."""
    pytest.fail("write this test")


def test_no_connection_is_held_after_requests(client, connections):
    """Leak check: after a successful request, a 404 and a 409, no connection may
    still be checked out."""
    pytest.fail("write this test")
