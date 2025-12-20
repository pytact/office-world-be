"""Add reinvite fields to users

Revision ID: 002_add_reinvite
Revises: 001_initial
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_reinvite'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add reinvite_count column
    op.add_column('users', sa.Column('reinvite_count', sa.Integer(), nullable=False, server_default='0'))
    
    # Add last_reinvite_at column
    op.add_column('users', sa.Column('last_reinvite_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add check constraint for reinvite_count
    op.create_check_constraint(
        'chk_users_reinvite_count',
        'users',
        'reinvite_count >= 0'
    )
    
    # Update token column type from UUID to String (if needed)
    # Check if token column exists and is UUID type
    # Note: This might need adjustment based on your actual database state
    # op.alter_column('users', 'token', type_=sa.String(length=255), existing_type=postgresql.UUID(as_uuid=True))


def downgrade() -> None:
    # Drop check constraint
    op.drop_constraint('chk_users_reinvite_count', 'users', type_='check')
    
    # Drop columns
    op.drop_column('users', 'last_reinvite_at')
    op.drop_column('users', 'reinvite_count')

