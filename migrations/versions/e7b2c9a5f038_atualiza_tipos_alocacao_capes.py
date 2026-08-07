"""atualiza tipos de alocacao para classificacao CAPES/CNPq

Revision ID: e7b2c9a5f038
Revises: d5c8a24f19b7
Create Date: 2026-08-04 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e7b2c9a5f038'
down_revision = 'd5c8a24f19b7'
branch_labels = None
depends_on = None

RENOMEACOES = {
    "Diárias": "Diárias – Nacional",
    "Passagens": "Passagens e Despesas com Locomoção",
    "Equipamento": "Equipamentos e Material Permanente",
    "Combustível": "Material de Consumo - combustível",
    "Serviços de Terceiros": "Outros Serviços de Terceiros – Pessoa Jurídica",
}

NOVOS = [
    ("Diárias - Internacional", "custeio"),
    ("Auxílio Financeiro a Estudantes", "custeio"),
    ("Auxílio Financeiro a Pesquisadores", "custeio"),
    ("Outros Serviços de Terceiros – Pessoa Física", "custeio"),
    ("Obras e Instalações", "capital"),
    ("Serviços de TIC – PJ (software, licenças de caráter permanente)", "capital"),
    ("Aquisição de Imóveis", "capital"),
]

INATIVAR = ["Bolsas", "Publicação e Divulgação", "Outros"]


def upgrade():
    conexao = op.get_bind()

    for nome_antigo, nome_novo in RENOMEACOES.items():
        conexao.execute(
            sa.text("UPDATE tipo_alocacao SET nome = :novo WHERE nome = :antigo"),
            {"novo": nome_novo, "antigo": nome_antigo},
        )

    for nome, categoria in NOVOS:
        conexao.execute(
            sa.text(
                "INSERT INTO tipo_alocacao (nome, ativo, categoria_padrao) "
                "VALUES (:nome, true, :categoria) ON CONFLICT (nome) DO NOTHING"
            ),
            {"nome": nome, "categoria": categoria},
        )

    for nome in INATIVAR:
        conexao.execute(
            sa.text("UPDATE tipo_alocacao SET ativo = false WHERE nome = :nome"),
            {"nome": nome},
        )


def downgrade():
    conexao = op.get_bind()

    for nome in INATIVAR:
        conexao.execute(
            sa.text("UPDATE tipo_alocacao SET ativo = true WHERE nome = :nome"),
            {"nome": nome},
        )

    for nome, _categoria in NOVOS:
        conexao.execute(sa.text("DELETE FROM tipo_alocacao WHERE nome = :nome"), {"nome": nome})

    for nome_antigo, nome_novo in RENOMEACOES.items():
        conexao.execute(
            sa.text("UPDATE tipo_alocacao SET nome = :antigo WHERE nome = :novo"),
            {"antigo": nome_antigo, "novo": nome_novo},
        )