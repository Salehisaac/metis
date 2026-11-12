import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


def make_session():
    from models import Base, Chat, ChatMember, Message, User
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add_all([User(id=1, username="ali"), User(id=2, username="sara"), User(id=3, username="omid")])
    session.add_all([Chat(id=1, title="general"), Chat(id=2, title="backend"),
                     Chat(id=3, title="announcements"), Chat(id=4, title="empty")])
    session.add_all([ChatMember(chat_id=1, user_id=1), ChatMember(chat_id=1, user_id=2),
                     ChatMember(chat_id=2, user_id=1), ChatMember(chat_id=2, user_id=3),
                     ChatMember(chat_id=3, user_id=2)])
    session.add_all([Message(id=i, chat_id=1 if i % 3 else 2, sender_id=1, body=f"m{i}") for i in range(1, 31)])
    session.commit()
    return session


def statements_during(session, fn, *args):
    sent = []

    def record(conn, cursor, statement, parameters, context, executemany):
        sent.append(statement)

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", record)
    try:
        fn(session, *args)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    return sent


def test_find_user():
    from queries import find_user
    session = make_session()
    assert find_user(session, "sara").id == 2
    assert find_user(session, "nobody") is None


def test_first_page_is_newest_first():
    from queries import messages_page
    session = make_session()
    page = messages_page(session, 1, limit=5)
    assert [m.id for m in page] == [29, 28, 26, 25, 23]


def test_next_page_continues_before_id():
    from queries import messages_page
    session = make_session()
    page = messages_page(session, 1, before_id=23, limit=5)
    assert [m.id for m in page] == [22, 20, 19, 17, 16]


def test_last_page_is_short_and_then_empty():
    from queries import messages_page
    session = make_session()
    assert [m.id for m in messages_page(session, 2, before_id=7)] == [6, 3]
    assert messages_page(session, 2, before_id=3) == []
    assert messages_page(session, 99) == []


def test_member_counts_includes_empty_chats_and_breaks_ties_by_title():
    from queries import member_counts
    session = make_session()
    assert member_counts(session) == [("backend", 2), ("general", 2), ("announcements", 1), ("empty", 0)]


def test_like_increments():
    from models import Message
    from queries import like
    session = make_session()
    like(session, 5)
    like(session, 5)
    session.commit()
    assert session.get(Message, 5).likes == 2


def test_like_missing_message():
    from queries import like
    session = make_session()
    with pytest.raises(LookupError):
        like(session, 999)


def test_like_is_one_update_with_sql_arithmetic():
    from queries import like
    session = make_session()
    sent = statements_during(session, like, 5)
    assert len(sent) == 1, sent
    assert sent[0].startswith("UPDATE messages SET likes=(messages.likes + "), sent
