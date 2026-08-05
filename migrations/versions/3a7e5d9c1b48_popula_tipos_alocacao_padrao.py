"""popula tipos de alocacao padrao

Revision ID: 3a7e5d9c1b48
Revises: 8f3d6c2e5a91
Create Date: 2026-08-01 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a7e5d9c1b48'
down_revision = '8f3d6c2e5a91'
branch_labels = None
depends_on = None

TIPOS_PADRAO = [
    "Material de Consumo",
    "Diárias e Passagens",
    "Equipamento",
    "Serviços de Terceiros",
    "Publicação e Divulgação",
    "Bolsas",
    "Outros",
]


def upgrade():
    conexao = op.get_bind()
    for nome in TIPOS_PADRAO:
        conexao.execute(
            sa.text(
                "INSERT INTO tipo_alocacao (nome, ativo) VALUES (:nome, true) "
                "ON CONFLICT (nome) DO NOTHING"
            ),
            {"nome": nome},
        )


def downgrade():
    conexao = op.get_bind()
    for nome in TIPOS_PADRAO:
        conexao.execute(
            sa.text("DELETE FROM tipo_alocacao WHERE nome = :nome"),
            {"nome": nome},
        )