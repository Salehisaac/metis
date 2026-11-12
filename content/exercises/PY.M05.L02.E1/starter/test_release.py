import dataclasses

import pytest


def test_parse_valid():
    from release import Version
    assert Version.parse("1.10.2") == Version(1, 10, 2)
    assert Version.parse("0.0.0") == Version(0, 0, 0)


def test_parse_strips_surrounding_whitespace():
    from release import Version
    assert Version.parse("  2.0.1\n") == Version(2, 0, 1)


def test_parse_rejects_bad_input():
    from release import Version
    for bad in ["", "1.2", "1.2.3.4", "a.b.c", "1.-2.3", "1..3", "1. 2.3", "v1.2.3"]:
        with pytest.raises(ValueError):
            Version.parse(bad)


def test_str_is_dotted():
    from release import Version
    assert str(Version(1, 10, 2)) == "1.10.2"
    assert repr(Version(1, 10, 2)) == "Version(major=1, minor=10, patch=2)"


def test_versions_sort_numerically():
    from release import Version
    texts = ["1.10.0", "1.9.3", "0.12.0", "1.9.10", "1.9.2"]
    ordered = sorted(Version.parse(t) for t in texts)
    assert [str(v) for v in ordered] == ["0.12.0", "1.9.2", "1.9.3", "1.9.10", "1.10.0"]
    assert Version(2, 0, 0) > Version(1, 99, 99)


def test_version_is_frozen_and_hashable():
    from release import Version
    v = Version(1, 2, 3)
    with pytest.raises(dataclasses.FrozenInstanceError):
        v.patch = 4
    assert len({Version(1, 2, 3), Version(1, 2, 3), Version(1, 2, 4)}) == 2


def test_next_minor_returns_new_version():
    from release import Version
    v = Version(1, 9, 7)
    assert v.next_minor() == Version(1, 10, 0)
    assert v == Version(1, 9, 7)


def test_release_notes_default_and_not_shared():
    from release import Release, Version
    a = Release(Version(1, 0, 0))
    b = Release(Version(1, 1, 0))
    a.notes.append("first release")
    assert a.notes == ["first release"]
    assert b.notes == []
    assert Release(Version(1, 0, 0), ["x"]) == Release(Version(1, 0, 0), ["x"])
