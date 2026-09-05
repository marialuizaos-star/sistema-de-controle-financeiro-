"""prestacao de contas por alocacao

Revision ID: 7e1d4a9c3f56
Revises: 3c7e9a1f5b28
Create Date: 2026-09-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7e1d4a9c3f56'
down_revision = '3c7e9a1f5b28'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('alocacao', sa.Column('status_prestacao_contas', sa.String(length=20), nullable=True))
    op.add_column('alocacao', sa.Column('motivo_reprovacao_prestacao', sa.Text(), nullable=True))
    op.add_column('alocacao', sa.Column('enviada_em_prestacao', sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        'ck_alocacao_status_prestacao_contas_valido',
        'alocacao',
        "status_prestacao_contas IS NULL OR status_prestacao_contas IN ('em_analise', 'aceita', 'reprovada')",
    )


def downgrade():
    op.drop_constraint('ck_alocacao_status_prestacao_contas_valido', 'alocacao', type_='check')
    op.drop_column('alocacao', 'enviada_em_prestacao')
    op.drop_column('alocacao', 'motivo_reprovacao_prestacao')
    op.drop_column('alocacao', 'status_prestacao_contas')