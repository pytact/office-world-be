"""Remove ACTIVE from employment_status constraint

Revision ID: 010_remove_active_status
Revises: 009_f7_project_management
Create Date: 2025-01-XX 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '010_remove_active_status'
down_revision: Union[str, None] = '009_f7_project_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove 'ACTIVE' from employment_status constraint.
    
    Before removing the constraint, update any existing employees with
    'ACTIVE' status to 'PROBATION' (default for new invites).
    Then drop the old constraint and create a new one without 'ACTIVE'.
    """
    # First, update any existing employees with 'ACTIVE' status to 'PROBATION'
    op.execute("""
        UPDATE employees 
        SET employment_status = 'PROBATION'
        WHERE employment_status = 'ACTIVE'
    """)
    
    # Drop the existing constraint
    op.drop_constraint(
        'chk_employees_employment_status',
        'employees',
        type_='check'
    )
    
    # Create new constraint without 'ACTIVE' using raw SQL
    op.execute("""
        ALTER TABLE employees 
        ADD CONSTRAINT chk_employees_employment_status 
        CHECK (employment_status IN ('TRAINEE', 'PROBATION', 'CONFIRMED', 'NOTICE_PERIOD', 'ON_HOLD', 'TERMINATED', 'RESIGNED'))
    """)


def downgrade() -> None:
    """Restore 'ACTIVE' to employment_status constraint.
    
    Drop the constraint and recreate it with 'ACTIVE' included.
    Note: We don't restore 'ACTIVE' status to employees that were changed,
    as we can't determine which ones should be restored.
    """
    # Drop the constraint
    op.drop_constraint(
        'chk_employees_employment_status',
        'employees',
        type_='check'
    )
    
    # Recreate constraint with 'ACTIVE' included using raw SQL
    op.execute("""
        ALTER TABLE employees 
        ADD CONSTRAINT chk_employees_employment_status 
        CHECK (employment_status IN ('TRAINEE', 'PROBATION', 'CONFIRMED', 'NOTICE_PERIOD', 'ACTIVE', 'ON_HOLD', 'TERMINATED', 'RESIGNED'))
    """)

