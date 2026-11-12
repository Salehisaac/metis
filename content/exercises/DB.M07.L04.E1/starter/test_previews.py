from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session


def make_session(chats=30, users=12):
    from models import Base, Chat, Message, User
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s, s.begin():
        people = [User(username=f"u{i:02d}") for i in range(users)]
        for n in range(chats):
            chat = Chat(title=f"chat {n:02d}", members=[people[(n + k) % users] for k in range(3)])
            chat.messages = [Message(body=f"c{n} m{k}", sender=people[k % users]) for k in range(users)]
            s.add(chat)
    return Session(engine)


def count_selects(session, fn, *args):
    sent = []

    def record(conn, cursor, statement, parameters, context, executemany):
        sent.append(statement)

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", record)
    try:
        result = fn(session, *args)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    return result, len(sent)


def test_member_lists_content():
    from previews import chat_member_lists
    result = chat_member_lists(make_session(chats=3, users=4))
    assert result == [("chat 00", ["u00", "u01", "u02"]),
                      ("chat 01", ["u01", "u02", "u03"]),
                      ("chat 02", ["u00", "u02", "u03"])]


def test_member_lists_chat_without_members():
    from models import Chat
    from previews import chat_member_lists
    session = make_session(chats=1, users=3)
    session.add(Chat(title="a lonely chat"))
    session.commit()
    assert chat_member_lists(session)[0] == ("a lonely chat", [])


def test_member_lists_use_at_most_two_queries():
    from previews import chat_member_lists
    session = make_session(chats=30)
    result, selects = count_selects(session, chat_member_lists)
    assert len(result) == 30
    assert selects <= 2, f"{selects} SELECT statements for 30 chats"


def test_latest_with_senders_content():
    from previews import latest_with_senders
    session = make_session(chats=2, users=4)
    assert latest_with_senders(session, 2, 3) == [("u03", "c1 m3"), ("u02", "c1 m2"), ("u01", "c1 m1")]


def test_latest_with_senders_unknown_chat():
    from previews import latest_with_senders
    assert latest_with_senders(make_session(chats=1), 99) == []


def test_latest_with_senders_uses_at_most_two_queries():
    from previews import latest_with_senders
    session = make_session(chats=2, users=12)
    result, selects = count_selects(session, latest_with_senders, 1, 10)
    assert len({sender for sender, _ in result}) == 10
    assert selects <= 2, f"{selects} SELECT statements for 10 messages"
