import pytest

from ranking import top_senders

MESSAGES = [
    ("sara", "hi"),
    ("ali", "salam"),
    ("bob", "yo"),
    ("ali", "how are you?"),
    ("bob", "fine"),
    ("ali", "good"),
]


def test_top_two():
    assert top_senders(MESSAGES, 2) == ["ali", "bob"]


def test_top_one():
    assert top_senders(MESSAGES, 1) == ["ali"]


def test_n_is_a_ranking_size_not_a_count():
    # ali sent 3, bob 2, sara 1: n=3 means "the top 3", i.e. everyone
    assert top_senders(MESSAGES, 3) == ["ali", "bob", "sara"]


def test_ties_are_alphabetical_even_if_input_is_not():
    msgs = [("zoe", "a"), ("mia", "b"), ("adam", "c")]
    assert top_senders(msgs, 3) == ["adam", "mia", "zoe"]


def test_tie_at_the_cutoff():
    msgs = [("kian", "x"), ("kian", "y"), ("tara", "z"), ("dana", "w")]
    assert top_senders(msgs, 2) == ["kian", "dana"]


def test_n_larger_than_number_of_senders():
    assert top_senders(MESSAGES, 10) == ["ali", "bob", "sara"]


def test_empty_text_does_not_count():
    msgs = [("ali", ""), ("ali", ""), ("bob", "hey"), ("eve", "")]
    assert top_senders(msgs, 3) == ["bob"]


def test_n_zero_and_empty_input():
    assert top_senders(MESSAGES, 0) == []
    assert top_senders([], 3) == []


def test_negative_n_raises():
    with pytest.raises(ValueError):
        top_senders(MESSAGES, -1)


def test_input_is_not_modified():
    msgs = [("b", "1"), ("a", "2"), ("b", "3")]
    before = list(msgs)
    top_senders(msgs, 2)
    assert msgs == before
