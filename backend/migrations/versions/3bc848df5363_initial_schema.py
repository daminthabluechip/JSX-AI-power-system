"""initial schema

Revision ID: 3bc848df5363
Revises: 
Create Date: 2026-10-14 00:34:30.073929

"""
from alembic import op
import sqlalchemy as sa


revision = '3bc848df5363'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('depots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('opens_at', sa.Time(), nullable=True),
    sa.Column('closes_at', sa.Time(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer', sa.String(length=120), nullable=False),
    sa.Column('address', sa.String(length=255), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.Column('volume_m3', sa.Float(), nullable=False),
    sa.Column('priority', sa.String(length=10), nullable=False),
    sa.Column('target_date', sa.Date(), nullable=False),
    sa.Column('earliest_arrival', sa.Time(), nullable=True),
    sa.Column('latest_arrival', sa.Time(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('plans',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('planning_date', sa.Date(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('total_distance_km', sa.Float(), nullable=True),
    sa.Column('total_time_min', sa.Float(), nullable=True),
    sa.Column('solve_time_s', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('vehicles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('registration', sa.String(length=20), nullable=False),
    sa.Column('model', sa.String(length=80), nullable=True),
    sa.Column('vehicle_type', sa.String(length=40), nullable=True),
    sa.Column('driver', sa.String(length=80), nullable=True),
    sa.Column('weight_capacity_kg', sa.Float(), nullable=False),
    sa.Column('volume_capacity_m3', sa.Float(), nullable=False),
    sa.Column('shift_start', sa.Time(), nullable=True),
    sa.Column('shift_end', sa.Time(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('depot_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['depot_id'], ['depots.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('registration')
    )
    op.create_table('events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('vehicle_id', sa.Integer(), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.Column('occurred_at', sa.DateTime(), nullable=True),
    sa.Column('delay_minutes', sa.Integer(), nullable=True),
    sa.Column('handled_by_plan_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['handled_by_plan_id'], ['plans.id'], ),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('positions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('vehicle_id', sa.Integer(), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('speed_kmh', sa.Float(), nullable=True),
    sa.Column('recorded_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('positions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_positions_vehicle_id'), ['vehicle_id'], unique=False)

    op.create_table('routes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=False),
    sa.Column('vehicle_id', sa.Integer(), nullable=False),
    sa.Column('planned_departure', sa.DateTime(), nullable=True),
    sa.Column('load_kg', sa.Float(), nullable=True),
    sa.Column('volume_m3', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stops',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('route_id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('planned_arrival', sa.DateTime(), nullable=True),
    sa.Column('planned_departure', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['route_id'], ['routes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('stops')
    op.drop_table('routes')
    with op.batch_alter_table('positions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_positions_vehicle_id'))

    op.drop_table('positions')
    op.drop_table('events')
    op.drop_table('vehicles')
    op.drop_table('plans')
    op.drop_table('orders')
    op.drop_table('depots')
