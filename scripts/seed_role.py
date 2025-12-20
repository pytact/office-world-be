"""Seed script to insert roles into the roles table."""
import asyncio
import sys
import traceback
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, func
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.config import settings
from src.permissions.models import Role

# Ensure models are registered so relationships resolve
import src.users.models  # noqa: F401
import src.companies.models  # noqa: F401 - Required for UserRoleAssignment.company relationship


async def check_tables_exist(session: AsyncSession) -> bool:
    """Check if database tables exist."""
    try:
        await session.execute(select(func.count()).select_from(Role))
        return True
    except ProgrammingError as e:
        error_str = str(e).lower()
        if "does not exist" in error_str or "relation" in error_str:
            return False
        raise


# Role definitions with permissions
ROLES_DATA = [
    {
        "name": "SuperAdmin",
        "code": "SuperAdmin",
        "permissions": {
            "companies": ["create", "read", "update", "delete"],
            "users": ["create", "read", "update", "delete"],
            "users_roles": ["create", "read", "update", "delete"],
            "roles": ["read"],
            "kpis": ["read"],
        },
    },
    {
        "name": "CEO",
        "code": "CEO",
        "permissions": {
            "employees": ["create", "read", "update", "delete"],
            "salary": ["create", "read", "update", "delete"],
            "salary_history": ["read"],
            "projects": ["create", "read", "update", "delete"],
            "tasks": ["create", "read", "update", "delete"],
            "task_assignments": ["create", "read", "update", "delete"],
            "attendance": ["read"],
            "leaves": ["read", "approve"],
            "holidays": ["create", "read", "update", "delete"],
            "users_roles": ["create", "read", "update"],
            "kpis": ["read"],
        },
    },
    {
        "name": "HR",
        "code": "HR",
        "permissions": {
            "employees": ["create", "read", "update"],
            "salary": ["create", "read", "update", "delete"],
            "salary_history": ["read"],
            "attendance": ["read"],
            "leaves": ["read", "approve"],
            "holidays": ["create", "read", "update", "delete"],
            "users_roles": ["create", "read", "update"],
        },
    },
    {
        "name": "Manager",
        "code": "Manager",
        "permissions": {
            "employees": ["read"],
            "projects": ["create", "read", "update", "delete"],
            "tasks": ["create", "read", "update", "delete"],
            "task_assignments": ["create", "read", "update", "delete"],
            "attendance": ["read"],
            "leaves": ["read", "approve"],
            "kpis": ["read"],
        },
    },
    {
        "name": "Employee",
        "code": "Employee",
        "permissions": {
            "employees": ["read", "update"],
            "tasks": ["read", "update"],
            "task_assignments": ["create", "read"],
            "leaves": ["create", "read"],
            "attendance": ["create", "read"],
            "holidays": ["read"],
            "salary": ["read"],
        },
    },
]


async def seed_roles() -> None:
    """Seed roles into the database."""
    print("=" * 60)
    print("Roles Seeding Script")
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
                print("   docker compose exec api python scripts/seed_role.py")
                print("\n   Or locally:")
                print("   python scripts/seed_role.py")
                return

            print("\nCreating/updating roles...")
            created_roles = []

            for role_data in ROLES_DATA:
                try:
                    # Check if role already exists (not soft-deleted)
                    result = await session.execute(
                        select(Role).where(
                            Role.name == role_data["name"],
                            Role.deleted_at.is_(None),
                        )
                    )
                    existing_role = result.scalar_one_or_none()

                    if existing_role:
                        # Update existing role if permissions or code changed
                        updated = False
                        if existing_role.permissions != role_data["permissions"]:
                            existing_role.permissions = role_data["permissions"]
                            updated = True
                        if existing_role.code != role_data["code"]:
                            existing_role.code = role_data["code"]
                            updated = True

                        if updated:
                            await session.flush()
                            print(f"  ✅ Updated role: {role_data['name']} (code: {role_data['code']})")
                        else:
                            print(f"  ✅ Role already exists: {role_data['name']} (code: {role_data['code']})")
                        created_roles.append(existing_role)
                    else:
                        # Create new role
                        # Explicitly set audit fields to None for seeding (no users exist yet)
                        new_role = Role(
                            name=role_data["name"],
                            code=role_data["code"],
                            permissions=role_data["permissions"],
                            created_by=None,
                            updated_by=None,
                        )
                        session.add(new_role)
                        await session.flush()
                        print(f"  ✅ Created role: {role_data['name']} (code: {role_data['code']})")
                        created_roles.append(new_role)

                except Exception as e:
                    await session.rollback()
                    print(f"  ❌ Error creating role {role_data['name']}: {e}")
                    raise

            # Commit all changes
            await session.commit()

            print("\n" + "=" * 60)
            print("✅ Roles created/updated successfully!")
            print("=" * 60)
            print(f"\nCreated/Updated Roles:")
            for role in created_roles:
                print(f"  - {role.name} (id: {role.id})")
            print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ Error seeding roles: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


async def main() -> None:
    """Main function to run the seeding script."""
    await seed_roles()


if __name__ == "__main__":
    asyncio.run(main())

