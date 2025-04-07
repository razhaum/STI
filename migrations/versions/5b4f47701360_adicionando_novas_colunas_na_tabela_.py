"""Adicionando novas colunas na tabela solicitacao

Revision ID: 5b4f47701360
Revises: fd36278c81dd
Create Date: 2025-04-01 20:29:26.069814

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b4f47701360'
down_revision = 'fd36278c81dd'
branch_labels = None
depends_on = None


def upgrade():
    # Verifica primeiro, e cria a coluna somente se não existir ainda
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column['name'] for column in inspector.get_columns('solicitacao')]

    with op.batch_alter_table('solicitacao', schema=None) as batch_op:
        if 'classe' not in columns:
            batch_op.add_column(sa.Column('classe', sa.String(length=100), nullable=True))
            op.execute("UPDATE solicitacao SET classe = 'valor_padrao' WHERE classe IS NULL")
            batch_op.alter_column('classe', nullable=False)


def downgrade():
    with op.batch_alter_table('solicitacao', schema=None) as batch_op:
        batch_op.drop_column('classe')

    # ### end Alembic commands ###
