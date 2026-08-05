"""documentos obrigatorios por tipo de alocacao

Revision ID: b6e3d8f27a45
Revises: 4d8a2f6b91ce
Create Date: 2026-08-02 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b6e3d8f27a45'
down_revision = '4d8a2f6b91ce'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tipo_alocacao', sa.Column('documentos_obrigatorios', sa.Text(), nullable=True))

    conexao = op.get_bind()
    textos = {
        "Diárias": "Obrigatório anexar Relatório de Viagem e/ou Declaração de Diárias.",
        "Passagens": "Obrigatório anexar Canhoto de Embarque e Nota Fiscal da passagem.",
        "Combustível": "Obrigatório anexar Nota Fiscal com placa do veículo e comprovante de abastecimento.",
    }
    for nome, texto in textos.items():
        conexao.execute(
            sa.text("UPDATE tipo_alocacao SET documentos_obrigatorios = :texto WHERE nome = :nome"),
            {"texto": texto, "nome": nome},
        )


def downgrade():
    op.drop_column('tipo_alocacao', 'documentos_obrigatorios')