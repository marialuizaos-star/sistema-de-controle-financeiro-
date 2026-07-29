"""recria constraint de status do projeto

Revision ID: 6f3c22f04588
Revises: 714d05335617
Create Date: 2026-07-28 18:35:07.029066

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6f3c22f04588'
down_revision = '714d05335617'
branch_labels = None
depends_on = None


def upgrade():
    op.create_check_constraint(
        "ck_projeto_status_valido",
        "projeto",
        "status IN ('ativo', 'inativo', 'encerrado')",
    )


def downgrade():
    op.drop_constraint("ck_projeto_status_valido", "projeto", type_="check")