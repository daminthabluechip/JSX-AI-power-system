"""plan metrics and unassigned

Revision ID: c21781b7c500
Revises: 3bc848df5363
Create Date: 2026-10-14 00:39:34.972546

"""
from alembic import op
import sqlalchemy as sa


revision = 'c21781b7c500'
down_revision = '3bc848df5363'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('plans', schema=None) as batch_op:
        batch_op.add_column(sa.Column('baseline_distance_km', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('unassigned', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('error', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('plans', schema=None) as batch_op:
        batch_op.drop_column('error')
        batch_op.drop_column('unassigned')
        batch_op.drop_column('baseline_distance_km')
