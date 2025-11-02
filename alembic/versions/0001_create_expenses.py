"""create expenses table

Revision ID: 0001_create_expenses
Revises: 
Create Date: 2025-10-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_create_expenses'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('tx_date', sa.Date(), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('payer', sa.String(length=100), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table('expenses')
