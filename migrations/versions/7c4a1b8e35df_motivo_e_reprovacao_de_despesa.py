"""motivo e reprovacao de despesa

Revision ID: 7c4a1b8e35df
Revises: e2a7c9f14d68
Create Date: 2026-08-02 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c4a1b8e35df'
down_revision = 'e2a7c9f14d68'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('despesa', sa.Column('motivo_status', sa.Text(), nullable=True))

    op.drop_constraint("ck_despesa_status_valido", "despesa", type_="check")
    op.create_check_constraint(
        "ck_despesa_status_valido",
        "despesa",
        "status IN ('lancada', 'estornada', 'reprovada')",
    )


def downgrade():
    op.drop_constraint("ck_despesa_status_valido", "despesa", type_="check")
    op.create_check_constraint(
        "ck_despesa_status_valido",
        "despesa",
        "status IN ('lancada', 'estornada')",
    )
    op.drop_column('despesa', 'motivo_status')