"""add notifications table

Revision ID: 1b2c3d4e5f6a
Revises: 9a8b7c6d5e4f
Create Date: 2026-10-08 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b2c3d4e5f6a'
down_revision: Union[str, None] = '9a8b7c6d5e4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'notifications' not in tables:
        op.create_table(
            'notifications',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('recipient_id', sa.String(length=36), nullable=False),
            sa.Column('notification_type', sa.Enum('GRIEVANCE_ACCEPTED', 'GRIEVANCE_REJECTED', 'WORK_ORDER_ASSIGNED', 'WORK_STARTED', 'WORK_PROGRESS_UPDATED', 'WORK_VERIFICATION_SUBMITTED', 'WORK_VERIFICATION_APPROVED', 'WORK_VERIFICATION_REJECTED', 'ROAD_OPERATION_ACTIVATED', 'ROAD_OPERATION_COMPLETED', 'ROAD_OPERATION_CANCELLED', name='notificationtype'), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('related_entity_type', sa.String(length=50), nullable=True),
            sa.Column('related_entity_id', sa.String(length=36), nullable=True),
            sa.Column('channel', sa.Enum('IN_APP', 'SMS', name='notificationchannel'), nullable=False),
            sa.Column('delivery_status', sa.Enum('PENDING', 'SENT', 'FAILED', 'SKIPPED', name='deliverystatus'), nullable=False),
            sa.Column('is_read', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('idempotency_key', sa.String(length=255), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('idempotency_key')
        )
        op.create_index(op.f('ix_notifications_recipient_id'), 'notifications', ['recipient_id'], unique=False)
        op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)
        op.create_index(op.f('ix_notifications_channel'), 'notifications', ['channel'], unique=False)
        op.create_index(op.f('ix_notifications_delivery_status'), 'notifications', ['delivery_status'], unique=False)
        op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
        op.create_index(op.f('ix_notifications_idempotency_key'), 'notifications', ['idempotency_key'], unique=True)
        op.create_index(op.f('ix_notifications_related_entity_id'), 'notifications', ['related_entity_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'notifications' in tables:
        op.drop_table('notifications')
