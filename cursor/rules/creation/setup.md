# FastAPI Project Setup Guide

**Purpose:** Complete guide for creating FastAPI backend projects following best practices.

**Reference:** https://github.com/zhanymkanov/fastapi-best-practices

---

## RULE 1: Foundation Principles

### 1.1 Primary Reference
- **MUST** follow conventions from `fastapi-best-practices` repository
- **MUST** use it as single source of truth for:
  - Project structure (src/, domain packages, global modules)
  - Async route usage
  - Pydantic usage
  - Dependencies / DI
  - Database / migrations patterns
  - Testing and tooling preferences
- **DO NOT** invent architecture that conflicts with the repo
- If conflict exists, resolve in favor of repo's practices

### 1.2 Module Development Approach
**CRITICAL WARNING:** All module/model names in examples are STRUCTURAL PATTERNS ONLY.

**MANDATORY UNDERSTANDING:**
- Examples like "organizations", "members", "Organization", "Member" are PATTERNS ONLY
- They demonstrate HOW to structure code, NOT WHAT to build
- **NEVER** build example modules unless user explicitly requests them
- **USER PROVIDES** actual module and model names
- Apply PATTERNS to USER'S ACTUAL MODULE/MODEL NAMES

**BEFORE DEVELOPMENT - MUST ASK USER FOR:**
- Module name (e.g., "products", "users", "orders")
- Model name(s) within that module
- Specific requirements or fields for the module
- Database name, user, password
- API title, version, prefix
- Environment name, debug mode
- Celery app name (ONLY if Celery requested)

**DO NOT** proceed with code generation until user provides all required information.

---

## RULE 2: Authentication Module

### 2.1 Default Behavior
- **MANDATORY:** Authentication module MUST be included by default
- **ONLY skip** if user explicitly says: "no auth", "skip auth", "without auth", "don't need auth", "no authentication"
- **If user doesn't mention auth:** Automatically include complete auth module

### 2.2 Authentication Components
When including auth module, MUST include:
- User model with authentication fields (email, password_hash, etc.)
- JWT token generation (access + refresh tokens)
- OAuth2PasswordBearer for Swagger UI
- `/token` endpoint for OAuth2 compatibility
- Password hashing with bcrypt
- Authentication dependencies (`get_current_user`, `get_current_active_user`, role-based access)

**Reference:** See `auth_setup.md` for complete implementation details.

---

## RULE 3: Optional Components

### 3.1 Redis
- **ONLY add** if user says: "add redis", "develop redis", or "include redis"
- **DO NOT add** unless user explicitly requests it
- **Reference:** See `redis_validate.md` for complete setup

### 3.2 Celery
- **ONLY add** if user says: "add celery", "develop celery", or "include celery"
- **DO NOT add** unless user explicitly requests it
- **CRITICAL:** Redis must be set up before Celery (Celery uses Redis as broker)
- **If user requests Celery but Redis not set up:** Ask if they want Redis added first
- **Reference:** See `celery_validate.md` for complete setup

---

## RULE 4: Setup Files Reference

### 4.1 Project Structure
- **File:** `project_structure_validate.md` in rules/validate folder
- **START HERE** - Single source of truth for file structure creation
- **CRITICAL:** Always check if files exist before creating them
- Contains: complete file checklist, creation order, existence checks, verification steps

### 4.2 Authentication Setup
- **File:** `auth_setup.md` in rules/creation folder
- Contains: OAuth2PasswordBearer, JWT tokens, password security, token endpoints, authentication dependencies

### 4.3 Database Setup
- **File:** `database_setup.md` in rules/creation folder
- Contains: database connection, pooling, Alembic migrations, UUID patterns

### 4.4 Domain Architecture
- **File:** `module_architecture_validate.md` in rules/validate folder
- Contains: patterns for models, schemas, repositories, services, routers

### 4.5 Docker Setup
- **File:** `docker_validate.md` in rules/validate folder
- Contains: Dockerfile, docker-compose.yml patterns, health checks, service dependencies

### 4.6 Dependencies Management
- **File:** `dependencies_validate.md` in rules/validate folder
- Contains: requirements structure, critical package dependencies, verification rules

### 4.7 Configuration Setup
- **File:** `config_validate.md` in rules/validate folder
- Contains: BaseSettings setup, environment variables, pydantic-settings requirements

### 4.8 Response and Error Handling
- **File:** `response_error_handling.md` in rules folder
- **CRITICAL:** ALL API responses MUST use `StandardResponse[T]` format
- **CRITICAL:** ALL exceptions MUST extend base exception classes from `src.exceptions`
- Contains: StandardResponse format, exception hierarchy, error handling patterns

### 4.9 Development Build
- **File:** `development_build.md` in rules folder
- Contains: development service configuration, minimal build strategies, hot-reload setup
- **CRITICAL:** During development, only build `db`, `migrate`, and `api` services by default

---

## RULE 5: Development Workflow

### 5.1 Workflow Order (CRITICAL - FOLLOW EXACTLY)

**Step 1: Create Project Structure**
- Refer to `project_structure_validate.md` for complete file structure checklist
- **ALWAYS** check if files/directories exist before creating them
- Report to user which files exist and which need to be created
- Create all directories (src/, alembic/, requirements/, etc.)
- Create all `__init__.py` files
- Create configuration files (.gitignore, logging.ini, etc.)

**Step 1.5: Include Authentication Module (MANDATORY BY DEFAULT)**
- **CRITICAL:** Authentication module MUST be included automatically unless user explicitly says "no auth"
- **If user doesn't mention auth:** Automatically create complete auth module
- **Reference:** See `auth_setup.md` for complete implementation details
- **ONLY skip** if user explicitly requests no authentication

**Step 2: Create Models Before Migrations**
- Create all SQLAlchemy models first
- Ensure models use UUID for primary keys
- Ensure models use `server_default=func.now()` for timestamps
- Verify all relationships are correct

**Step 3: Create Initial Migration ONCE**
- **CRITICAL:** Check if `alembic/versions/` directory exists and has any files
- **If migration files exist:** Review them, use them, DO NOT create new ones
- **If no migration files exist:** Create ONE initial migration manually
- Use descriptive name: `001_initial_migration.py`
- Use simple revision ID: `'001_initial'`
- Set `down_revision: None` for initial migration
- **DO NOT** run `alembic revision --autogenerate` for initial migration
- **DO NOT** create multiple initial migrations

**Step 4: Create Requirements Files**
- List ALL packages used in code
- Include `email-validator` if using `EmailStr`
- Include `pydantic-settings` if using `BaseSettings`
- Verify every import has corresponding package in requirements

**Step 5: Create Docker Configuration**
- Create Dockerfile
- Create docker-compose.yml with ALL services (db, redis, migrate, api, worker)
- Ensure migrate service runs before api/worker
- Verify all environment variables match

**Step 6: Final Verification**
- Run through PRE-DEPLOYMENT CHECKLIST (see RULE 12)
- Verify no duplicate migration files
- Verify all dependencies are listed
- Test that `docker-compose up` works end-to-end

### 5.2 Common Workflow Mistakes to Avoid
- INCORRECT: Creating migrations before models are complete
- INCORRECT: Running `alembic revision --autogenerate` multiple times
- INCORRECT: Creating migration files without checking if they already exist
- INCORRECT: Forgetting to add packages to requirements.txt
- INCORRECT: Creating docker-compose without migrate service
- INCORRECT: Not verifying migration file uniqueness

---

## RULE 6: Project Structure

### 6.1 Root Application Folder
- **MUST** use `src/` as the root application folder
- **MUST** place domain packages under `src/`

### 6.2 Directory Structure Pattern
```
fastapi-project
├── alembic/
│   ├── __init__.py
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── exceptions.py
│   ├── pagination.py  
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── router.py
│   │
│   ├── infra/  # OPTIONAL - only if Redis or Celery requested
│   │   ├── __init__.py
│   │   ├── cache_redis.py  # OPTIONAL - only if Redis requested
│   │   └── celery_app.py  # OPTIONAL - only if Celery requested
│   │
│   └── <user_module>/  # USER PROVIDES ACTUAL MODULE NAME
│       ├── __init__.py
│       ├── models.py
│       ├── schemas.py
│       ├── repository.py
│       ├── service.py
│       ├── router.py
│       ├── dependencies.py
│       ├── constants.py
│       ├── exceptions.py
│       ├── utils.py
│       ├── config.py
│       └── documentations/  # Swagger/OpenAPI documentation classes
│           ├── __init__.py
│           └── {module}_api_doc.py (e.g., organization_api_doc.py)
├── requirements/
│   ├── base.txt
│   └── dev.txt

├── tests/
├── templates/
├── .env
├── .gitignore
├── logging.ini
├── alembic.ini
├── Dockerfile
└── docker-compose.yml
```

**CRITICAL NOTE:** Module names in structure are STRUCTURAL PATTERN EXAMPLES ONLY. USER PROVIDES ACTUAL MODULE NAMES.

---

## RULE 7: Architecture & Layering

### 7.1 Async All The Way
- **MUST** use async routes and async DB access
- **MUST** follow "Async Routes" recommendations from the repo
- **MUST NOT** do blocking I/O inside async routes
- If blocking I/O required, run it in a threadpool

### 7.2 Configuration (`src/config.py`)
- **Reference:** See `config_validate.md` in rules/validate folder
- **MUST** implement using Pydantic BaseSettings (from `pydantic_settings`)
- **CRITICAL:** Must include `pydantic-settings` in requirements/base.txt
- Settings for Postgres, Redis, and Celery must come from here
- **MUST** use `model_config` dict (not `Config` class) for Pydantic v2

### 7.3 Database (`src/database.py`)
- **MUST** implement as central place for:
  - Async SQLAlchemy engine: `create_async_engine(settings.database_url, ...)`
  - Connection pool configuration (pool_size, max_overflow, pool_timeout, pool_recycle)
  - Async session maker (`async_sessionmaker`)
- **MUST** provide `get_session()` dependency for FastAPI routes/services
- **Reference:** See `database_setup.md` for complete database setup instructions

### 7.4 Database Migrations (Alembic)
- **Reference:** See `database_setup.md` for complete migration setup instructions
- **CRITICAL:** Initial migrations MUST use UUID from the start, NOT INTEGER
- **CRITICAL:** Only ONE initial migration file should exist
- **MUST** use descriptive migration file names (not auto-generated hash names)
- **MUST** use simple revision IDs: `'001_initial'` (not hash-based)
- **MUST** set `down_revision: None` for initial migration

**Correct Initial Migration Pattern:**
```python
# Use user's actual table name
op.create_table('user_table_name',
    sa.Column('id', sa.Uuid(), nullable=False),  # CORRECT: UUID from start
    sa.Column('name', sa.String(), nullable=False),
    ...
    sa.PrimaryKeyConstraint('id')
)
```

**WRONG Pattern:**
```python
op.create_table('user_table_name',
    sa.Column('id', sa.Integer(), nullable=False),  # INCORRECT: ERROR: Use UUID instead
    ...
)
```

### 7.5 Redis (OPTIONAL)
- **ONLY** implement if user explicitly requests Redis
- **Reference:** See `redis_validate.md` for complete Redis setup instructions
- **MUST** implement `src/infra/cache_redis.py` similar to the `aws` client example
- Expose singleton-ish Redis client using connection pool

### 7.6 Celery (OPTIONAL)
- **ONLY** implement if user explicitly requests Celery
- **Reference:** See `celery_validate.md` for complete Celery setup instructions
- **CRITICAL:** Redis must be set up first (Celery uses Redis as broker)
- **MUST** implement `src/infra/celery_app.py`
- Configure Celery with Redis as broker + backend
- Define at least one example task

---

## RULE 8: Domain Module Architecture

### 8.1 Module File Structure
For each domain module (USER PROVIDES ACTUAL MODULE NAME), MUST include:
- `models.py` → SQLAlchemy models
- `schemas.py` → Pydantic v2 models
- `repository.py` → Database operations
- `service.py` → Business logic
- `router.py` → FastAPI endpoints
- `dependencies.py` → Domain-specific dependencies
- `constants.py` → Domain-specific constants
- `exceptions.py` → Domain-specific exceptions
- `utils.py` → Domain-specific utilities
- `config.py` → Domain-specific configuration (optional)
- `documentations/` → Swagger/OpenAPI documentation classes
  - `__init__.py`
  - `{module}_api_doc.py` → API documentation class with `summary` and `description` for each endpoint

**Reference:** See `module_architecture_validate.md` for complete domain architecture patterns.

### 8.2 Models (`models.py`)

**RULE 8.2.1: Primary Keys**
- **MUST** use UUID type, NOT int
- **MUST** use `UUID` type with `default=uuid4` for primary keys
- **Correct pattern:**
  ```python
  from uuid import uuid4, UUID
  
  id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, index=True)
  ```
- **WRONG pattern:**
  ```python
  id: Mapped[int] = mapped_column(primary_key=True)  # INCORRECT: Use UUID instead
  ```

**RULE 8.2.2: Foreign Keys**
- **MUST** use UUID type matching the referenced primary key
- **Correct pattern:**
  ```python
  organization_id: Mapped[UUID] = mapped_column(
      ForeignKey("organizations.id", ondelete="CASCADE"),
      index=True,
  )
  ```

**RULE 8.2.3: Timestamp Fields**
- **CRITICAL:** MUST use `server_default=func.now()` NOT `default_factory`
- `default_factory` is a Python dataclass feature and does NOT work with SQLAlchemy 2.x Mapped types
- **Correct pattern:**
  ```python
  from sqlalchemy import DateTime, func
  from datetime import datetime
  
  created_at: Mapped[datetime] = mapped_column(
      DateTime(timezone=True),
      server_default=func.now(),
  )
  updated_at: Mapped[datetime | None] = mapped_column(
      DateTime(timezone=True),
      onupdate=func.now(),
  )
  ```
- **WRONG pattern:**
  ```python
  created_at: Mapped[datetime] = mapped_column(default_factory=datetime.utcnow)  # INCORRECT: ERROR
  ```

### 8.3 Schemas (`schemas.py`)

**RULE 8.3.1: Schema Organization**
- **Request Schemas:** Define input validation for API endpoints (e.g., `ResourceCreate`, `ResourceUpdate`, `ResourceListQuery`)
- **Response Schemas:** Define output structure for API responses (e.g., `ResourceRead`, `ResourceList`)
- **Purpose:** Request schemas validate input, Response schemas structure output
- **Business Logic:** Implemented in `service.py`, NOT in schemas

**RULE 8.3.2: ID Fields**
- **MUST** use UUID type for all ID fields
- **MUST** use `ConfigDict(from_attributes=True)` for Pydantic v2

**RULE 8.3.3: Request Schema Pattern**
```python
from uuid import UUID
from pydantic import BaseModel

class ResourceCreate(BaseModel):  # Request schema
    name: str
    organization_id: UUID  # CORRECT: Must be UUID

class ResourceUpdate(BaseModel):  # Request schema
    name: Optional[str] = None

class ResourceListQuery(BaseModel):  # Query schema
    page: int = 1
    page_size: int = 20
    search: Optional[str] = None
```

**RULE 8.3.4: Response Schema Pattern**
```python
from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ResourceRead(BaseModel):  # Response schema
    id: UUID  # CORRECT: Must be UUID
    name: str
    created_at: datetime
    updated_at: Optional[datetime] = None  # CORRECT: Must be Optional (None on creation)
    model_config = ConfigDict(from_attributes=True)
```

**RULE 8.3.5: Updated At Field**
- **CRITICAL:** `updated_at` field MUST be Optional in response schemas
- `updated_at` is `None` when a record is first created (before any updates)
- `onupdate=func.now()` only triggers on UPDATE operations, not on INSERT
- **WRONG pattern:**
  ```python
  updated_at: datetime  # INCORRECT: ERROR: None on creation will fail validation
  ```

### 8.4 Repository (`repository.py`)

**RULE 8.4.1: Purpose**
- **Data Access Layer** - Handle database operations only (CRUD using AsyncSession)
- **Pure database operations** - no business logic, no validation, no HTTP concerns
- **Single Responsibility**: Only database queries and data persistence

**RULE 8.4.2: What Repository SHOULD Contain**
- Database queries (SELECT, INSERT, UPDATE, DELETE)
- SQLAlchemy operations using AsyncSession
- Eager loading relationships with `selectinload()`
- Filtering, sorting, pagination at database level
- Transaction management (commit, rollback)
- Query building and optimization

**RULE 8.4.3: What Repository MUST NOT Contain**
- **Business logic** (validation rules, business rules, calculations)
- **HTTP concerns** (status codes, request/response handling)
- **Validation** (use schemas and service layer for validation)
- **Business rules** (e.g., "cannot delete if has dependencies" - this is service layer)
- **Error messages** (use constants.py for messages)
- **Configuration** (use config.py for settings)

**RULE 8.4.4: ID Parameters**
- **MUST** use UUID type for all ID parameters, not int

**RULE 8.4.5: CORRECT Repository Pattern**
```python
# src/organizations/repository.py
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

class OrganizationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, org_id: UUID) -> Optional[Organization]:
        """Get organization by ID - pure database operation"""
        result = await self.session.execute(
            select(Organization)
            .where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, org: Organization) -> Organization:
        """Create organization - pure database operation"""
        self.session.add(org)
        await self.session.commit()
        await self.session.refresh(org)
        return org
    
    async def list_with_pagination(
        self, 
        page: int, 
        page_size: int,
        filters: dict = None
    ) -> tuple[list[Organization], int]:
        """List organizations with pagination - pure database operation"""
        query = select(Organization)
        
        # Apply filters (database-level filtering)
        if filters:
            if filters.get("status"):
                query = query.where(Organization.status == filters["status"])
        
        # Count total
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()
        
        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return list(items), total
```

**RULE 8.4.6: WRONG Repository Pattern (DO NOT DO THIS)**
```python
# INCORRECT: Business logic in repository
async def create(self, org: Organization) -> Organization:
    # INCORRECT: Business validation in repository
    if org.status == "inactive":
        raise ValueError("Cannot create inactive organization")  # WRONG: Business logic
    
    # INCORRECT: Business rule in repository
    if await self.count_by_name(org.name) > 0:
        raise ValueError("Organization name must be unique")  # WRONG: Business logic
    
    self.session.add(org)
    await self.session.commit()
    return org
```

**RULE 8.4.7: Key Principles**
- **Repository is thin** - only database operations
- **No business logic** - all business rules go in service.py
- **No validation** - validation happens in schemas and service layer
- **No error messages** - use constants.py for messages
- **Pure data access** - repository methods should be reusable and testable

### 8.5 Service (`service.py`)

**RULE 8.5.1: Business Logic Location**
- **ALL business logic MUST be in service.py** - NOT in router, NOT in repository
- Service methods receive request schemas, return response schemas
- Service uses repository for data access
- Service handles validation, business rules, transactions
- **Purpose:** Business logic layer - validates input, applies rules, orchestrates data operations

**RULE 8.5.2: Service Separation**
- Services must NOT know HTTP details (no FastAPI imports)
- Services work with domain models, repositories, and infra (like Celery)

### 8.6 Router (`router.py`)

**RULE 8.6.1: Router Development Flow**
- **Flow:** Router → Request Schema → Service (Business Logic) → Response Schema
- **Main Purpose:**
  - Define **request schemas** in `schemas.py` for input validation
  - Define **response schemas** in `schemas.py` for output structure
  - Implement **business logic** in `service.py`
  - Router is **thin** - only handles HTTP concerns and delegates to service

**RULE 8.6.2: Router Structure Pattern**
```python
from fastapi import APIRouter, Depends, status
from uuid import UUID
from src.module.dependencies import ResourceApiDep
from src.module.documentations.resource_api_doc import ResourceApiDocs
from src.module.schemas import ResourceCreate, ResourceUpdate, ResourceListQuery  # Request schemas
from src.module.schemas import ResourceRead  # Response schemas

router = APIRouter(
    prefix="/api/resources",
    tags=["Resources"],
)
```

**RULE 8.6.3: Router Endpoint Pattern**
- **MUST** use API dependency class pattern (e.g., `ResourceApiDep`) instead of direct service instantiation
- **MUST** use Pydantic schemas for request bodies (e.g., `data: ResourceCreate`) - defines input validation
- **MUST** use Pydantic schemas for response models (e.g., `ResourceRead`) - defines output structure
- **MUST** use `Depends()` pattern for query parameters when query schema exists
- **MUST** include comprehensive endpoint documentation (summary, description) for Swagger from documentation class
- **MUST** specify response_model and status_code in decorator
- **Business logic MUST be in service.py** - router only delegates

**RULE 8.6.4: Correct Endpoint Pattern**
```python
from src.schemas import StandardResponse  # CORRECT: Import StandardResponse wrapper

# GET RESOURCE BY ID
@router.get(
    "/{resource_id}",
    response_model=StandardResponse[ResourceRead],  # CORRECT: StandardResponse wrapper
    summary=ResourceApiDocs.get.api_summary.summary,  # CORRECT: Swagger documentation from documentation class
    description=ResourceApiDocs.get.api_summary.description,
)
async def get_resource(
    resource_id: UUID,  # CORRECT: Path parameter
    api: ResourceApiDep  # CORRECT: API dependency (handles service instantiation)
) -> StandardResponse[ResourceRead]:  # CORRECT: StandardResponse type hint
    # CORRECT: Delegate to service - business logic is in service.py
    resource = await api.get_resource_by_id(resource_id)
    # CORRECT: Wrap in StandardResponse
    return StandardResponse(data=resource, message="Resource retrieved successfully")

# CREATE RESOURCE
@router.post(
    "",
    response_model=StandardResponse[ResourceRead],  # CORRECT: StandardResponse wrapper
    status_code=status.HTTP_201_CREATED,
    summary=ResourceApiDocs.create.api_summary.summary,
    description=ResourceApiDocs.create.api_summary.description,
)
async def create_resource(
    data: ResourceCreate,  # CORRECT: Request schema - defines input validation
    api: ResourceApiDep  # CORRECT: API dependency
) -> StandardResponse[ResourceRead]:  # CORRECT: StandardResponse type hint
    # CORRECT: Delegate to service - business logic in service.py
    resource = await api.create_resource(data=data)
    # CORRECT: Wrap in StandardResponse
    return StandardResponse(data=resource, message="Resource created successfully")

# LIST RESOURCES
@router.get(
    "",
    response_model=StandardResponse[PagedCollection[ResourceRead]],  # CORRECT: StandardResponse wrapper
    summary=ResourceApiDocs.list.api_summary.summary,
    description=ResourceApiDocs.list.api_summary.description,
)
async def list_resources(
    api: ResourceApiDep,  # CORRECT: API dependency
    query: ResourceListQuery = Depends(ResourceListQuery),  # CORRECT: Query schema with Depends()
) -> StandardResponse[PagedCollection[ResourceRead]]:  # CORRECT: StandardResponse type hint
    # CORRECT: Delegate to service - business logic in service.py
    resources = await api.list_resources(query)
    # CORRECT: Wrap in StandardResponse
    return StandardResponse(data=resources, message="Resources retrieved successfully")
```

**RULE 8.6.5: WRONG Patterns (DO NOT DO THIS)**
```python
# INCORRECT: Direct service instantiation (should use API dependency)
@router.post("")
async def create_resource(
    data: ResourceCreate,
    session: AsyncSession = Depends(get_session),
):
    service = ResourceService(session)  # INCORRECT: Direct service instantiation
    result = await service.create_resource(data)
    return StandardResponse(success=True, data=result, message="...")

# INCORRECT: Individual Query() parameters (should use query schema with Depends())
@router.get("")
async def list_resources(
    page: int = Query(1),  # INCORRECT: Individual Query() parameters
    page_size: int = Query(20),
    search: str = Query(None),
    session: AsyncSession = Depends(get_session),
):
    ...
```

**RULE 8.6.6: Query Parameters Pattern**
- **MUST** use query schema with `Depends()` when query schema exists
- **CORRECT:** `query: ResourceListQuery = Depends(ResourceListQuery)`
- **WRONG:** Individual `Query()` parameters when query schema exists
- **Exception:** Simple single query parameters can use `Query()` directly

**RULE 8.6.7: API Dependency Pattern (CRITICAL)**

**CRITICAL VIOLATION:** All routers MUST use API dependency pattern instead of direct service instantiation.

**Current Pattern (WRONG - DO NOT USE):**
```python
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    service = UserService(session)  # ❌ WRONG: Direct instantiation
    result = await service.get_user(user_id)
    return result
```

**Required Pattern (CORRECT - MUST USE):**
```python
async def get_user(
    user_id: UUID,
    api: UserApiDep,  # ✅ CORRECT: API dependency injection
):
    return await api.get_user(user_id)  # ✅ CORRECT: Delegate to API dependency
```

**Key Requirements:**
- **MUST** use API dependency class (e.g., `ResourceApiDep`, `UserApiDep`) injected via `Depends()`
- **MUST NOT** directly instantiate services in router endpoints (e.g., `service = UserService(session)`)
- **MUST NOT** inject `AsyncSession` directly in router endpoints for service instantiation
- API dependency handles service instantiation and business logic delegation
- Router endpoints delegate directly to API dependency methods
- **CORRECT:** `api: ResourceApiDep` → `return await api.create_resource(data=data)`
- **WRONG:** `session: AsyncSession = Depends(get_session)` → `service = ResourceService(session)`

**RULE 8.6.8: Development Flow Summary**
```
Router (router.py)
  ↓
Request Schema (schemas.py) - Input Validation
  ↓
Service (service.py) - Business Logic
  ↓
Repository (repository.py) - Data Access
  ↓
Response Schema (schemas.py) - Output Structure
  ↓
Router (router.py) - Returns Response
```

**RULE 8.6.9: Rationale**
- **Request schemas** define input validation - single source of truth for request structure
- **Response schemas** define output structure - single source of truth for response structure
- **Business logic in service.py** - clear separation of concerns, testable, reusable
- **Router is thin** - only handles HTTP concerns (routing, validation, documentation, Swagger)
- **Service contains ALL business logic** - validation, business rules, transactions, orchestration
- API dependency pattern provides better separation of concerns
- Query schema with `Depends()` centralizes query parameter validation
- Prevents field definition duplication between router and schema
- Ensures validation is centralized in Pydantic schemas
- Maintains DRY principle (Don't Repeat Yourself)
- Makes maintenance easier (change schema once, not in multiple places)
- FastAPI automatically validates and parses request bodies using schemas
- Comprehensive documentation improves API discoverability (Swagger)
- Consistent, clean router code that delegates to service

**RULE 8.6.10: ETag Logic Location (CRITICAL)**
- **CRITICAL:** ETag logic MUST be in service layer, NOT in router layer
- **ETag is business logic concern** - version validation, conditional updates belong in service
- **Service layer handles ETag validation** - checks If-Match/If-None-Match, generates ETag, validates version conflicts
- **CORRECT:** Service methods accept HTTP headers, generate ETag, validate version conflicts, return Response objects with status codes (304, 412)
- **WRONG:** Router handles ETag generation, validation, or conditional request logic
- **Reference:** See `error_prevention.md` RULE 19 for complete ETag implementation patterns

### 8.7 Constants (`constants.py`)

**RULE 8.7.1: Purpose**
- **Domain-specific constants** - Static values used across the module
- **Error codes and messages** - Centralized error message strings
- **Status values** - Enum-like string constants
- **Magic numbers/strings** - Static values that should not be hardcoded

**RULE 8.7.2: What Constants SHOULD Contain**
- Error message strings (e.g., `ERROR_ORGANIZATION_NOT_FOUND = "Organization not found"`)
- Success message strings (e.g., `SUCCESS_ORGANIZATION_CREATED = "Organization created successfully"`)
- Status values (e.g., `STATUS_ACTIVE = "active"`, `STATUS_INACTIVE = "inactive"`)
- Error codes (e.g., `ERROR_CODE_ORG_NOT_FOUND = "ORGANIZATION_NOT_FOUND"`)
- Enum-like constants (e.g., `ROLE_ADMIN = "admin"`, `ROLE_CREATOR = "creator"`)
- Magic numbers/strings that are used in multiple places

**RULE 8.7.3: What Constants MUST NOT Contain**
- **Functions or logic** (use utils.py for functions)
- **Computed values** (only static string/number literals)
- **Database access** (use repository.py for database operations)
- **Configuration** (use config.py for environment-based settings)
- **Business logic** (use service.py for business logic)

**RULE 8.7.4: CORRECT Constants Pattern**
```python
# src/organizations/constants.py

# Error Messages
ERROR_ORGANIZATION_NOT_FOUND = "Organization not found"
ERROR_ORGANIZATION_ALREADY_EXISTS = "Organization with this name already exists"
ERROR_INVALID_STATUS = "Invalid organization status"
ERROR_ORGANIZATION_HAS_USERS = "Cannot delete organization. It has active users."

# Success Messages
SUCCESS_ORGANIZATION_CREATED = "Organization created successfully"
SUCCESS_ORGANIZATION_UPDATED = "Organization updated successfully"
SUCCESS_ORGANIZATION_DELETED = "Organization deleted successfully"

# Status Values
STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"

# Error Codes
ERROR_CODE_ORG_NOT_FOUND = "ORGANIZATION_NOT_FOUND"
ERROR_CODE_DUPLICATE_NAME = "DUPLICATE_ORGANIZATION_NAME"
ERROR_CODE_INVALID_STATUS = "INVALID_STATUS"
ERROR_CODE_ORG_HAS_DEPENDENCIES = "ORGANIZATION_HAS_DEPENDENCIES"

# Industry Types
INDUSTRY_ECOMMERCE = "Ecommerce"
INDUSTRY_AGENCY = "Agency"
INDUSTRY_RETAIL = "Retail"
```

**RULE 8.7.5: WRONG Constants Pattern (DO NOT DO THIS)**
```python
# INCORRECT: Functions in constants.py
def get_error_message(code: str) -> str:  # WRONG: Functions belong in utils.py
    return ERROR_MESSAGES.get(code, "Unknown error")

# INCORRECT: Computed values
MAX_FILE_SIZE = 2 * 1024 * 1024  # WRONG: Computed value, use config.py or hardcode

# INCORRECT: Database access
ACTIVE_ORGS_COUNT = await get_active_orgs_count()  # WRONG: Database access belongs in repository.py
```

**RULE 8.7.6: Key Principles**
- **Static values only** - no functions, no computed values, no logic
- **UPPER_CASE naming** - follow Python constant naming convention
- **Group by category** - organize constants logically (errors, success, status, etc.)
- **Centralized** - all domain-specific constants in one place
- **Reusable** - import and use across service, router, exceptions

### 8.8 Config (`config.py`)

**RULE 8.8.1: Purpose**
- **Domain-specific configuration** - Settings that vary by environment
- **Environment-based values** - Loaded from `.env` file or environment variables
- **Feature flags** - Enable/disable features per environment
- **Domain-specific defaults** - Default values for domain operations

**RULE 8.8.2: When to Use Config**
- **OPTIONAL** - Only create if module needs domain-specific configuration
- **Use when**: Module has settings that differ between environments (dev, staging, prod)
- **Use when**: Module has feature flags or toggles
- **Use when**: Module has configurable limits, timeouts, or thresholds
- **Don't use**: If all values are static constants (use constants.py instead)

**RULE 8.8.3: What Config SHOULD Contain**
- Environment-based settings (API keys, URLs, timeouts)
- Feature flags (e.g., `ENABLE_LOGO_UPLOAD: bool = True`)
- Configurable limits (e.g., `MAX_LOGO_SIZE_MB: int = 2`)
- Default values (e.g., `DEFAULT_PAGE_SIZE: int = 20`)
- Domain-specific API settings
- Settings loaded from `.env` file

**RULE 8.8.4: What Config MUST NOT Contain**
- **Hardcoded secrets** (use environment variables)
- **Business logic** (use service.py for business logic)
- **Static constants** (use constants.py for static values)
- **Functions** (use utils.py for functions)
- **Database access** (use repository.py for database operations)

**RULE 8.8.5: CORRECT Config Pattern**
```python
# src/organizations/config.py
from pydantic_settings import BaseSettings

class OrganizationSettings(BaseSettings):
    """Organization-specific configuration"""
    
    # File upload settings
    MAX_LOGO_SIZE_MB: int = 2
    ALLOWED_LOGO_FORMATS: list[str] = ["PNG", "JPEG", "JPG"]
    LOGO_UPLOAD_PATH: str = "/uploads/logos"
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Feature flags
    ENABLE_LOGO_UPLOAD: bool = True
    ENABLE_ORGANIZATION_ANALYTICS: bool = False
    
    # Timeouts and limits
    ORGANIZATION_CREATION_TIMEOUT_SECONDS: int = 30
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "env_prefix": "ORG_",  # Optional: prefix for env vars
    }

org_settings = OrganizationSettings()
```

**RULE 8.8.6: WRONG Config Pattern (DO NOT DO THIS)**
```python
# INCORRECT: Hardcoded secrets
class OrganizationSettings(BaseSettings):
    API_KEY = "secret-key-12345"  # WRONG: Should be in .env file

# INCORRECT: Business logic
class OrganizationSettings(BaseSettings):
    def validate_org_name(self, name: str) -> bool:  # WRONG: Logic belongs in service.py
        return len(name) > 0

# INCORRECT: Static constants (use constants.py instead)
class OrganizationSettings(BaseSettings):
    STATUS_ACTIVE = "active"  # WRONG: Static constant, use constants.py
```

**RULE 8.8.7: Key Principles**
- **Optional file** - only create if needed
- **Environment-based** - values loaded from .env or environment variables
- **Pydantic BaseSettings** - use pydantic-settings for configuration management
- **Type hints required** - all fields must have type hints
- **Defaults provided** - provide sensible defaults for all settings
- **Separate from constants** - config is for environment-based values, constants.py is for static values

### 8.9 Other Module Files
- `dependencies.py` → Domain-specific dependencies that routers need
- `exceptions.py` → Domain-specific exceptions (consistent with repo structure)
- `utils.py` → Non-business helpers (response normalization, minor transformations)

### 8.10 Swagger Documentation (`documentations/{module}_api_doc.py`)

**RULE 8.10.1: Swagger Documentation Standardization**
- **MUST create a documentation class for each resource module** to centralize Swagger/OpenAPI documentation
- **Purpose**: Keeps Swagger documentation consistent, maintainable, and centralized (not hardcoded in routers)
- **Structure**: Create a documentation class with ClassVar attributes for each endpoint operation
- **Required Fields**: Each endpoint operation MUST have `summary` and `description` fields
- **Flexibility**: Structure can vary (dict, ApiSummary object, custom class) as long as `summary` and `description` are accessible

**RULE 8.10.2: Documentation Class Requirements**
- **Location**: `src/{module}/documentations/{module}_api_doc.py`
- **Class Naming**: `{Resource}ApiDocs` (e.g., `OrganizationApiDocs`, `UserApiDocs`, `AssetGroupApiDocs`)
- **Structure**: Use ClassVar attributes for each endpoint operation (e.g., `create`, `list`, `get`, `update`, `delete`)
- **Required Fields per Operation**:
  * `summary`: Brief, clear purpose statement (e.g., "Purpose of this API is to create a new organization")
  * `description`: Detailed description (can include permissions, usage notes, business rules, etc.)

**RULE 8.10.3: Router Decorator Requirements**
- **MUST use `summary` from documentation class** (not hardcoded strings)
- **MUST use `description` from documentation class** (not hardcoded strings)
- **Pattern**: `summary=ResourceApiDocs.operation_name.<path_to_summary>`
- **Pattern**: `description=ResourceApiDocs.operation_name.<path_to_description>`
- **Exact path depends on implementation structure** (flexible - can be dict access, object attribute, etc.)

**RULE 8.10.4: CORRECT Implementation Examples**

**Example 1 - Using Dictionary Structure:**
```python
# src/organizations/documentations/organization_api_doc.py
from typing import ClassVar

class OrganizationApiDocs:
    """API documentation for Organization endpoints"""
    
    create: ClassVar[dict] = {
        "summary": "Purpose of this API is to create a new organization",
        "description": "Creates a new organization with required details. Only SuperAdmin can create organizations."
    }
    
    list: ClassVar[dict] = {
        "summary": "Purpose of this API is to list organizations with pagination",
        "description": "Retrieves a paginated list of organizations. Supports filtering, searching, and sorting."
    }
    
    update: ClassVar[dict] = {
        "summary": "Purpose of this API is to update organization details",
        "description": "Updates organization information. Only SuperAdmin can update organizations."
    }
```

```python
# src/organizations/routers.py
from src.organizations.documentations.organization_api_doc import OrganizationApiDocs

@router.post(
    "",
    response_model=OrganizationRead,
    summary=OrganizationApiDocs.create["summary"],
    description=OrganizationApiDocs.create["description"]
)
async def create_organization(...):
    """Create a new organization"""
    pass
```

**Example 2 - Using ApiSummary Object Structure:**
```python
# src/organizations/documentations/organization_api_doc.py
from typing import ClassVar
from src.core.docs.operation_docs import ApiSummary

class OrganizationApiDocs:
    """API documentation for Organization endpoints"""
    
    create: ClassVar[ApiSummary] = ApiSummary(
        summary="Purpose of this API is to create a new organization",
        description="Creates a new organization with required details. Only SuperAdmin can create organizations."
    )
    
    update: ClassVar[ApiSummary] = ApiSummary(
        summary="Purpose of this API is to update organization details",
        description="Updates organization information. Only SuperAdmin can update organizations."
    )
```

```python
# src/organizations/routers.py
from src.organizations.documentations.organization_api_doc import OrganizationApiDocs

@router.post(
    "",
    summary=OrganizationApiDocs.create.summary,
    description=OrganizationApiDocs.create.description
)
async def create_organization(...):
    """Create a new organization"""
    pass
```

**RULE 8.10.5: WRONG Patterns (DO NOT DO THIS)**
```python
# WRONG - Hardcoded strings in router decorator
@router.post(
    "",
    response_model=OrganizationRead,
    summary="Create organization",  # WRONG - hardcoded string
    description="Creates a new organization"  # WRONG - hardcoded string
)
async def create_organization(...):
    pass
```

**RULE 8.10.6: Benefits**
- **Centralized Management**: All Swagger documentation in one place per resource
- **Consistency**: Ensures consistent Swagger UI appearance across all endpoints
- **Easy Maintenance**: Update documentation in one place, not scattered across routers
- **Better Developer Experience**: Clear, structured documentation for API consumers
- **Reusability**: Documentation can be reused or extended for other purposes

**RULE 8.10.7: Implementation Flexibility**
- **Structure can vary**: Use dict, ApiSummary object, custom class, or any structure that exposes `summary` and `description`
- **Access pattern can vary**: Use dict access (`["summary"]`), object attributes (`.summary`), or any pattern that works
- **Only requirement**: `summary` and `description` must be accessible and used in router decorators
- **No specific class structure enforced**: Adapt to your project's existing patterns

**RULE 8.10.8: Verification Checklist**
- CORRECT: Documentation class exists in `src/{module}/documentations/{module}_api_doc.py`
- CORRECT: Documentation class has ClassVar attributes for each endpoint operation
- CORRECT: Each operation has both `summary` and `description` fields
- CORRECT: Router decorators use documentation class attributes (not hardcoded strings)
- CORRECT: `summary` and `description` are properly accessible via the chosen structure

**RULE 8.10.9: When to Use**
- **REQUIRED** for ALL API endpoints - every router endpoint MUST use documentation class for `summary` and `description`
- **Rationale**: Centralizes Swagger documentation management, ensures consistency, makes documentation easier to maintain and update

---

## RULE 9: Python Dependencies / Requirements

### 9.1 Requirements File Structure
- **MUST** have `requirements/base.txt` for production dependencies
- **MUST** have `requirements/dev.txt` for development dependencies
- **Reference:** See `dependencies_validate.md` for complete dependencies management rules

### 9.2 Critical Package Dependencies
- **CRITICAL:** If using `EmailStr` → MUST have `email-validator` in requirements/base.txt
- **CRITICAL:** If using `BaseSettings` → MUST have `pydantic-settings` in requirements/base.txt
- **CRITICAL:** If using `redis.asyncio` → MUST have `redis` in requirements/base.txt
- **CRITICAL:** If using `celery` → MUST have `celery` in requirements/base.txt
- **MUST** verify ALL imports have corresponding packages in requirements

---

## RULE 10: API Design

### 10.1 RESTful Endpoints
- **MUST** follow "Follow the REST" and response serialization guidance from the repo
- **MUST** use clean RESTful endpoints:
  - `/v1/<user_module_name>` (CRUD)
  - `/v1/<user_module_name>/by-<relation>/{relation_id}` (CRUD + query by relation)
- **MUST** use async routes, Pydantic request/response models, and proper status codes

**CRITICAL NOTE:** Endpoint patterns are STRUCTURAL EXAMPLES ONLY - implement using USER'S ACTUAL MODULE NAMES.

---

## RULE 11: Docker / Docker-Compose

### 11.1 Dockerfile
- **MUST** create Dockerfile for running `api`, `worker`, and `migrate` services
- **MUST** use Python 3.11-slim base image
- **MUST** install system dependencies (gcc, postgresql-client)
- **MUST** copy requirements and install packages
- **MUST** copy application code
- **MUST** expose port 8000

### 11.2 Docker-Compose Services
- **MUST** include `db` service (Postgres)
- **MUST** include `migrate` service (Alembic migrations - REQUIRED, runs before api/worker)
- **MUST** include `api` service (FastAPI app via Uvicorn)
- **OPTIONAL:** `redis` service (only if user requests Redis)
- **OPTIONAL:** `worker` service (only if user requests Celery)

### 11.3 Docker-Compose Rules

**RULE 11.3.1: Version Field**
- **MUST NOT** include `version` field
- Modern docker-compose (v2+) does not require or use the `version` field
- Including it will generate warnings: "the attribute `version` is obsolete"

**RULE 11.3.2: Port Mapping Strategy**
- **MUST** use non-standard host ports to avoid conflicts with local services
- PostgreSQL: Use `"5433:5432"` (host:container) instead of `"5432:5432"`
- Redis: Use `"6380:6379"` (host:container) instead of `"6379:6379"`
- Container-to-container communication still uses standard ports (5432, 6379) via service names

**RULE 11.3.3: Health Checks**
- **MUST** include health checks for `db` service
- **MUST** include health checks for `redis` service (if Redis is included)
- **MUST** use `depends_on` with `condition: service_healthy` for services that depend on them

**RULE 11.3.4: Service Dependencies**
- **MUST** use `depends_on` with health check conditions for proper startup order
- `migrate` depends on `db` with `condition: service_healthy`
- `api` depends on:
  - `db` with `condition: service_healthy`
  - `migrate` with `condition: service_completed_successfully`
  - `redis` with `condition: service_healthy` (if Redis service exists)
- `worker` depends on (if Celery requested):
  - `db` with `condition: service_healthy`
  - `redis` with `condition: service_healthy` (required - Celery needs Redis)
  - `migrate` with `condition: service_completed_successfully`

**RULE 11.3.5: Environment Variables**
- **MUST** use service names (e.g., `db`, `redis`) for internal container communication
- Database URL: `postgresql+asyncpg://postgres:password@db:5432/dbname`
- Redis URL: `redis://redis:6379/0`
- **CRITICAL: Password Consistency**
  - Password in `DATABASE_URL` MUST match `POSTGRES_PASSWORD` in `db` service environment
  - Username in `DATABASE_URL` MUST match `POSTGRES_USER` in `db` service environment
  - Database name in `DATABASE_URL` MUST match `POSTGRES_DB` in `db` service environment
  - **MUST** verify consistency between db service environment variables and DATABASE_URL

**RULE 11.3.6: Migrate Service**
- **MUST** include `migrate` service that runs `alembic upgrade head`
- **MUST** have `restart: "no"` (runs once and exits)
- **MUST** depend on `db` with `condition: service_healthy`
- **MUST** use same DATABASE_URL environment variable as api/worker
- **CRITICAL:** Without this, application will fail with "relation does not exist" errors

**RULE 11.3.7: Redis Memory Overcommit Warning**
- Redis will show warning: "WARNING Memory overcommit must be enabled!"
- This is a **warning, not an error** - Redis will function normally
- **Best practice:** Add Redis command with memory limits: `redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --save ""`
- **MUST NOT** use `privileged: true` or `sysctls` in docker-compose (security risk)

### 11.4 Docker-Compose Summary
**MUST-DO items:**
- CORRECT: Omit `version` field
- CORRECT: Use port 5433 for PostgreSQL host mapping (not 5432)
- CORRECT: Use port 6380 for Redis host mapping (not 6379)
- CORRECT: Include health checks for db and redis
- CORRECT: Use `depends_on` with health check conditions
- CORRECT: Configure Redis with memory limits and `--save ""` to minimize warnings
- CORRECT: Ensure DATABASE_URL password/username/dbname matches POSTGRES_PASSWORD/POSTGRES_USER/POSTGRES_DB
- CORRECT: Include `migrate` service that runs before `api` and `worker`

**Reference:** See `docker_validate.md` for complete Docker verification rules.

---

## RULE 12: Pre-Deployment Checklist

### 12.1 Dependencies Verification
- CORRECT: Check ALL imports in ALL Python files for required packages
- CORRECT: Verify ALL packages used in code are listed in requirements/base.txt
- CORRECT: Special cases: EmailStr → email-validator, BaseSettings → pydantic-settings, redis.asyncio → redis, celery → celery
- **Reference:** See `dependencies_validate.md` for complete dependencies verification rules

### 12.2 Docker-Compose Verification
- CORRECT: `migrate` service exists and runs `alembic upgrade head`
- CORRECT: `migrate` service has `restart: "no"`
- CORRECT: `api` and `worker` depend on `migrate` with `condition: service_completed_successfully`
- CORRECT: All services have correct DATABASE_URL matching db service credentials
- CORRECT: Health checks are configured for `db` and `redis`
- CORRECT: Port mappings use non-standard host ports (5433, 6380)
- CORRECT: NO `version` field in docker-compose.yml
- **Reference:** See `docker_validate.md` for complete Docker verification rules

### 12.3 Database Migration Verification
- CORRECT: **ONLY ONE initial migration file exists** in `alembic/versions/` (check for duplicates)
- CORRECT: Initial migration file has descriptive name (e.g., `001_initial_migration.py`)
- CORRECT: **NO auto-generated duplicate migration files** (e.g., files with hash-based names)
- CORRECT: Initial migration uses UUID for all primary keys (not INTEGER)
- CORRECT: Initial migration uses `postgresql.UUID(as_uuid=True)` for UUID columns
- CORRECT: Timestamp columns use `server_default=sa.text('now()')` (not `default_factory`)
- CORRECT: Alembic env.py properly imports all models
- CORRECT: `down_revision` in initial migration is `None`
- **Reference:** See `database_setup.md` for complete migration verification rules

### 12.4 Code Consistency Verification
- CORRECT: All model primary keys use `UUID` type (not `int`)
- CORRECT: All schema ID fields use `UUID` type (not `int`)
- CORRECT: All router path parameters for IDs use `UUID` type (not `int`)
- CORRECT: All `updated_at` fields in schemas are `Optional[datetime]` (not required)
- CORRECT: All timestamp fields in models use `server_default=func.now()` (not `default_factory`)
- CORRECT: All foreign keys use `UUID` type matching the referenced primary key
- **Reference:** See `module_architecture_validate.md` for complete code consistency patterns

### 12.5 End-to-End Verification
- CORRECT: The codebase can be dropped into a fresh repo
- CORRECT: Running `docker-compose up` should work without manual intervention
- CORRECT: No manual migration commands needed
- CORRECT: No manual dependency installation needed
- CORRECT: API should be accessible at http://localhost:8000/docs after startup
- CORRECT: Database tables should exist automatically
- **Test scenario:** Fresh clone → `docker-compose up` → Should work immediately

### 12.6 File Structure Verification
- CORRECT: All required domain files exist (models, schemas, repository, service, router, dependencies, constants, exceptions, utils, config)
- CORRECT: All `__init__.py` files exist for Python packages
- CORRECT: Alembic configuration files exist (alembic.ini, alembic/env.py, alembic/script.py.mako)
- CORRECT: **ONLY ONE initial migration file exists** in `alembic/versions/` (no duplicates)
- CORRECT: Migration file has descriptive name (not auto-generated hash name)
- CORRECT: Requirements files exist (requirements/base.txt, requirements/dev.txt)
- CORRECT: Docker files exist (Dockerfile, docker-compose.yml)
- CORRECT: Configuration files exist (.gitignore, logging.ini, .env)
- CORRECT: `src/main.py` exists with FastAPI app
- CORRECT: `src/config.py` exists with BaseSettings from `pydantic_settings`
- CORRECT: `alembic/env.py` properly handles async URL conversion

### 12.7 Mandatory Final Check
Before marking as complete, mentally simulate:
1. User clones fresh repo
2. User runs `docker-compose up`
3. Everything works without any manual steps
4. If ANY manual step is needed, the codebase is incomplete

### 12.8 Migration-Specific Final Check
Before marking migrations as complete, verify:
1. CORRECT: Only ONE initial migration file exists in `alembic/versions/`
2. CORRECT: Migration file name is descriptive (e.g., `001_initial_migration.py`)
3. CORRECT: No duplicate or conflicting migration files
4. CORRECT: Initial migration uses UUID types correctly
5. CORRECT: Running `alembic upgrade head` on fresh database creates all tables successfully
6. CORRECT: Migration revision chain is correct (no broken `down_revision` links)

---

## RULE 13: Output Format

### 13.1 Before Generating Code
**MUST ASK user for ALL required information:**
- Module name and model name (for domain modules) - USER PROVIDES THESE
- Database name, user, and password (for database configuration) - USER PROVIDES THESE
- API title, version, and prefix (for API configuration) - USER PROVIDES THESE
- Environment name and debug mode (for environment configuration) - USER PROVIDES THESE
- Celery app name (ONLY if user explicitly requests Celery) - USER PROVIDES THIS

**OPTIONAL COMPONENTS - DO NOT ADD UNLESS USER REQUESTS:**
- Redis: Only add if user explicitly mentions "redis"
- Celery: Only add if user explicitly mentions "celery"
- If user requests Celery but Redis is not set up, ask if they want Redis added first

**DO NOT proceed with code generation until user provides all required information.**

**CRITICAL: DO NOT use example names like "organizations" or "members" unless explicitly requested by user**
- These are STRUCTURAL PATTERN EXAMPLES ONLY - understand the pattern, use user's actual names
- DO NOT use placeholder values like "password", "dbname" - always ask user for actual values

### 13.2 Code Generation Order
1. FIRST show the final folder structure
2. THEN provide all important code files:
   - src/config.py
   - src/database.py
   - src/infra/cache_redis.py (if Redis requested)
   - src/infra/celery_app.py (if Celery requested)
   - src/<user_requested_modules>/* (router, schemas, models, dependencies, config, constants, exceptions, service, utils)
   - src/api/router.py
   - src/main.py
   - docker-compose.yml
3. All code must be **complete and consistent**, with valid imports
4. Do NOT include commentary or explanations unless explicitly asked
5. Do NOT generate anything that conflicts with the practices in `fastapi-best-practices`
6. **CRITICAL:** Only develop modules that the user explicitly requests

---

## Summary

This guide provides rule-based instructions for creating FastAPI backend projects. Each rule is numbered and contains specific, actionable requirements. Follow rules in order and refer to referenced validation files for detailed implementation patterns.

**Key Principles:**
- Request schemas define input validation
- Response schemas define output structure
- Business logic goes in service.py
- Router is thin and delegates to service
- Clear separation: Router → Request Schema → Service → Response Schema
