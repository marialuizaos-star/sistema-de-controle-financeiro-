"""tipo na notificacao

Revision ID: 2f8a6c1e9b3d
Revises: 7e1d4a9c3f56
Create Date: 2026-09-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '2f8a6c1e9b3d'
down_revision = '7e1d4a9c3f56'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('notificacao', sa.Column('tipo', sa.String(length=30), nullable=True))


def downgrade():
    op.drop_column('notificacao', 'tipo')