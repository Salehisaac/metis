"""initial schema: users, chats, chat_members (given; don't change)

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(32), nullable=False, unique=True),
    )
    op.create_table(
        "chats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(100), nullable=False),
    )
    op.create_table(
        "chat_members",
        sa.Column("chat_id", sa.Integer(), sa.ForeignKey("chats.id"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("chat_members")
    op.drop_table("chats")
    op.drop_table("users")
