def get_session(make_session):
    """A request-scoped DB session, written as a generator with a single yield.

    Before the yield: create the session with make_session(), then yield it.
    After the request succeeded: commit, then close.
    After the request failed: roll back, close, and re-raise the same exception.
    If commit itself fails: roll back, close, and let that error propagate.
    If the generator is closed without being resumed (gen.close()): never commit, but close.
    """
    session = make_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
