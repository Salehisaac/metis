from words import count_words


def test_example():
    assert count_words("Go py go") == {"go": 2, "py": 1}


def test_empty_and_whitespace():
    assert count_words("") == {}
    assert count_words("  \n\t ") == {}
