"""Add is_moderator to User model

Revision ID: fb4cc42329d0
Revises: dc83e21db708
Create Date: 2024-06-30 23:45:55.452648

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fb4cc42329d0'
down_revision = 'dc83e21db708'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_moderator', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('is_moderator')

    # ### end Alembic commands ###
