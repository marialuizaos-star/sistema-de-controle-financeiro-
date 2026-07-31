"""adiciona solicitação de remanejamento de verba

Revision ID: 2f7b8e91a4c6
Revises: 9c2e5a1b7d34
Create Date: 2026-07-30 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f7b8e91a4c6'
down_revision = '9c2e5a1b7d34'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'solicitacao_remanejamento',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('projeto_id', sa.Integer(), nullable=False),
        sa.Column('alocacao_origem_id', sa.Integer(), nullable=False),
        sa.Column('alocacao_destino_id', sa.Integer(), nullable=False),
        sa.Column('valor', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('justificativa', sa.Text(), nullable=True),
        sa.Column('motivo_reprovacao', sa.Text(), nullable=True),
        sa.Column('solicitado_por_id', sa.Integer(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('valor >= 0', name='ck_remanejamento_valor_positivo'),
        sa.CheckConstraint(
            "status IN ('pendente', 'aprovado', 'reprovado')",
            name='ck_remanejamento_status_valido',
        ),
        sa.CheckConstraint(
            'alocacao_origem_id != alocacao_destino_id',
            name='ck_remanejamento_origem_destino_diferentes',
        ),
        sa.ForeignKeyConstraint(['projeto_id'], ['projeto.id']),
        sa.ForeignKeyConstraint(['alocacao_origem_id'], ['alocacao.id']),
        sa.ForeignKeyConstraint(['alocacao_destino_id'], ['alocacao.id']),
        sa.ForeignKeyConstraint(['solicitado_por_id'], ['usuario.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('solicitacao_remanejamento')