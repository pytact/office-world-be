"""Add F4 company profile fields and is_deleted

Revision ID: 005_f4_company_fields
Revises: 004_add_f2_indexes
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_f4_company_fields'
down_revision: Union[str, None] = '004_add_f2_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add F4 company profile fields and is_deleted field.
    
    Based on F4_api_spec.md - Platform Company Management (F-004).
    Adds profile fields (description, address, city, state, country, postal_code, website, logo_url)
    and is_deleted field for visibility (hard deletion per F4 spec).
    """
    # Add profile fields (editable by CEO/HR when company is active)
    op.add_column('companies', sa.Column('description', sa.String(length=1000), nullable=True))
    op.add_column('companies', sa.Column('address', sa.String(length=255), nullable=True))
    op.add_column('companies', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('companies', sa.Column('state', sa.String(length=100), nullable=True))
    op.add_column('companies', sa.Column('country', sa.String(length=100), nullable=True))
    op.add_column('companies', sa.Column('postal_code', sa.String(length=20), nullable=True))
    op.add_column('companies', sa.Column('website', sa.String(length=2048), nullable=True))
    op.add_column('companies', sa.Column('logo_url', sa.String(length=2048), nullable=True))
    
    # Add is_deleted field (for visibility - hard deletion per F4 spec)
    op.add_column('companies', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add check constraint for is_deleted
    op.create_check_constraint(
        'chk_companies_is_deleted',
        'companies',
        "is_deleted IN (true, false)"
    )


def downgrade() -> None:
    """Remove F4 company profile fields and is_deleted field."""
    # Drop check constraint
    op.drop_constraint('chk_companies_is_deleted', 'companies', type_='check')
    
    # Drop columns
    op.drop_column('companies', 'is_deleted')
    op.drop_column('companies', 'logo_url')
    op.drop_column('companies', 'website')
    op.drop_column('companies', 'postal_code')
    op.drop_column('companies', 'country')
    op.drop_column('companies', 'state')
    op.drop_column('companies', 'city')
    op.drop_column('companies', 'address')
    op.drop_column('companies', 'description')

