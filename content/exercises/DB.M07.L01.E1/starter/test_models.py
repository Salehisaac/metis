import pytest
from sqlalchemy import create_engine, insert, select
from sqlalchemy.exc import IntegrityError


def tables():
    from models import Base
    return Base.metadata.tables


def setup_db():
    from models import Base, Message, User
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(insert(User), [{"id": 1, "username": "ali"}, {"id": 2, "username": "sara"}])
        conn.execute(insert(Message), [{"id": 1, "sender_id": 1, "body": "hi"}])
    return engine


def test_contacts_table_columns():
    t = tables()["contacts"]
    assert [c.name for c in t.primary_key.columns] == ["owner_id", "contact_id"]
    assert t.c.nickname.nullable is True
    assert t.c.nickname.type.length == 64
    assert t.c.added_at.nullable is False
    assert t.c.added_at.server_default is not None


def test_contacts_foreign_keys():
    t = tables()["contacts"]
    targets = {fk.parent.name: fk.target_fullname for fk in t.foreign_keys}
    assert targets == {"owner_id": "users.id", "contact_id": "users.id"}


def test_reactions_table_columns():
    t = tables()["reactions"]
    assert [c.name for c in t.primary_key.columns] == ["id"]
    for name in ("message_id", "user_id", "emoji"):
        assert t.c[name].nullable is False, name
    assert t.c.emoji.type.length == 16
    targets = {fk.parent.name: fk.target_fullname for fk in t.foreign_keys}
    assert targets == {"message_id": "messages.id", "user_id": "users.id"}


def test_reactions_unique_constraint():
    from sqlalchemy import UniqueConstraint
    t = tables()["reactions"]
    uniques = {c.name: [col.name for col in c.columns] for c in t.constraints if isinstance(c, UniqueConstraint)}
    assert uniques.get("uq_reactions_message_user_emoji") == ["message_id", "user_id", "emoji"]


def test_contact_rows_get_added_at_from_the_database():
    from models import Contact
    engine = setup_db()
    with engine.begin() as conn:
        conn.execute(insert(Contact), [{"owner_id": 1, "contact_id": 2}])
        row = conn.execute(select(Contact.nickname, Contact.added_at)).one()
    assert row.nickname is None
    assert row.added_at is not None


def test_same_contact_twice_is_rejected():
    from models import Contact
    engine = setup_db()
    with engine.begin() as conn:
        conn.execute(insert(Contact), [{"owner_id": 1, "contact_id": 2}])
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(insert(Contact), [{"owner_id": 1, "contact_id": 2, "nickname": "again"}])


def test_same_emoji_twice_is_rejected_but_other_emoji_is_fine():
    from models import Reaction
    engine = setup_db()
    with engine.begin() as conn:
        conn.execute(insert(Reaction), [{"message_id": 1, "user_id": 2, "emoji": "+1"},
                                        {"message_id": 1, "user_id": 2, "emoji": "heart"},
                                        {"message_id": 1, "user_id": 1, "emoji": "+1"}])
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(insert(Reaction), [{"message_id": 1, "user_id": 2, "emoji": "+1"}])


def test_emoji_is_required():
    from models import Reaction
    engine = setup_db()
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(insert(Reaction), [{"message_id": 1, "user_id": 2, "emoji": None}])
