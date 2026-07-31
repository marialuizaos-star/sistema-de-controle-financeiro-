"""adiciona papel_projeto na alocacao

Revision ID: 4e8b1f7a9c3d
Revises: 7d4a9c15e8b2
Create Date: 2026-07-31 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4e8b1f7a9c3d'
down_revision = '7d4a9c15e8b2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('alocacao', sa.Column('papel_projeto', sa.String(length=20), nullable=True))
    op.create_check_constraint(
        "ck_alocacao_papel_projeto_valido",
        "alocacao",
        "papel_projeto IS NULL OR papel_projeto IN "
        "('coordenador', 'pesquisador', 'bolsista', 'tecnico', 'colaborador')",
    )


def downgrade():
    op.drop_constraint("ck_alocacao_papel_projeto_valido", "alocacao", type_="check")
    op.drop_column('alocacao', 'papel_projeto')