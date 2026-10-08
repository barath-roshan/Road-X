"""add chat conversations and messages tables

Revision ID: 3c4d5e6f7a8b
Revises: 1b2c3d4e5f6a
Create Date: 2026-10-09 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c4d5e6f7a8b'
down_revision: Union[str, None] = '1b2c3d4e5f6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'chat_conversations' not in tables:
        op.create_table(
            'chat_conversations',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('citizen_id', sa.String(length=36), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False, server_default='Citizen Chat Session'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['citizen_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_chat_conversations_citizen_id'), 'chat_conversations', ['citizen_id'], unique=False)

    if 'chat_messages' not in tables:
        op.create_table(
            'chat_messages',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('conversation_id', sa.String(length=36), nullable=False),
            sa.Column('role', sa.Enum('USER', 'ASSISTANT', 'SYSTEM', name='chatrole'), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('sources_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_chat_messages_conversation_id'), 'chat_messages', ['conversation_id'], unique=False)
        op.create_index(op.f('ix_chat_messages_role'), 'chat_messages', ['role'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'chat_messages' in tables:
        op.drop_table('chat_messages')

    if 'chat_conversations' in tables:
        op.drop_table('chat_conversations')
