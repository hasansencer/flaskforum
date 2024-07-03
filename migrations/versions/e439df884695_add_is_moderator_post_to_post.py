"""Add is_moderator_post to Post

Revision ID: e439df884695
Revises: 36f8ae9b1727
Create Date: 2024-07-01 01:32:54.965707

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e439df884695'
down_revision = '36f8ae9b1727'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_moderator_post', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.drop_column('is_moderator_post')

    # ### end Alembic commands ###