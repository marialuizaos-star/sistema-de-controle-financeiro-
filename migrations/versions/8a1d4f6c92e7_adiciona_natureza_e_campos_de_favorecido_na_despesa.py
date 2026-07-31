"""adiciona natureza e campos de favorecido na despesa

Revision ID: 8a1d4f6c92e7
Revises: 6f3c22f04588
Create Date: 2026-07-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a1d4f6c92e7'
down_revision = '6f3c22f04588'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'despesa',
        sa.Column('natureza', sa.String(length=12), nullable=False, server_default='custeio'),
    )
    op.add_column('despesa', sa.Column('cnpj_favorecido', sa.String(length=18), nullable=True))
    op.add_column('despesa', sa.Column('numero_comprovante_fiscal', sa.String(length=50), nullable=True))

    op.create_check_constraint(
        "ck_despesa_natureza_valida",
        "despesa",
        "natureza IN ('custeio', 'capital', 'devolucao')",
    )

    # Remove o server_default depois de popular os registros existentes —
    # o valor padrão em novos registros já é garantido pelo default do modelo (Python).
    op.alter_column('despesa', 'natureza', server_default=None)


def downgrade():
    op.drop_constraint("ck_despesa_natureza_valida", "despesa", type_="check")
    op.drop_column('despesa', 'numero_comprovante_fiscal')
    op.drop_column('despesa', 'cnpj_favorecido')
    op.drop_column('despesa', 'natureza')