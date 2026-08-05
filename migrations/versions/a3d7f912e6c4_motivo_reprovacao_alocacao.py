"""motivo de reprovacao na alocacao

Revision ID: a3d7f912e6c4
Revises: f9a1c7e42b83
Create Date: 2026-08-03 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a3d7f912e6c4'
down_revision = 'f9a1c7e42b83'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('alocacao', sa.Column('motivo_reprovacao', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('alocacao', 'motivo_reprovacao')