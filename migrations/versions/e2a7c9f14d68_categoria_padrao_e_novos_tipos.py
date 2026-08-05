"""categoria padrao e novos tipos de alocacao

Revision ID: e2a7c9f14d68
Revises: 9f1c4e7a2b56
Create Date: 2026-08-02 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2a7c9f14d68'
down_revision = '9f1c4e7a2b56'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tipo_alocacao', sa.Column('categoria_padrao', sa.String(length=10), nullable=True))

    conexao = op.get_bind()

    # "Diárias e Passagens" vira só "Diárias" (renomeia em vez de apagar, pra
    # preservar as alocações que já apontam pra esse tipo_alocacao_id).
    conexao.execute(
        sa.text("UPDATE tipo_alocacao SET nome = :novo WHERE nome = :antigo"),
        {"novo": "Diárias", "antigo": "Diárias e Passagens"},
    )

    # Tipos novos.
    for nome in ("Passagens", "Combustível"):
        conexao.execute(
            sa.text("INSERT INTO tipo_alocacao (nome, ativo) VALUES (:nome, true) "
                    "ON CONFLICT (nome) DO NOTHING"),
            {"nome": nome},
        )

    # Categoria sugerida de cada tipo padrão.
    mapa_categoria = {
        "Material de Consumo": "custeio",
        "Diárias": "custeio",
        "Passagens": "custeio",
        "Equipamento": "capital",
        "Serviços de Terceiros": "custeio",
        "Publicação e Divulgação": "custeio",
        "Bolsas": "custeio",
        "Outros": "custeio",
        "Combustível": "custeio",
    }
    for nome, categoria in mapa_categoria.items():
        conexao.execute(
            sa.text("UPDATE tipo_alocacao SET categoria_padrao = :categoria WHERE nome = :nome"),
            {"categoria": categoria, "nome": nome},
        )


def downgrade():
    conexao = op.get_bind()
    conexao.execute(sa.text("DELETE FROM tipo_alocacao WHERE nome IN ('Passagens', 'Combustível')"))
    conexao.execute(
        sa.text("UPDATE tipo_alocacao SET nome = :antigo WHERE nome = :novo"),
        {"antigo": "Diárias e Passagens", "novo": "Diárias"},
    )
    op.drop_column('tipo_alocacao', 'categoria_padrao')