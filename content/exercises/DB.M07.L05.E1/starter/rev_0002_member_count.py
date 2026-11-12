"""add chats.member_count

Revision ID: 0002
Revises: 0001

The chat list shows how many members each chat has. Counting chat_members on every request
is too slow, so we store the number on the chat.
- Required (NOT NULL); a new chat starts at 0 even when inserted by code that doesn't know the column.
- Existing chats must get their real member count.
- downgrade() must undo upgrade() completely, keeping all other data.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chats", sa.Column("member_count", sa.Integer(), nullable=False))


def downgrade() -> None:
    pass
