"""hierarquia de alocacoes (nivel 1/2) e categoria do projeto

Revision ID: 9d4e7f2a8c15
Revises: c4f8e26a9d17
Create Date: 2026-08-10 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '9d4e7f2a8c15'
down_revision = 'c4f8e26a9d17'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projeto', sa.Column('categoria', sa.String(length=10), nullable=True))
    op.create_check_constraint(
        "ck_projeto_categoria_valida", "projeto",
        "categoria IS NULL OR categoria IN ('custeio', 'capital')",
    )

    op.add_column('alocacao', sa.Column('alocacao_pai_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_alocacao_pai', 'alocacao', 'alocacao', ['alocacao_pai_id'], ['id']
    )
    op.add_column('alocacao', sa.Column('status', sa.String(length=20), nullable=False, server_default='aprovada'))
    op.alter_column('alocacao', 'status', server_default=None)
    op.create_check_constraint(
        "ck_alocacao_status_valido", "alocacao",
        "status IN ('aprovada', 'pendente', 'reprovada')",
    )

    op.add_column('despesa', sa.Column('cpf_favorecido', sa.String(length=14), nullable=True))


def downgrade():
    op.drop_column('despesa', 'cpf_favorecido')
    op.drop_constraint('ck_alocacao_status_valido', 'alocacao', type_='check')
    op.drop_column('alocacao', 'status')
    op.drop_constraint('fk_alocacao_pai', 'alocacao', type_='foreignkey')
    op.drop_column('alocacao', 'alocacao_pai_id')
    op.drop_constraint('ck_projeto_categoria_valida', 'projeto', type_='check')
    op.drop_column('projeto', 'categoria')