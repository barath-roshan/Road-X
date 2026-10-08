"""add road operations and events

Revision ID: 9a8b7c6d5e4f
Revises: 600ef8c4509b
Create Date: 2026-10-08 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a8b7c6d5e4f'
down_revision: Union[str, None] = '600ef8c4509b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'road_operations' not in tables:
        op.create_table(
            'road_operations',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('road_id', sa.String(length=36), nullable=True),
            sa.Column('grievance_id', sa.String(length=36), nullable=True),
            sa.Column('work_order_id', sa.String(length=36), nullable=True),
            sa.Column('created_by', sa.String(length=36), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('reason', sa.Text(), nullable=False),
            sa.Column('operation_type', sa.Enum('ROAD_CLOSURE', 'LANE_RESTRICTION', 'MAINTENANCE_WORK', 'DETOUR', 'HAZARD_BLOCK', name='roadoperationtype'), nullable=False),
            sa.Column('status', sa.Enum('PLANNED', 'ACTIVE', 'COMPLETED', 'CANCELLED', name='roadoperationstatus'), nullable=False),
            sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
            sa.Column('expected_end_time', sa.DateTime(timezone=True), nullable=False),
            sa.Column('actual_end_time', sa.DateTime(timezone=True), nullable=True),
            sa.Column('alternative_route_name', sa.String(length=255), nullable=True),
            sa.Column('alternative_route_instructions', sa.Text(), nullable=True),
            sa.Column('alternative_road_id', sa.String(length=36), nullable=True),
            sa.Column('alternative_distance_km', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['alternative_road_id'], ['road_segments.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['grievance_id'], ['grievances.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['road_id'], ['road_segments.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('road_operations', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_road_operations_created_by'), ['created_by'], unique=False)
            batch_op.create_index(batch_op.f('ix_road_operations_grievance_id'), ['grievance_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_road_operations_operation_type'), ['operation_type'], unique=False)
            batch_op.create_index(batch_op.f('ix_road_operations_road_id'), ['road_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_road_operations_status'), ['status'], unique=False)
            batch_op.create_index(batch_op.f('ix_road_operations_work_order_id'), ['work_order_id'], unique=False)

    if 'road_operation_events' not in tables:
        op.create_table(
            'road_operation_events',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('operation_id', sa.String(length=36), nullable=False),
            sa.Column('actor_id', sa.String(length=36), nullable=True),
            sa.Column('actor_role', sa.String(length=30), nullable=True),
            sa.Column('event_type', sa.String(length=50), nullable=False),
            sa.Column('old_status', sa.String(length=50), nullable=True),
            sa.Column('new_status', sa.String(length=50), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['operation_id'], ['road_operations.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('road_operation_events', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_road_operation_events_actor_id'), ['actor_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_road_operation_events_event_type'), ['event_type'], unique=False)
            batch_op.create_index(batch_op.f('ix_road_operation_events_operation_id'), ['operation_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('road_operation_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_road_operation_events_operation_id'))
        batch_op.drop_index(batch_op.f('ix_road_operation_events_event_type'))
        batch_op.drop_index(batch_op.f('ix_road_operation_events_actor_id'))
    op.drop_table('road_operation_events')

    with op.batch_alter_table('road_operations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_road_operations_work_order_id'))
        batch_op.drop_index(batch_op.f('ix_road_operations_status'))
        batch_op.drop_index(batch_op.f('ix_road_operations_road_id'))
        batch_op.drop_index(batch_op.f('ix_road_operations_operation_type'))
        batch_op.drop_index(batch_op.f('ix_road_operations_grievance_id'))
        batch_op.drop_index(batch_op.f('ix_road_operations_created_by'))
    op.drop_table('road_operations')
