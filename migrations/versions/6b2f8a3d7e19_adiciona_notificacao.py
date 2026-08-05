"""adiciona notificacao

Revision ID: 6b2f8a3d7e19
Revises: 3a7e5d9c1b48
Create Date: 2026-08-02 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6b2f8a3d7e19'
down_revision = '3a7e5d9c1b48'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'notificacao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('mensagem', sa.String(length=255), nullable=False),
        sa.Column('link', sa.String(length=255), nullable=True),
        sa.Column('lida', sa.Boolean(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('notificacao')