"""Alembic environment configuration for async SQLAlchemy."""

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import settings and base
from src.config import settings
from src.database import Base

# Import all models to ensure they are registered with Base.metadata
# Only import models that are actually implemented and required for auth
from src.users.models import User
from src.companies.models import Company
from src.permissions.models import Role, UserRoleAssignment
from src.employees.models import Employee  # Required for User.employee relationship
from src.salaries.models import BankInfo, SalaryDetails, SalaryPayment, SalaryHistory  # F-006 Salary Management
from src.projects.models import Project  # F-007 Project Management
from src.tasks.models import Task, TaskAssignment  # F-008 Task Management
from src.leaves.models import LeaveRequest  # F-009 Leave Management
from src.notifications.models import Notification  # F-003 Notifications
from src.attendance.models import Attendance, AttendanceLog  # F-010 Attendance Management
from src.audits.models import AuditLog  # F-011 Audit Logging & Activity History
from src.reports.models import Export  # F-012 Part B: Export Functionality for Reports & Analytics
# TODO: Import other models when they are implemented:
# from src.dashboards.models import Dashboard

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# CRITICAL: For offline migrations, remove +asyncpg (Alembic needs sync URL)
# For online migrations, keep +asyncpg for async engine
if context.is_offline_mode():
    database_url = settings.database_url.replace("+asyncpg", "")
else:
    database_url = settings.database_url  # Keep +asyncpg for async engine
config.set_main_option("sqlalchemy.url", database_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Ensure we use async URL with +asyncpg for async engine
    async_database_url = settings.database_url
    if "+asyncpg" not in async_database_url:
        async_database_url = async_database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Create async engine for online migrations
    connectable = async_engine_from_config(
        {"sqlalchemy.url": async_database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def run_async_migrations() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    def do_run_migrations(connection: Connection) -> None:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
