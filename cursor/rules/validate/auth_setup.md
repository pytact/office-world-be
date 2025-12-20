# FastAPI Authentication Module

**Purpose:** Standards for implementing authentication module with proper layer separation and security.

---

## RULE 1: Module Structure

### 1.1 Standard Module Layout

**RULE 1.1.1: Required Files**
```
auth/
├── router.py          # API endpoints only
├── schemas.py         # Pydantic models
├── models.py          # SQLAlchemy models
├── dependencies.py    # FastAPI dependencies
├── config.py          # Configuration & settings
├── constants.py       # Constants & messages
├── exceptions.py      # Custom exceptions
├── service.py         # Business logic layer
└── utils.py          # Helper functions
```

**RULE 1.1.2: File Organization Rules**
- CORRECT Each file has a single, clear responsibility
- CORRECT Follow standard naming conventions
- CORRECT Group related functionality together
- INCORRECT Mix responsibilities in single files

### 1.2 Layer Responsibilities

**RULE 1.2.1: Layer Responsibility Table**

| Layer | Purpose | Contains | DO NOT |
|-------|---------|----------|--------|
| `router.py` | API endpoints | Route definitions | Business logic, DB queries, password hashing, token creation |
| `service.py` | Business logic | All business logic, DB operations | Request/response handling, HTTP status codes |
| `schemas.py` | Data validation | Pydantic models | Business logic |
| `models.py` | Database | SQLAlchemy models | Business logic, methods (except `__repr__`) |
| `dependencies.py` | Auth checks | FastAPI dependencies | - |
| `utils.py` | Helpers | Pure functions | Database access, global state |
| `exceptions.py` | Errors | Custom exceptions | Raising exceptions (only define) |
| `config.py` | Settings | Configuration | Hardcoded secrets |
| `constants.py` | Values | Constants | Functions or logic |

**RULE 1.2.2: Layer Separation Rules**
- CORRECT Keep each layer focused on its responsibility
- CORRECT Use service layer for all business logic
- CORRECT Use router layer only for route definitions
- INCORRECT Mix business logic with route definitions
- INCORRECT Put database queries in router layer

---

## RULE 2: Layer Separation

### 2.1 Router Layer Rules

**RULE 2.1.1: CORRECT Router Pattern**
```python
# CORRECT
@router.post("/register", response_model=StandardResponse[UserResponse])
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    user = await service.create_user(user_data)
    return StandardResponse(success=True, data=user, message="User created successfully")
```

**RULE 2.1.2: Router Layer Rules**
- CORRECT Define routes only
- CORRECT Call service methods for business logic
- CORRECT Return StandardResponse format
- INCORRECT Include business logic in router
- INCORRECT Include database queries in router
- INCORRECT Include password hashing in router
- INCORRECT Include token creation in router

**RULE 2.1.3: WRONG Router Pattern (DO NOT DO THIS)**
```python
# INCORRECT WRONG - Business logic in router
@router.post("/register")
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_session)):
    existing = await session.query(User).filter(User.email == user_data.email).first()  # INCORRECT
    if existing:
        raise HTTPException(...)  # INCORRECT
    hashed_password = get_password_hash(user_data.password)  # INCORRECT
    # ... more logic
```

### 2.2 Service Layer Rules

**RULE 2.2.1: CORRECT Service Pattern**
```python
# CORRECT - All logic in service
class AuthService:
    async def create_user(self, user_data: UserCreate) -> User:
        # Check existence
        existing = await self.get_user_by_email(user_data.email)
        if existing:
            raise UserAlreadyExistsException()
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user
        db_user = User(email=user_data.email, hashed_password=hashed_password)
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user
```

**RULE 2.2.2: Service Layer Rules**
- CORRECT All business logic in service layer
- CORRECT All database operations in service layer
- CORRECT All validation logic in service layer
- CORRECT Raise custom exceptions from service
- INCORRECT Handle HTTP status codes in service
- INCORRECT Handle request/response formatting in service

---

## RULE 3: OAuth2PasswordBearer

### 3.1 OAuth2PasswordBearer Configuration

**CRITICAL RULE:** MUST use `OAuth2PasswordBearer` (NOT `HTTPBearer` or custom) for Swagger UI integration.

**RULE 3.1.1: CORRECT OAuth2PasswordBearer Pattern**
```python
# src/users/dependencies.py
from fastapi.security import OAuth2PasswordBearer

# CORRECT
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1/users/token",  # MUST point to OAuth2 token endpoint
    auto_error=False              # Don't auto-raise if token missing
)

async def get_current_user(
    token: str = Depends(oauth2_scheme),  # Auto extracts token
    session: AsyncSession = Depends(get_session),
) -> User:
    # CRITICAL: Check if token is None before decoding
    if not token:
        raise UnauthenticatedError("Could not validate credentials")
    # ... rest of validation
```

**RULE 3.1.2: OAuth2PasswordBearer Rules**
- CORRECT MUST use OAuth2PasswordBearer (enables Swagger UI "Authorize" button)
- CORRECT MUST set tokenUrl to OAuth2-compatible token endpoint
- CORRECT MUST set auto_error=False to handle None tokens gracefully
- CORRECT MUST check if token is None before decoding
- INCORRECT NEVER use HTTPBearer (no Swagger UI OAuth2 modal)
- INCORRECT NEVER use manual header extraction (not standard)

---

## RULE 4: OAuth2 Token Endpoint

### 4.1 Token Endpoint Requirements

**CRITICAL RULE:** MUST create OAuth2-compatible token endpoint for Swagger UI.

**RULE 4.1.1: CORRECT Token Endpoint Pattern**
```python
@router.post("/token", status_code=status.HTTP_200_OK)
async def token(
    username: str = Form(...),  # OAuth2 uses 'username' but treat as email
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    """OAuth2-compatible token endpoint for Swagger UI authorization"""
    try:
        service = UserService(session)
        user = await service.authenticate_user(username, password)
        tokens = await service.create_tokens(user)
        return {
            "access_token": tokens["access_token"],
            "token_type": "bearer"
        }
    except (InvalidCredentialsException, InactiveUserException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

**RULE 4.1.2: Token Endpoint Rules**
- CORRECT Token endpoint MUST accept `Form(...)` parameters (not JSON)
- CORRECT Token endpoint MUST return OAuth2-compatible response
- CORRECT Token endpoint MUST handle errors in OAuth2 format
- CORRECT Use `username` parameter (treat as email internally)
- CORRECT Return `access_token` and `token_type` in response
- INCORRECT Use JSON body instead of Form parameters
- INCORRECT Return non-OAuth2-compatible response format

---

## RULE 5: bcrypt Version

### 5.1 bcrypt Version Requirement

**CRITICAL RULE:** MUST pin bcrypt to 4.0.1 (bcrypt 5.0.0 is incompatible with passlib 1.7.4).

**RULE 5.1.1: CORRECT Package Versions**
```txt
# requirements/base.txt
passlib[bcrypt]==1.7.4
bcrypt==4.0.1  # CRITICAL: Pin to 4.0.1
```

**RULE 5.1.2: bcrypt Version Rules**
- CORRECT MUST pin bcrypt to 4.0.1
- CORRECT Verify: `pip list | grep bcrypt` should show `bcrypt==4.0.1`
- INCORRECT NEVER use bcrypt 5.0.0 with passlib 1.7.4
- INCORRECT Use unpinned bcrypt version

---

## RULE 6: Implementation Patterns

### 6.1 Router Pattern

**RULE 6.1.1: Router Implementation**
```python
from src.schemas import StandardResponse
from src.module.schemas import ResourceResponse

# CORRECT
@router.post("/register", response_model=StandardResponse[UserResponse])
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    user = await service.create_user(user_data)
    return StandardResponse(success=True, data=user, message="User created successfully")
```

**RULE 6.1.2: Router Pattern Rules**
- CORRECT Use StandardResponse for all responses
- CORRECT Define response_model in route decorator
- CORRECT Call service methods for business logic
- CORRECT Return StandardResponse with success, data, and message

### 6.2 Service Pattern

**RULE 6.2.1: Service Implementation**
```python
class AuthService:
    async def create_user(self, user_data: UserCreate) -> User:
        # All business logic here
        existing = await self.get_user_by_email(user_data.email)
        if existing:
            raise UserAlreadyExistsException()
        
        hashed_password = get_password_hash(user_data.password)
        db_user = User(email=user_data.email, hashed_password=hashed_password)
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user
```

**RULE 6.2.2: Service Pattern Rules**
- CORRECT All business logic in service methods
- CORRECT All database operations in service methods
- CORRECT Raise custom exceptions from service
- CORRECT Return domain models (not schemas)

### 6.3 Schema Pattern

**RULE 6.3.1: Schema Implementation**
```python
from pydantic import BaseModel, EmailStr, Field, validator

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        return v
```

**RULE 6.3.2: Schema Pattern Rules**
- CORRECT Use Pydantic BaseModel for all schemas
- CORRECT Use EmailStr for email fields
- CORRECT Use Field for validation constraints
- CORRECT Use validators for custom validation
- CORRECT Define separate schemas for create, update, and response

### 6.4 Model Pattern

**RULE 6.4.1: Model Implementation**
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True, default=uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**RULE 6.4.2: Model Pattern Rules**
- CORRECT Use UUID for primary keys
- CORRECT Use server_default for timestamps
- CORRECT Add indexes for frequently queried fields
- CORRECT Use nullable=False for required fields
- INCORRECT Include business logic in models
- INCORRECT Include methods (except `__repr__`) in models

### 6.5 Dependency Pattern

**RULE 6.5.1: Dependency Implementation**
```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/users/token", auto_error=False)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not token:
        raise UnauthenticatedError("Could not validate credentials")
    
    payload = decode_token(token)
    if payload is None:
        raise UnauthenticatedError("Could not validate credentials")
    
    user = await session.get(User, payload["sub"])
    if not user:
        raise UnauthenticatedError("Could not validate credentials")
    
    return user
```

**RULE 6.5.2: Dependency Pattern Rules**
- CORRECT Use OAuth2PasswordBearer for token extraction
- CORRECT Check if token is None before decoding
- CORRECT Validate token payload
- CORRECT Fetch user from database
- CORRECT Raise custom exceptions for errors

### 6.6 Exception Pattern

**RULE 6.6.1: CORRECT Exception Pattern**
```python
from src.exceptions import NotFoundError, ConflictError, UnauthenticatedError

# CORRECT - Extend base exceptions
class UserNotFound(NotFoundError):
    def __init__(self, user_id: str):
        super().__init__(resource="User", resource_id=user_id)

class UserEmailExists(ConflictError):
    def __init__(self, email: str):
        super().__init__(
            message=f"User with email {email} already exists",
            error_code="DUPLICATE_EMAIL",
            details=[{"field": "email", "issue": email}]
        )
```

**RULE 6.6.2: WRONG Exception Pattern (DO NOT DO THIS)**
```python
# INCORRECT WRONG - Using HTTPException directly
class UserNotFound(HTTPException):  # INCORRECT ERROR
    ...
```

**RULE 6.6.3: Exception Pattern Rules**
- CORRECT Extend base exceptions from src.exceptions
- CORRECT Provide meaningful error messages
- CORRECT Include error codes and details
- INCORRECT Use HTTPException directly
- INCORRECT Create exceptions without extending base classes

### 6.7 Utility Pattern

**RULE 6.7.1: CORRECT Utility Pattern**
```python
# CORRECT - Pure functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**RULE 6.7.2: Utility Pattern Rules**
- CORRECT Use pure functions (no side effects)
- CORRECT No database access in utils
- CORRECT No global state in utils
- CORRECT Type hints for all functions
- INCORRECT Include database queries in utils
- INCORRECT Include business logic in utils

### 6.8 Config Pattern

**RULE 6.8.1: CORRECT Config Pattern**
```python
from pydantic_settings import BaseSettings

# CORRECT - Use pydantic-settings
class AuthSettings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True

auth_settings = AuthSettings()
```

**RULE 6.8.2: Config Pattern Rules**
- CORRECT Use Pydantic BaseSettings
- CORRECT Type all fields
- CORRECT Provide defaults where appropriate
- CORRECT Load from .env file
- INCORRECT No hardcoded secrets
- INCORRECT Use plain dictionaries for config

### 6.9 Constants Pattern

**RULE 6.9.1: CORRECT Constants Pattern**
```python
# CORRECT - Group related constants
# Token Types
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

# Error Messages
ERROR_USER_NOT_FOUND = "User not found"
ERROR_INVALID_CREDENTIALS = "Invalid email or password"

# Success Messages
SUCCESS_USER_CREATED = "User created successfully"
```

**RULE 6.9.2: Constants Pattern Rules**
- CORRECT UPPER_CASE naming
- CORRECT Group by category
- CORRECT Use comments for sections
- CORRECT String literals only
- INCORRECT No functions or logic
- INCORRECT No computed values

---

## RULE 7: Security Standards

### 7.1 Password Security

**RULE 7.1.1: Password Security Rules**
- CORRECT Use bcrypt for hashing
- CORRECT Minimum 8 characters
- CORRECT Require uppercase, lowercase, digit
- CORRECT Never log passwords
- CORRECT Use Field validation
- INCORRECT No MD5 or SHA hashing
- INCORRECT No plain password storage

### 7.2 JWT Standards

**RULE 7.2.1: JWT Token Rules**
- CORRECT Separate access & refresh tokens
- CORRECT Short expiry for access (15-30 min)
- CORRECT Longer expiry for refresh (7 days)
- CORRECT Include token type in payload
- CORRECT Verify token type on decode
- INCORRECT No single token type
- INCORRECT No long-lived access tokens

### 7.3 API Security

**RULE 7.3.1: API Security Rules**
- CORRECT Use OAuth2PasswordBearer
- CORRECT Validate all inputs
- CORRECT Use custom exceptions
- CORRECT Rate limiting (production)
- CORRECT CORS configuration
- INCORRECT No basic auth
- INCORRECT No generic error messages

---

## RULE 8: Common Mistakes

### 8.1 Common Mistakes Reference Table

**RULE 8.1.1: Mistakes and Solutions**

| Mistake | Correct Approach |
|---------|------------------|
| Business logic in router | Move all logic to service layer |
| Database queries in router | Use service methods instead |
| Missing type hints | Add type hints everywhere |
| Hardcoded secrets | Use config.py with .env |
| Using HTTPException directly | Extend base exceptions |
| Using HTTPBearer | Use OAuth2PasswordBearer |
| Missing token endpoint | Create `/token` endpoint with Form params |
| bcrypt 5.0.0 | Pin bcrypt to 4.0.1 |
| No token None check | Always check `if not token:` before decoding |

**RULE 8.1.2: Prevention Rules**
- CORRECT Review code for common mistakes before completion
- CORRECT Use service layer for all business logic
- CORRECT Use OAuth2PasswordBearer (not HTTPBearer)
- CORRECT Always check token for None before decoding
- CORRECT Pin bcrypt to 4.0.1

---

## RULE 9: Naming Conventions

### 9.1 File Naming

**RULE 9.1.1: File Naming Rules**
- CORRECT `router.py`, `schemas.py`, `models.py`, `service.py`
- INCORRECT `auth_router.py`, `user_schemas.py`, `database_models.py`

### 9.2 Function Naming

**RULE 9.2.1: Function Naming Rules**
- CORRECT `get_user_by_email(email: str) -> Optional[User]`
- INCORRECT `getUserByEmail(email)` (camelCase, no type hints)

### 9.3 Class Naming

**RULE 9.3.1: Class Naming Rules**
- CORRECT `AuthService`, `UserCreate`, `InvalidCredentialsException`
- INCORRECT `auth_service` (snake_case), `createUser` (camelCase)

### 9.4 Variable Naming

**RULE 9.4.1: Variable Naming Rules**
- CORRECT `user_data: UserCreate`, `access_token: str`
- INCORRECT `userData` (camelCase), `token` (not descriptive)

---

## RULE 10: HTTP Status Codes

### 10.1 Status Code Usage

**RULE 10.1.1: Status Code Reference Table**

| Status | When to use |
|--------|-------------|
| 200 | OK (GET, PUT) |
| 201 | Created (POST) |
| 204 | No Content (DELETE) |
| 400 | Bad Request |
| 401 | Unauthorized (authentication) |
| 403 | Forbidden (authorization) |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

**RULE 10.1.2: Status Code Rules**
- CORRECT Use appropriate status codes for each operation
- CORRECT Use 401 for authentication errors
- CORRECT Use 403 for authorization errors
- CORRECT Use 422 for validation errors
- CORRECT Use 404 for not found errors

---

## RULE 11: Verification Checklist

### 11.1 Module Structure Checklist

**RULE 11.1.1: Structure Verification**
- CORRECT Module structure follows standard layout
- CORRECT All required files exist
- CORRECT Files are properly organized

### 11.2 Layer Separation Checklist

**RULE 11.2.1: Layer Verification**
- CORRECT No business logic in routers
- CORRECT No database queries in routers
- CORRECT All business logic in service layer
- CORRECT All database operations in service layer

### 11.3 OAuth2 Checklist

**RULE 11.3.1: OAuth2 Verification**
- CORRECT OAuth2PasswordBearer used (NOT HTTPBearer)
- CORRECT Token endpoint created with Form params
- CORRECT Token endpoint returns OAuth2-compatible response
- CORRECT `auto_error=False` set on OAuth2PasswordBearer
- CORRECT Token None check before decoding

### 11.4 Security Checklist

**RULE 11.4.1: Security Verification**
- CORRECT bcrypt pinned to 4.0.1
- CORRECT All exceptions extend base exceptions
- CORRECT Type hints everywhere
- CORRECT No hardcoded secrets
- CORRECT Password validation in schemas
- CORRECT JWT tokens with proper expiry

---

## RULE 12: Golden Rules

### 12.1 Core Principles

**RULE 12.1.1: Golden Rules List**
1. CORRECT Separation of Concerns - Each layer has ONE job
2. CORRECT No Business Logic in Routers - Always use service layer
3. CORRECT Type Everything - Use type hints everywhere
4. CORRECT Custom Exceptions - Don't use generic HTTPException
5. CORRECT Security First - Never compromise on security
6. CORRECT OAuth2PasswordBearer - Required for Swagger UI
7. CORRECT Token Endpoint - Required for OAuth2 flow
8. CORRECT bcrypt 4.0.1 - Required for compatibility

**RULE 12.1.2: Golden Rules Application**
- CORRECT Apply all golden rules in every implementation
- CORRECT Review code against golden rules before completion
- CORRECT Use golden rules as checklist for verification

---

## RULE 13: FastAPI App Initialization with Swagger UI Token Persistence

### 13.1 Swagger UI Authorization Token Persistence

**CRITICAL RULE:** MUST configure FastAPI app with `swagger_ui_parameters` to persist authorization tokens on page refresh.

**RULE 13.1.1: CORRECT FastAPI App Initialization Pattern**
```python
# src/main.py
from fastapi import FastAPI
from src.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    swagger_ui_parameters={
        "persistAuthorization": True,  # Persist authorization token on page refresh
    },
)
```

**RULE 13.1.2: Swagger UI Parameters Rules**
- CORRECT MUST include `swagger_ui_parameters` in FastAPI app initialization
- CORRECT MUST set `persistAuthorization: True` to persist tokens on page refresh
- CORRECT This ensures users don't need to re-authenticate after refreshing Swagger UI page
- CORRECT Works with OAuth2PasswordBearer and OAuth2 token endpoint
- INCORRECT Missing `swagger_ui_parameters` (tokens lost on page refresh)
- INCORRECT Setting `persistAuthorization: False` (defeats the purpose)

**RULE 13.1.3: Benefits**
- CORRECT Users can refresh Swagger UI page without losing authorization
- CORRECT Better developer experience when testing APIs
- CORRECT Reduces need to re-enter credentials repeatedly
- CORRECT Works seamlessly with OAuth2PasswordBearer authentication flow

**RULE 13.1.4: Verification Checklist**
- CORRECT FastAPI app initialization includes `swagger_ui_parameters`
- CORRECT `persistAuthorization` is set to `True`
- CORRECT Token persists after refreshing Swagger UI page
- CORRECT OAuth2PasswordBearer is properly configured (see RULE 3)
- CORRECT OAuth2 token endpoint exists (see RULE 4)

---

## Summary

This guide provides rule-based instructions for implementing authentication module with proper layer separation and security. Each rule is numbered and contains specific, actionable requirements.

**Key Principles:**
- Separation of concerns - Each layer has one job
- Security first - Never compromise on security
- Type everything - Use type hints everywhere
- Custom exceptions - Don't use generic HTTPException

**Critical Reminders:**
- Use OAuth2PasswordBearer (not HTTPBearer) for Swagger UI
- Create OAuth2-compatible token endpoint with Form params
- Pin bcrypt to 4.0.1 (not 5.0.0)
- Always check token for None before decoding
- Keep all business logic in service layer
- Never put database queries in router layer
- Configure FastAPI app with `swagger_ui_parameters={"persistAuthorization": True}` to persist tokens on page refresh
