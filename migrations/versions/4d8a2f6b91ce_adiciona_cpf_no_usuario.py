"""adiciona cpf no usuario

Revision ID: 4d8a2f6b91ce
Revises: 7c4a1b8e35df
Create Date: 2026-08-02 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '4d8a2f6b91ce'
down_revision = '7c4a1b8e35df'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('usuario', sa.Column('cpf', sa.String(length=14), nullable=True))


def downgrade():
    op.drop_column('usuario', 'cpf')