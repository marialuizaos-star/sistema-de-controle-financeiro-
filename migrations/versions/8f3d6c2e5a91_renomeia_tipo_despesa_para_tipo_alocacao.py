"""renomeia tipo_despesa para tipo_alocacao

Revision ID: 8f3d6c2e5a91
Revises: 4e8b1f7a9c3d
Create Date: 2026-07-31 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f3d6c2e5a91'
down_revision = '4e8b1f7a9c3d'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('tipo_despesa', 'tipo_alocacao')

    with op.batch_alter_table('alocacao', schema=None) as batch_op:
        batch_op.alter_column('tipo_despesa_id', new_column_name='tipo_alocacao_id')


def downgrade():
    with op.batch_alter_table('alocacao', schema=None) as batch_op:
        batch_op.alter_column('tipo_alocacao_id', new_column_name='tipo_despesa_id')

    op.rename_table('tipo_alocacao', 'tipo_despesa')