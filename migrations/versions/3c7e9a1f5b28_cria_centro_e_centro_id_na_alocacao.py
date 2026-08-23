"""cria centro e centro_id na alocacao

Revision ID: 3c7e9a1f5b28
Revises: 9f2a3b7d1c44
Create Date: 2026-08-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c7e9a1f5b28'
down_revision = '9f2a3b7d1c44'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'centro',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=150), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome'),
    )
    op.add_column('alocacao', sa.Column('centro_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_alocacao_centro_id', 'alocacao', 'centro', ['centro_id'], ['id']
    )


def downgrade():
    op.drop_constraint('fk_alocacao_centro_id', 'alocacao', type_='foreignkey')
    op.drop_column('alocacao', 'centro_id')
    op.drop_table('centro')