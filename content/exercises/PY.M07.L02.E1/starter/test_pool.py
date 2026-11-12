import pytest


def make(names):
    from pool import Pool
    return Pool(names)


def test_lease_gives_first_free_connection():
    pool = make(["c1", "c2"])
    with pool.lease() as conn:
        assert conn == "c1"
        assert pool.free == ["c2"]
    assert sorted(pool.free) == ["c1", "c2"]


def test_nested_leases_get_different_connections():
    pool = make(["c1", "c2"])
    with pool.lease() as a:
        with pool.lease() as b:
            assert a != b
            assert pool.free == []
    assert sorted(pool.free) == ["c1", "c2"]


def test_connection_returned_when_block_raises():
    pool = make(["c1"])
    with pytest.raises(ValueError, match="bad row"):
        with pool.lease():
            raise ValueError("bad row")
    assert pool.free == ["c1"]


def test_connection_returned_on_early_return():
    pool = make(["c1"])

    def find():
        with pool.lease() as conn:
            return conn

    assert find() == "c1"
    assert pool.free == ["c1"]


def test_empty_pool_raises():
    pool = make([])
    with pytest.raises(RuntimeError, match="pool exhausted"):
        with pool.lease():
            pass
    assert pool.free == []


def test_exhausted_pool_is_not_corrupted():
    pool = make(["c1"])
    with pool.lease():
        with pytest.raises(RuntimeError, match="pool exhausted"):
            with pool.lease():
                pass
        assert pool.free == []
    assert pool.free == ["c1"], "each connection must be returned exactly once"


def test_pool_reusable_many_times():
    pool = make(["c1", "c2"])
    for _ in range(5):
        with pool.lease():
            pass
    assert sorted(pool.free) == ["c1", "c2"]
