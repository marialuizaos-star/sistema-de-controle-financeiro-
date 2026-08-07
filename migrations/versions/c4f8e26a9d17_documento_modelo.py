"""documento modelo (central de downloads)

Revision ID: c4f8e26a9d17
Revises: e7b2c9a5f038
Create Date: 2026-08-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c4f8e26a9d17'
down_revision = 'e7b2c9a5f038'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'documento_modelo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(length=150), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('arquivo', sa.String(length=255), nullable=False),
        sa.Column('nome_original', sa.String(length=255), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('documento_modelo')