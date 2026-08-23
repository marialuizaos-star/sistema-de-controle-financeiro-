"""permite categoria ambos no projeto

Revision ID: 9f2a3b7d1c44
Revises: 9d4e7f2a8c15
Create Date: 2026-08-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f2a3b7d1c44'
down_revision = '9d4e7f2a8c15'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_projeto_categoria_valida", "projeto", type_="check")
    op.create_check_constraint(
        "ck_projeto_categoria_valida",
        "projeto",
        "categoria IS NULL OR categoria IN ('custeio', 'capital', 'ambos')",
    )


def downgrade():
    op.drop_constraint("ck_projeto_categoria_valida", "projeto", type_="check")
    op.create_check_constraint(
        "ck_projeto_categoria_valida",
        "projeto",
        "categoria IS NULL OR categoria IN ('custeio', 'capital')",
    )