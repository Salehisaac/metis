from contextlib import contextmanager

import pytest


class FakeSession:
    def __init__(self, events, fail_commit=False):
        self.events = events
        self.fail_commit = fail_commit

    def commit(self):
        self.events.append("commit")
        if self.fail_commit:
            raise RuntimeError("deadlock on commit")

    def rollback(self):
        self.events.append("rollback")

    def close(self):
        self.events.append("close")


def factory(events, made, **kwargs):
    def make_session():
        session = FakeSession(events, **kwargs)
        made.append(session)
        return session

    return make_session


def start(**kwargs):
    """Create the dependency and run it up to its yield, as a framework would."""
    from deps import get_session
    events, made = [], []
    gen = get_session(factory(events, made, **kwargs))
    session = next(gen)
    return gen, session, events, made


def test_yields_the_new_session_and_does_nothing_else_yet():
    gen, session, events, made = start()
    assert made == [session]
    assert events == []


def test_session_is_created_lazily():
    from deps import get_session
    events, made = [], []
    get_session(factory(events, made))
    assert made == [], "nothing may run before the framework calls next()"


def test_success_commits_then_closes():
    gen, session, events, _ = start()
    with pytest.raises(StopIteration):
        next(gen)
    assert events == ["commit", "close"]


def test_error_rolls_back_closes_and_reraises_same_exception():
    gen, session, events, _ = start()
    error = ValueError("invalid order")
    with pytest.raises(ValueError) as info:
        gen.throw(error)
    assert info.value is error
    assert events == ["rollback", "close"]


def test_failed_commit_rolls_back_and_propagates():
    gen, session, events, _ = start(fail_commit=True)
    with pytest.raises(RuntimeError, match="deadlock"):
        next(gen)
    assert events == ["commit", "rollback", "close"]


def test_abandoned_request_closes_without_commit():
    gen, session, events, _ = start()
    gen.close()
    assert "commit" not in events
    assert events.count("close") == 1
    assert events[-1] == "close"


def test_failing_factory_leaves_nothing_to_clean_up():
    from deps import get_session

    def broken():
        raise ConnectionError("db down")

    gen = get_session(broken)
    with pytest.raises(ConnectionError):
        next(gen)


def test_works_as_a_context_manager():
    from deps import get_session
    events, made = [], []
    session_scope = contextmanager(get_session)
    with session_scope(factory(events, made)) as session:
        assert session is made[0]
    assert events == ["commit", "close"]

    events.clear()
    with pytest.raises(KeyError):
        with session_scope(factory(events, made)):
            raise KeyError("missing")
    assert events == ["rollback", "close"]
