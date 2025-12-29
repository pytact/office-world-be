"""Fix salary_details effective_from constraint

Revision ID: 013_fix_salary_constraint
Revises: 012_f9_leave_management
Create Date: 2025-01-25 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '013_fix_salary_constraint'
down_revision: Union[str, None] = '012_f9_leave_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix chk_salary_details_effective_from constraint to only apply to active records.
    
    The constraint 'effective_from >= CURRENT_DATE' should only apply to active records
    (where effective_to IS NULL). Historical records (where effective_to IS NOT NULL)
    should be exempt from this constraint since they represent past salary configurations.
    
    Changes:
    - Drop the old constraint first (to allow data fixes)
    - Fix existing data: Close any active records with effective_from < CURRENT_DATE
    - Add new constraint: (effective_to IS NULL AND effective_from >= CURRENT_DATE) OR (effective_to IS NOT NULL)
    """
    # Step 1: Drop the old constraint first (allows us to update rows with past dates)
    op.drop_constraint('chk_salary_details_effective_from', 'salary_details', type_='check')
    
    # Step 2: Fix existing data - close any active records (effective_to IS NULL) 
    # that have effective_from < CURRENT_DATE by setting effective_to = effective_from
    # This makes them historical records, which are exempt from the date constraint
    op.execute("""
        UPDATE salary_details 
        SET effective_to = effective_from,
            updated_at = NOW()
        WHERE effective_to IS NULL 
          AND effective_from < CURRENT_DATE
    """)
    
    # Step 3: Add the new constraint that only applies to active records
    op.create_check_constraint(
        'chk_salary_details_effective_from',
        'salary_details',
        "(effective_to IS NULL AND effective_from >= CURRENT_DATE) OR (effective_to IS NOT NULL)",
    )


def downgrade() -> None:
    """Revert the constraint change."""
    # Drop the new constraint
    op.drop_constraint('chk_salary_details_effective_from', 'salary_details', type_='check')
    
    # Restore the old constraint
    op.create_check_constraint(
        'chk_salary_details_effective_from',
        'salary_details',
        'effective_from >= CURRENT_DATE',
    )

