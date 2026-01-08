"""add_wins_losses_to_team_selections

Revision ID: ed0b94316806
Revises: 4e7959f9f75b
Create Date: 2026-01-08 09:36:15.929741

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed0b94316806'
down_revision: Union[str, None] = '4e7959f9f75b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add wins and losses columns to team_selections table
    op.add_column('team_selections', sa.Column('wins', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('team_selections', sa.Column('losses', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove wins and losses columns from team_selections table
    op.drop_column('team_selections', 'losses')
    op.drop_column('team_selections', 'wins')
