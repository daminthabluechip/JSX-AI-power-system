"""plan baseline served

Revision ID: e177d81c9006
Revises: 09ff8e3d65ed
Create Date: 2026-10-20 13:04:45.652452

"""
from alembic import op
import sqlalchemy as sa


revision = 'e177d81c9006'
down_revision = '09ff8e3d65ed'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('plans', schema=None) as batch_op:
        batch_op.add_column(sa.Column('baseline_served', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('plans', schema=None) as batch_op:
        batch_op.drop_column('baseline_served')
