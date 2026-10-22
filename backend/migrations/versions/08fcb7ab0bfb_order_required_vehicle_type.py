"""order required vehicle type

Revision ID: 08fcb7ab0bfb
Revises: 173abb12feec
Create Date: 2026-10-14 01:58:39.528477

"""
from alembic import op
import sqlalchemy as sa


revision = '08fcb7ab0bfb'
down_revision = '173abb12feec'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('required_vehicle_type', sa.String(length=30), nullable=True))


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('required_vehicle_type')
