"""adiciona prestacao de contas

Revision ID: 9f1c4e7a2b56
Revises: 6b2f8a3d7e19
Create Date: 2026-08-02 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f1c4e7a2b56'
down_revision = '6b2f8a3d7e19'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projeto', sa.Column('status_prestacao_contas', sa.String(length=20), nullable=True))
    op.add_column('projeto', sa.Column('motivo_reprovacao_prestacao', sa.Text(), nullable=True))
    op.add_column('projeto', sa.Column('enviada_em_prestacao', sa.DateTime(timezone=True), nullable=True))

    op.create_check_constraint(
        "ck_projeto_status_prestacao_contas_valido",
        "projeto",
        "status_prestacao_contas IS NULL OR status_prestacao_contas IN "
        "('em_analise', 'aceita', 'reprovada')",
    )


def downgrade():
    op.drop_constraint("ck_projeto_status_prestacao_contas_valido", "projeto", type_="check")
    op.drop_column('projeto', 'enviada_em_prestacao')
    op.drop_column('projeto', 'motivo_reprovacao_prestacao')
    op.drop_column('projeto', 'status_prestacao_contas')