def test_add_returns_whether_added():
    from playlist import Playlist
    p = Playlist()
    assert p.add("intro") is True
    assert p.add("intro") is False
    assert list(p) == ["intro"]


def test_add_many_skips_duplicates_and_counts():
    from playlist import Playlist
    p = Playlist()
    p.add("a")
    assert p.add_many(["b", "a", "c", "b"]) == 2
    assert list(p) == ["a", "b", "c"]
    assert p.add_many([]) == 0


def test_remove():
    from playlist import Playlist
    p = Playlist()
    p.add_many(["a", "b", "c"])
    assert p.remove("b") is True
    assert p.remove("b") is False
    assert p.remove("zzz") is False
    assert list(p) == ["a", "c"]


def test_len_in_and_iteration_order():
    from playlist import Playlist
    p = Playlist()
    assert len(p) == 0
    p.add_many(["z", "a", "m"])
    assert len(p) == 3
    assert "a" in p
    assert "b" not in p
    assert [t for t in p] == ["z", "a", "m"]


def test_tracks_is_a_read_only_snapshot():
    from playlist import Playlist
    p = Playlist()
    p.add_many(["a", "b"])
    snap = p.tracks
    assert snap == ("a", "b")
    p.add("c")
    assert snap == ("a", "b")
    assert p.tracks == ("a", "b", "c")


def test_is_not_a_list_and_has_no_bypass():
    from playlist import Playlist
    p = Playlist()
    assert not isinstance(p, list)
    for name in ("append", "extend", "insert", "__iadd__", "__setitem__"):
        assert not hasattr(p, name), f"Playlist still has {name}"


def test_playlists_are_independent():
    from playlist import Playlist
    a, b = Playlist(), Playlist()
    a.add("x")
    assert list(b) == []
    assert b.add("x") is True
