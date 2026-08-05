"""senha provisoria no usuario

Revision ID: f9a1c7e42b83
Revises: b6e3d8f27a45
Create Date: 2026-08-03 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f9a1c7e42b83'
down_revision = 'b6e3d8f27a45'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('usuario', sa.Column('senha_provisoria', sa.Boolean(), nullable=False, server_default='false'))
    op.alter_column('usuario', 'senha_provisoria', server_default=None)


def downgrade():
    op.drop_column('usuario', 'senha_provisoria')