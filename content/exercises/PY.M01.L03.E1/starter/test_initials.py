from initials import initials


def test_two_names():
    assert initials("ada lovelace") == "AL"


def test_three_names():
    assert initials("guido van rossum") == "GVR"


def test_single_name():
    assert initials("Linus") == "L"


def test_already_uppercase():
    assert initials("GRACE HOPPER") == "GH"


def test_extra_spaces():
    assert initials("  grace   hopper ") == "GH"


def test_empty():
    assert initials("") == ""
