"""arquivo de instrucoes no projeto

Revision ID: d5c8a24f19b7
Revises: a3d7f912e6c4
Create Date: 2026-08-03 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd5c8a24f19b7'
down_revision = 'a3d7f912e6c4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projeto', sa.Column('arquivo_instrucoes', sa.String(length=255), nullable=True))
    op.add_column('projeto', sa.Column('instrucoes_nome_original', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('projeto', 'instrucoes_nome_original')
    op.drop_column('projeto', 'arquivo_instrucoes')