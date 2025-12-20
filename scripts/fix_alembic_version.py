"""Fix Alembic version table after removing empty migration."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix_alembic_version():
    """Update alembic_version table to point to 001_initial."""
    engine = create_async_engine("postgresql+asyncpg://postgres:1112@db:5432/office_world")
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE alembic_version SET version_num = '001_initial'"))
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        print(f"Alembic version updated to: {version}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_alembic_version())

