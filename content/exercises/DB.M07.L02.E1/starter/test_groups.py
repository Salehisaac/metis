import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker


def make_factory(tmp_path):
    from models import Base, User
    engine = create_engine(f"sqlite:///{tmp_path / 'chat.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as session:
        session.add_all([User(username=n) for n in ("ali", "sara", "omid", "lena")])
    return factory


def members_of(factory, chat_id):
    from models import ChatMember, User
    with factory() as session:
        stmt = (select(User.username).join(ChatMember, ChatMember.user_id == User.id)
                .where(ChatMember.chat_id == chat_id).order_by(User.username))
        return session.scalars(stmt).all()


def count(factory, model):
    with factory() as session:
        return session.scalar(select(func.count()).select_from(model))


def test_create_group_returns_id_and_saves_members(tmp_path):
    from groups import create_group
    from models import Chat
    factory = make_factory(tmp_path)
    chat_id = create_group(factory, "backend", "ali", ["sara", "omid"])
    with factory() as session:
        assert session.get(Chat, chat_id).title == "backend"
    assert members_of(factory, chat_id) == ["ali", "omid", "sara"]


def test_creator_alone(tmp_path):
    from groups import create_group
    factory = make_factory(tmp_path)
    chat_id = create_group(factory, "notes", "lena", [])
    assert members_of(factory, chat_id) == ["lena"]


def test_duplicates_are_added_once(tmp_path):
    from groups import create_group
    factory = make_factory(tmp_path)
    chat_id = create_group(factory, "dupes", "ali", ["sara", "ali", "sara"])
    assert members_of(factory, chat_id) == ["ali", "sara"]


def test_unknown_member_saves_nothing(tmp_path):
    from groups import create_group
    from models import Chat, ChatMember
    factory = make_factory(tmp_path)
    with pytest.raises(LookupError, match="ghost"):
        create_group(factory, "broken", "ali", ["sara", "ghost"])
    assert count(factory, Chat) == 0
    assert count(factory, ChatMember) == 0


def test_unknown_creator_saves_nothing(tmp_path):
    from groups import create_group
    from models import Chat
    factory = make_factory(tmp_path)
    with pytest.raises(LookupError, match="nobody"):
        create_group(factory, "broken", "nobody", ["sara"])
    assert count(factory, Chat) == 0


def test_blank_title_saves_nothing(tmp_path):
    from groups import create_group
    from models import Chat
    factory = make_factory(tmp_path)
    with pytest.raises(ValueError):
        create_group(factory, "   ", "ali", ["sara"])
    assert count(factory, Chat) == 0


def test_add_member_then_again(tmp_path):
    from groups import add_member, create_group
    factory = make_factory(tmp_path)
    chat_id = create_group(factory, "backend", "ali", [])
    assert add_member(factory, chat_id, "sara") is True
    assert add_member(factory, chat_id, "sara") is False
    assert members_of(factory, chat_id) == ["ali", "sara"]


def test_add_member_unknown_chat_or_user(tmp_path):
    from groups import add_member, create_group
    factory = make_factory(tmp_path)
    chat_id = create_group(factory, "backend", "ali", [])
    with pytest.raises(LookupError):
        add_member(factory, 999, "sara")
    with pytest.raises(LookupError):
        add_member(factory, chat_id, "ghost")
