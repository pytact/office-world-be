"""Add password field to users

Revision ID: 003_add_password
Revises: 002_add_reinvite
Create Date: 2024-12-20 04:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_add_password'
down_revision: Union[str, None] = '002_add_reinvite'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Try to alter the column if it exists, otherwise add it
    # This handles the case where password column was created in initial migration
    try:
        # Column exists, alter it to be nullable (for invitation-based onboarding)
        op.alter_column('users', 'password',
                       existing_type=sa.String(length=255),
                       nullable=True)
    except Exception:
        # Column doesn't exist, add it
        op.add_column('users', sa.Column('password', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Alter password column back to nullable=False (matching initial migration)
    # Note: We don't drop the column since it was in the initial migration
    try:
        op.alter_column('users', 'password',
                       existing_type=sa.String(length=255),
                       nullable=False)
    except Exception:
        # Column doesn't exist, nothing to do
        pass

