"""stop actual arrival

Revision ID: 173abb12feec
Revises: fbe708b79958
Create Date: 2026-10-14 01:38:30.416320

"""
from alembic import op
import sqlalchemy as sa


revision = '173abb12feec'
down_revision = 'fbe708b79958'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('stops', schema=None) as batch_op:
        batch_op.add_column(sa.Column('actual_arrival', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('stops', schema=None) as batch_op:
        batch_op.drop_column('actual_arrival')
