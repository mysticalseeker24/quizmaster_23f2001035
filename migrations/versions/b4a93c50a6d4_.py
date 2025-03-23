"""Add Score table

Revision ID: b4a93c50a6d4
Revises: None
Create Date: 2025-03-23 14:00:00

"""
from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = 'b4a93c50a6d4'
down_revision = None  # Set this to the previous revision ID if applicable
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'score',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['quiz_id'], ['quiz.id']),
        sa.PrimaryKeyConstraint('id')
    )



def downgrade():
    # Drop the Score table
    op.drop_table('score')
