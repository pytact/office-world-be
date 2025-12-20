"""Seed script to insert superadmin user into the users table."""
import asyncio
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, func
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.config import settings
from src.users.models import User
from src.permissions.models import Role, UserRoleAssignment
from src.auth.utils import get_password_hash

# Ensure models are registered so relationships resolve
import src.permissions.models  # noqa: F401
import src.companies.models  # noqa: F401 - Required for UserRoleAssignment.company relationship

# Default superadmin credentials (can be overridden via environment variables)
DEFAULT_EMAIL = os.getenv("SUPERADMIN_EMAIL", "superadmin@df.com")
DEFAULT_PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "SuperAdmin@123")


async def check_tables_exist(session: AsyncSession) -> bool:
    """Check if database tables exist."""
    try:
        await session.execute(select(func.count()).select_from(User))
        return True
    except ProgrammingError as e:
        error_str = str(e).lower()
        if "does not exist" in error_str or "relation" in error_str:
            return False
        raise


async def seed_superadmin() -> None:
    """Seed superadmin user into the database."""
    print("=" * 60)
    print("Superadmin Seeding Script")
    print("=" * 60)
    print(f"\nDatabase URL: {settings.database_url.split('@')[0]}@***")  # Hide password
    print(f"Environment: {settings.environment}")

    # Create async engine using project settings
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
    )

    # Create async session maker
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with async_session() as session:
            # Check if tables exist
            print("\nChecking if database tables exist...")
            if not await check_tables_exist(session):
                print("⚠️  Database tables don't exist yet. Please run migrations first:")
                print("   alembic upgrade head")
                print("\n   Then run this script again:")
                print("   docker compose exec api python scripts/seed_superadmin.py")
                print("\n   Or locally:")
                print("   python scripts/seed_superadmin.py")
                return

            # Check if superadmin user already exists (not soft-deleted)
            print("\nChecking for existing superadmin user...")
            result = await session.execute(
                select(User).where(
                    User.email == DEFAULT_EMAIL,
                    User.deleted_at.is_(None),
                )
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"  ✅ Superadmin user with email '{DEFAULT_EMAIL}' already exists.")
                print(f"     User ID: {existing_user.id}")
                print(f"     Status: {'Active' if existing_user.is_active else 'Inactive'}")
                
                # Check if UserRoleAssignment exists
                user_role_result = await session.execute(
                    select(UserRoleAssignment).where(
                        UserRoleAssignment.user_id == existing_user.id,
                        UserRoleAssignment.deleted_at.is_(None),
                    )
                )
                existing_user_role = user_role_result.scalar_one_or_none()
                
                if existing_user_role:
                    print(f"  ✅ UserRoleAssignment already assigned.")
                else:
                    print(f"  ⚠️  UserRoleAssignment not found. Creating UserRoleAssignment...")
                    # Get superadmin role
                    role_result = await session.execute(
                        select(Role).where(
                            Role.name == "SuperAdmin",
                            Role.deleted_at.is_(None),
                        )
                    )
                    superadmin_role = role_result.scalar_one_or_none()

                    if not superadmin_role:
                        raise ValueError(
                            "SuperAdmin role not found. Please run seed_role.py first to create roles."
                        )
                    
                    # Create UserRoleAssignment entry (superadmin has NULL company_id)
                    new_user_role = UserRoleAssignment(
                        user_id=existing_user.id,
                        company_id=None,  # SuperAdmin has no company
                        role_id=superadmin_role.id,
                        is_active=True,
                        created_by=None,
                        updated_by=None,
                    )
                    session.add(new_user_role)
                    await session.flush()
                    print(f"  ✅ Created UserRoleAssignment for superadmin user.")
                
                await session.commit()
                print("\n" + "=" * 60)
                print("✅ Superadmin user already exists!")
                print("=" * 60)
                print(f"\nEmail: {DEFAULT_EMAIL}")
                print(f"Password: {DEFAULT_PASSWORD}")
                return

            # Get superadmin role
            print("\nFetching SuperAdmin role...")
            role_result = await session.execute(
                select(Role).where(
                    Role.name == "SuperAdmin",
                    Role.deleted_at.is_(None),
                )
            )
            superadmin_role = role_result.scalar_one_or_none()

            if not superadmin_role:
                raise ValueError(
                    "SuperAdmin role not found. Please run seed_role.py first to create roles."
                )
            print(f"  ✅ Found SuperAdmin role (id: {superadmin_role.id})")

            # Hash password
            print("\nCreating superadmin user...")
            hashed_password = get_password_hash(DEFAULT_PASSWORD)

            # Create superadmin user
            now = datetime.now(timezone.utc)
            new_user = User(
                email=DEFAULT_EMAIL,
                first_name="Super",
                last_name="Admin",
                password=hashed_password,
                is_active=True,
                is_deleted=False,
                activate_at=now,
                invite_at=None,
                expiry=None,
                token=None,
                created_by=None,  # First user, no creator
                updated_by=None,
            )
            session.add(new_user)
            await session.flush()  # Flush to get the user ID
            print(f"  ✅ Created superadmin user: {DEFAULT_EMAIL} (id: {new_user.id})")

            # Create UserRoleAssignment entry (superadmin has NULL company_id)
            print("\nAssigning SuperAdmin role...")
            new_user_role = UserRoleAssignment(
                user_id=new_user.id,
                company_id=None,  # SuperAdmin has no company
                role_id=superadmin_role.id,
                is_active=True,
                created_by=None,
                updated_by=None,
            )
            session.add(new_user_role)
            await session.flush()
            print(f"  ✅ Assigned SuperAdmin role to user: {DEFAULT_EMAIL}")

            # Commit all changes
            await session.commit()

            print("\n" + "=" * 60)
            print("✅ Superadmin seeded successfully!")
            print("=" * 60)
            print(f"\nUser Details:")
            print(f"  - Email: {DEFAULT_EMAIL}")
            print(f"  - Password: {DEFAULT_PASSWORD}")
            print(f"  - User ID: {new_user.id}")
            print(f"  - Status: {'Active' if new_user.is_active else 'Inactive'}")
            print(f"  - Role: SuperAdmin")
            print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ Error seeding superadmin: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


async def main() -> None:
    """Main function to run the seeding script."""
    await seed_superadmin()


if __name__ == "__main__":
    asyncio.run(main())

