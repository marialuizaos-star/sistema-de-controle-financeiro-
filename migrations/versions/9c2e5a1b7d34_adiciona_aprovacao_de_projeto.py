"""adiciona aprovação de cadastro de projeto por usuário

Revision ID: 9c2e5a1b7d34
Revises: 8a1d4f6c92e7
Create Date: 2026-07-30 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c2e5a1b7d34'
down_revision = '8a1d4f6c92e7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projeto', sa.Column('criado_por_id', sa.Integer(), nullable=True))
    op.add_column('projeto', sa.Column('motivo_reprovacao', sa.Text(), nullable=True))

    op.create_foreign_key(
        "fk_projeto_criado_por_id_usuario",
        "projeto", "usuario",
        ["criado_por_id"], ["id"],
    )

    op.drop_constraint("ck_projeto_status_valido", "projeto", type_="check")
    op.create_check_constraint(
        "ck_projeto_status_valido",
        "projeto",
        "status IN ('ativo', 'inativo', 'encerrado', 'pendente_aprovacao', 'reprovado')",
    )


def downgrade():
    op.drop_constraint("ck_projeto_status_valido", "projeto", type_="check")
    op.create_check_constraint(
        "ck_projeto_status_valido",
        "projeto",
        "status IN ('ativo', 'inativo', 'encerrado')",
    )

    op.drop_constraint("fk_projeto_criado_por_id_usuario", "projeto", type_="foreignkey")
    op.drop_column('projeto', 'motivo_reprovacao')
    op.drop_column('projeto', 'criado_por_id')