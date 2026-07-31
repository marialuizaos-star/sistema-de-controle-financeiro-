"""adiciona departamento e ultimo_acesso ao usuario

Revision ID: 7d4a9c15e8b2
Revises: 2f7b8e91a4c6
Create Date: 2026-07-31 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d4a9c15e8b2'
down_revision = '2f7b8e91a4c6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('usuario', sa.Column('departamento', sa.String(length=150), nullable=True))
    op.add_column('usuario', sa.Column('ultimo_acesso', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('usuario', 'ultimo_acesso')
    op.drop_column('usuario', 'departamento')