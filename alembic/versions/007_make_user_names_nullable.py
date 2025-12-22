"""Make user first_name and last_name nullable

Revision ID: 007_make_user_names_nullable
Revises: 006_f5_employee_management
Create Date: 2025-12-22 07:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_make_user_names_nullable'
down_revision: Union[str, None] = '006_f5_employee_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make first_name and last_name nullable in users table.
    
    Based on F1_db_spec.md Section 7.1 - first_name and last_name are set at 
    activation, nullable until activated.
    """
    # Alter first_name column to be nullable
    # Note: Initial migration used length=50, but model uses length=100
    # We'll use the current database length (50) for the alter
    op.alter_column('users', 'first_name',
                    existing_type=sa.String(length=50),
                    nullable=True,
                    existing_nullable=False)
    
    # Alter last_name column to be nullable
    op.alter_column('users', 'last_name',
                    existing_type=sa.String(length=50),
                    nullable=True,
                    existing_nullable=False)


def downgrade() -> None:
    """Revert first_name and last_name to NOT NULL."""
    # Note: This will fail if there are any NULL values in these columns
    op.alter_column('users', 'first_name',
                    existing_type=sa.String(length=50),
                    nullable=False,
                    existing_nullable=True)
    
    op.alter_column('users', 'last_name',
                    existing_type=sa.String(length=50),
                    nullable=False,
                    existing_nullable=True)

