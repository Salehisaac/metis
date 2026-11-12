"""YOUR tests for the messages endpoints in app.py.

Every test takes the `client` fixture (from conftest.py) and nothing else.
Write each one as Arrange / Act / Assert. Replace each pytest.fail(...) line with your test.
test_meta.py then runs these tests against six broken copies of app.py:
each broken copy must make at least one of your tests fail.
"""

import pytest


def test_send_message_returns_201_and_the_message(client):
    """Normal path: POST /chats/2/messages with a valid text.
    Check the status code AND every field of the returned message you can predict."""
    pytest.fail("write this test")


def test_send_to_unknown_chat_is_404(client):
    """Error path: the chat doesn't exist."""
    pytest.fail("write this test")


def test_blank_text_is_422(client):
    """Invalid path: a text that has characters but is still empty for a human."""
    pytest.fail("write this test")


def test_list_shows_only_this_chat(client):
    """Edge path: a chat with no messages of its own, while another chat has some."""
    pytest.fail("write this test")


def test_list_keeps_sending_order(client):
    """Normal path: send two messages to one chat, then list that chat."""
    pytest.fail("write this test")
