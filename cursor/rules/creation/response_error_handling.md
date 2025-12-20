# Standardized Response and Error Handling

**Purpose:** Implement standardized responses and error handling throughout the project.

---

## RULE 1: Response Format Structure

### 1.1 Success Response Format

**MANDATORY:** Success responses MUST follow this exact structure:

```json
{
  "data": { ... },
  "message": "Operation completed successfully"
}
```

**CRITICAL Rules:**
- CORRECT: Field order is CRITICAL: `data`, `message` (in that exact order)
- CORRECT: Success responses contain ONLY these two fields
- CORRECT: `data` contains the actual response payload
- CORRECT: `message` contains human-friendly success message

### 1.2 Error Response Format

**MANDATORY:** Error responses MUST follow this exact structure:

```json
{
  "error": {
    "code": "UPPER_SNAKE_CODE",
    "details": [{"field": "field_name", "issue": "What is wrong"}]
  },
  "message": "Human friendly error message"
}
```

**CRITICAL Rules:**
- CORRECT: Field order is CRITICAL: `error`, `message` (in that exact order)
- CORRECT: The `error` object MUST contain ONLY `code` and `details`
- CORRECT: The `error` object MUST NOT contain `message` field
- CORRECT: The `message` field is ONLY at root level, never inside `error` object
- CORRECT: `code` uses UPPER_SNAKE_CASE format
- CORRECT: `details` is an array of objects with `field` and `issue` properties

**WRONG Patterns:**
```json
// INCORRECT: ERROR: message inside error object
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"  // INCORRECT: ERROR: message should be at root level
  }
}

// INCORRECT: ERROR: Wrong field order
{
  "message": "Error occurred",
  "error": {...}
}
```

---

## RULE 2: Base Exception Types

### 2.1 Exception Class Hierarchy

**MANDATORY:** All domain exceptions MUST extend base exception classes from `src.exceptions`.

**Available Base Exception Types:**

| Exception | HTTP Status | Auto Code | Use Case |
|-----------|-------------|-----------|----------|
| `BadRequestError` | 400 | Custom | Bad input/invalid format |
| `UnauthenticatedError` | 401 | Custom | Missing/invalid token |
| `ForbiddenError` | 403 | Custom | Insufficient permissions |
| `NotFoundError` | 404 | `<DOMAIN>_NOT_FOUND` | Resource not found |
| `ConflictError` | 409 | Custom | Resource conflicts/duplicates |
| `ValidationError` | 422 | Custom | Domain rule violations |
| `InternalServerError` | 500 | Custom | Server errors |

**CRITICAL:** Use `UnauthenticatedError` (NOT `UnauthorizedError`) for 401 errors.

### 2.2 Exception Definition Pattern

**RULE 2.2.1: Not Found Exception**
```python
from src.exceptions import NotFoundError

# Not Found (auto-generates RESOURCE_NOT_FOUND code)
class ResourceNotFound(NotFoundError):  # ⚠️ Use user's actual exception name
    def __init__(self, resource_id: str):  # ⚠️ Use user's actual parameter name
        super().__init__(
            resource="Resource",  # ⚠️ Use user's actual resource name
            resource_id=resource_id
        )
```

**RULE 2.2.2: Conflict Exception**
```python
from src.exceptions import ConflictError

# Conflict (duplicate)
class UserEmailExists(ConflictError):  # ⚠️ Use user's actual exception name
    def __init__(self, email: str):
        super().__init__(
            message=f"User with email {email} already exists",
            error_code="DUPLICATE_EMAIL",
            details=[{"field": "email", "issue": email}]
        )
```

**RULE 2.2.3: Unauthenticated Exception**
```python
from src.exceptions import UnauthenticatedError

# Unauthenticated (401) - CRITICAL: Use UnauthenticatedError, NOT UnauthorizedError
class InvalidCredentials(UnauthenticatedError):  # ⚠️ Use user's actual exception name
    def __init__(self):
        super().__init__(
            message="Invalid email or password",
            error_code="INVALID_CREDENTIALS",
            details=[{"field": "email", "issue": "Invalid email or password"}]
        )
```

**RULE 2.2.4: WRONG Patterns (DO NOT DO THIS)**
```python
# INCORRECT: Using HTTPException directly
class ResourceNotFound(HTTPException):  # INCORRECT: ERROR: Must extend base exception
    ...

# INCORRECT: Using UnauthorizedError (doesn't exist)
from src.exceptions import UnauthorizedError  # INCORRECT: ERROR: Use UnauthenticatedError
```

---

## RULE 3: Router Response Pattern

### 3.1 StandardResponse Wrapper

**MANDATORY:** All endpoints MUST use `StandardResponse[T]` wrapper.

**RULE 3.1.1: Single Item Response**
```python
from src.schemas import StandardResponse
from src.module.schemas import ResourceResponse  # ⚠️ Use user's actual imports

@router.get("/{id}", response_model=StandardResponse[ResourceResponse])
async def get_resource(id: UUID, ...):  # ⚠️ Use user's actual names
    resource = await service.get_resource(id)
    return StandardResponse(
        data=resource,
        message="Resource retrieved successfully"  # ⚠️ Use user's actual resource name
    )
```

**RULE 3.1.2: List Response**
```python
@router.get("", response_model=StandardResponse[List[ResourceResponse]])
async def list_resources(...):  # ⚠️ Use user's actual names
    resources = await service.list_resources()
    return StandardResponse(
        data=resources,
        message="Resources retrieved successfully"
    )
```

**RULE 3.1.3: Delete Response (No Data)**
```python
@router.delete("/{id}", response_model=StandardResponse[dict])
async def delete_resource(id: UUID, ...):  # ⚠️ Use user's actual names
    await service.delete_resource(id)
    return StandardResponse(
        data={},
        message="Resource deleted successfully"
    )
```

**RULE 3.1.4: WRONG Patterns (DO NOT DO THIS)**
```python
# INCORRECT: Missing StandardResponse wrapper
@router.get("/{id}", response_model=ResourceResponse)
async def get_resource(...):
    return resource  # INCORRECT: ERROR: Must wrap in StandardResponse

# INCORRECT: Inconsistent format
@router.get("/{id}")
async def get_resource(...):
    return {"data": resource}  # INCORRECT: ERROR: Must use StandardResponse format

# INCORRECT: Missing response_model
@router.get("/{id}")
async def get_resource(...):
    return StandardResponse(...)  # INCORRECT: ERROR: Must specify response_model
```

### 3.2 Response Model Specification

**MANDATORY:** MUST specify `response_model=StandardResponse[T]` in router decorator.

**Correct Pattern:**
```python
@router.get("/{id}", response_model=StandardResponse[ResourceResponse])
async def get_resource(...):
    ...
```

**Wrong Pattern:**
```python
@router.get("/{id}")  # INCORRECT: ERROR: Missing response_model
async def get_resource(...):
    ...
```

---

## RULE 4: Service Layer Pattern

### 4.1 Exception Raising

**MANDATORY:** Services MUST raise exceptions (NOT return error responses).

**RULE 4.1.1: Correct Pattern**
```python
# CORRECT: CORRECT: Raise exception
async def get_resource(self, resource_id: UUID) -> Resource:  # ⚠️ Use user's actual names
    resource = await self.repository.get_by_id(resource_id)
    if not resource:
        raise ResourceNotFound(str(resource_id))  # CORRECT: Raise exception
    return resource
```

**RULE 4.1.2: WRONG Pattern**
```python
# INCORRECT: WRONG: Return error response
async def get_resource(self, resource_id: UUID):
    resource = await self.repository.get_by_id(resource_id)
    if not resource:
        return {"error": "Not found"}  # INCORRECT: Don't return error responses
    return resource
```

### 4.2 Service Exception Handling

**MANDATORY:** Services raise exceptions, routers let them propagate to global handlers.

**Key Principles:**
- CORRECT: Services raise exceptions when errors occur
- CORRECT: Services return domain models or response schemas on success
- CORRECT: Services do NOT catch exceptions (let them propagate)
- CORRECT: Services do NOT return error responses

---

## RULE 5: Router Layer Pattern

### 5.1 Exception Propagation

**MANDATORY:** Routers MUST NOT handle exceptions - let global handlers do it.

**RULE 5.1.1: Correct Pattern**
```python
# CORRECT: CORRECT: Let exception propagate
@router.get("/{id}", response_model=StandardResponse[ResourceResponse])
async def get_resource(id: UUID, ...):  # ⚠️ Use user's actual names
    service = ResourceService(session)
    resource = await service.get_resource(id)  # Exception auto-handled by global handler
    return StandardResponse(
        data=resource,
        message="Resource retrieved successfully"
    )
```

**RULE 5.1.2: WRONG Pattern**
```python
# INCORRECT: WRONG: Try-catch in router
@router.get("/{id}")
async def get_resource(id: UUID, ...):
    try:
        resource = await service.get_resource(id)
    except ResourceNotFound:
        return {"error": "Not found"}  # INCORRECT: Don't handle exceptions in routers
```

### 5.2 Router Exception Handling Rules

**MANDATORY:**
- CORRECT: Routers do NOT use try-catch blocks
- CORRECT: Routers let exceptions propagate to global handlers
- CORRECT: Routers only wrap successful responses in `StandardResponse`
- CORRECT: Routers do NOT return error responses directly

**DO NOT:**
- INCORRECT: Add try-catch blocks in routers
- INCORRECT: Return error responses directly in routers
- INCORRECT: Handle exceptions manually in routers

---

## RULE 6: Exception Handler Registration

### 6.1 Handler Registration Order

**CRITICAL:** Handlers registered in `src/main.py` - DO NOT modify order.

**MANDATORY Order:**
```python
# Order matters - most specific first
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
# ... database handlers ...
app.add_exception_handler(Exception, catch_all_exception_handler)  # Last
```

**CRITICAL Rules:**
- CORRECT: Most specific exceptions first
- CORRECT: Generic exceptions last
- CORRECT: `Exception` handler must be registered last (catch-all)
- CORRECT: DO NOT modify this order

### 6.2 Handler Registration Rules

**DO NOT:**
- INCORRECT: Add custom exception handlers in routers
- INCORRECT: Return error responses directly in routers
- INCORRECT: Modify exception handler registration order
- INCORRECT: Register handlers in multiple places

---

## RULE 7: Success Message Standards

### 7.1 Message Format

**MANDATORY:** Use consistent success messages following this pattern:

- **Create:** `"{Resource} created successfully"`
- **Get:** `"{Resource} retrieved successfully"`
- **List:** `"{Resources} retrieved successfully"`
- **Update:** `"{Resource} updated successfully"`
- **Delete:** `"{Resource} deleted successfully"`

### 7.2 Message Examples

**Correct Patterns:**
```python
# Create
return StandardResponse(
    data=resource,
    message="User created successfully"
)

# Get
return StandardResponse(
    data=resource,
    message="User retrieved successfully"
)

# List
return StandardResponse(
    data=resources,
    message="Users retrieved successfully"
)

# Update
return StandardResponse(
    data=resource,
    message="User updated successfully"
)

# Delete
return StandardResponse(
    data={},
    message="User deleted successfully"
)
```

---

## RULE 8: HTTP Status Codes

### 8.1 Status Code Reference

| Status | When to Use | Typical Error Code |
|--------|-------------|-------------------|
| 200 | Successful read/update | - |
| 201 | Resource created | - |
| 204 | Successful delete/no content | - |
| 400 | Bad input/invalid format | `INVALID_REQUEST` / `VALIDATION_FAILED` |
| 401 | Missing/invalid token | `UNAUTHENTICATED` |
| 403 | Valid token, insufficient rights | `INSUFFICIENT_PERMISSIONS` |
| 404 | Resource not found | `<DOMAIN>_NOT_FOUND` |
| 409 | Business conflict/duplicate | `DUPLICATE_<THING>` / `RESOURCE_IN_USE` |
| 422 | Domain rule violation | `BUSINESS_RULE_FAILED` / `VALIDATION_FAILED` |
| 500 | Server error | `INTERNAL_ERROR` |

### 8.2 Status Code Rules

**MANDATORY:**
- CORRECT: Use appropriate HTTP status codes for each operation
- CORRECT: 201 for POST (create) operations
- CORRECT: 200 for GET, PATCH, PUT, DELETE operations
- CORRECT: Status codes are automatically set by exception handlers
- CORRECT: DO NOT manually set status codes in routers (exception handlers do this)

---

## RULE 9: Error Codes

### 9.1 Error Code Patterns

| Code Pattern | HTTP | Description |
|--------------|------|-------------|
| `<DOMAIN>_NOT_FOUND` | 404 | Resource not found (auto-generated by `NotFoundError`) |
| `DUPLICATE_<FIELD>` | 409 | Duplicate value (field must be unique) |
| `VALIDATION_FAILED` | 400/422 | Input validation failed (see `details[]`) |
| `RESOURCE_IN_USE` | 409 | Cannot delete (FK/reference exists) |
| `INVALID_REQUEST` | 400 | Bad request (invalid input format) |
| `UNAUTHENTICATED` | 401 | Authentication required (missing/invalid token) |
| `INSUFFICIENT_PERMISSIONS` | 403 | Insufficient permissions (valid token but no access) |
| `BUSINESS_RULE_FAILED` | 422 | Business rule violation (domain-specific) |
| `INTERNAL_ERROR` | 500 | Internal server error (unexpected error) |

### 9.2 Error Code Rules

**MANDATORY:**
- CORRECT: Use UPPER_SNAKE_CASE format for error codes
- CORRECT: Use descriptive, specific error codes
- CORRECT: Follow naming patterns shown above
- CORRECT: `NotFoundError` automatically generates `<DOMAIN>_NOT_FOUND` code
- CORRECT: Custom error codes for other exception types

---

## RULE 10: Critical Rules Summary

### 10.1 Mandatory Rules

**ALWAYS:**
1. CORRECT: Use `StandardResponse[T]` wrapper for all responses
2. CORRECT: Specify `response_model=StandardResponse[T]` in router decorators
3. CORRECT: Extend base exception classes (NOT `HTTPException`)
4. CORRECT: Use `UnauthenticatedError` (NOT `UnauthorizedError`) for 401 errors
5. CORRECT: Raise exceptions in services (NOT return error responses)
6. CORRECT: Let exceptions propagate in routers (NO try-catch)
7. CORRECT: Maintain field order: `data`/`error`, `message`
8. CORRECT: Include `message` field ONLY at root level (never inside `error` object)
9. CORRECT: Use consistent success message formats
10. CORRECT: Follow HTTP status code conventions

**NEVER:**
1. INCORRECT: Include `message` field inside `error` object
2. INCORRECT: Handle exceptions in routers
3. INCORRECT: Return error responses from services
4. INCORRECT: Modify exception handler registration order
5. INCORRECT: Use `HTTPException` directly (use base exceptions)
6. INCORRECT: Use `UnauthorizedError` (use `UnauthenticatedError`)
7. INCORRECT: Skip `response_model` in router decorators
8. INCORRECT: Return raw data without `StandardResponse` wrapper
9. INCORRECT: Use inconsistent success message formats
10. INCORRECT: Manually set status codes in routers

---

## RULE 11: Common Mistakes

### 11.1 Mistake Reference Table

| Mistake | Correct Approach |
|---------|------------------|
| Returning raw data without `StandardResponse` | Wrap in `StandardResponse(data=..., message=...)` |
| Using `HTTPException` directly | Extend base exception (`NotFoundError`, `ConflictError`, etc.) |
| Using `UnauthorizedError` | Use `UnauthenticatedError` (correct class name) |
| Handling exceptions in routers | Let global handlers catch exceptions |
| Returning error responses from services | Raise exceptions instead |
| Missing `response_model` in decorator | Add `response_model=StandardResponse[T]` |
| Including `message` in `error` object | `message` only at root level, `error` has only `code` and `details` |
| Wrong field order | Success: `data`, `message` / Error: `error`, `message` |
| Try-catch blocks in routers | Remove try-catch, let exceptions propagate |
| Inconsistent success messages | Follow naming convention: `"{Resource} {action} successfully"` |

---

## RULE 12: Verification Checklist

### 12.1 Endpoint Verification

Before marking any endpoint as complete, verify:

- [ ] Response uses `StandardResponse[T]` wrapper
- [ ] `response_model=StandardResponse[T]` specified in decorator
- [ ] Success message follows naming convention
- [ ] Exceptions extend base exception classes (NOT `HTTPException`)
- [ ] Using `UnauthenticatedError` (NOT `UnauthorizedError`) for 401 errors
- [ ] No try-catch blocks in routers
- [ ] Services raise exceptions (not return errors)
- [ ] Field order correct: Success (`data`, `message`) / Error (`error`, `message`)
- [ ] `error` object contains ONLY `code` and `details` (NO `message`)
- [ ] `message` field is ONLY at root level (never inside `error` object)

### 12.2 Service Verification

Before marking any service method as complete, verify:

- [ ] Service raises exceptions when errors occur
- [ ] Service does NOT return error responses
- [ ] Service does NOT catch exceptions (lets them propagate)
- [ ] Service returns domain models or response schemas on success

### 12.3 Exception Verification

Before marking any exception as complete, verify:

- [ ] Exception extends base exception class (NOT `HTTPException`)
- [ ] Exception uses correct base class for HTTP status code
- [ ] Exception provides appropriate error code
- [ ] Exception provides appropriate error details
- [ ] Exception message is human-friendly

---

## RULE 13: Files Reference

### 13.1 Required Files

**Response Schemas:**
- File: `src/schemas.py`
- Contains: `StandardResponse`, `ErrorInfo`, `ErrorDetail`

**Base Exceptions:**
- File: `src/exceptions.py`
- Contains: `BadRequestError`, `UnauthenticatedError`, `ForbiddenError`, `NotFoundError`, `ConflictError`, `ValidationError`, `InternalServerError`

**Exception Handlers:**
- File: `src/exceptions.py`
- Contains: Handler functions for each exception type

**Handler Registration:**
- File: `src/main.py`
- Contains: Exception handler registration (DO NOT modify order)

### 13.2 File Structure Rules

**MANDATORY:**
- CORRECT: Response schemas defined in `src/schemas.py`
- CORRECT: Base exceptions defined in `src/exceptions.py`
- CORRECT: Exception handlers defined in `src/exceptions.py`
- CORRECT: Handler registration in `src/main.py`
- CORRECT: Domain exceptions in `src/<module>/exceptions.py`

---

## Summary

This guide provides rule-based instructions for implementing standardized responses and error handling. Each rule is numbered and contains specific, actionable requirements.

**Key Principles:**
- All responses use `StandardResponse[T]` wrapper
- All exceptions extend base exception classes
- Services raise exceptions, routers let them propagate
- Global exception handlers format all error responses
- Consistent field order and message formats throughout

**Critical Reminders:**
- Use `UnauthenticatedError` (NOT `UnauthorizedError`) for 401 errors
- `message` field is ONLY at root level, never inside `error` object
- Field order is CRITICAL: `data`/`error`, `message`
- DO NOT handle exceptions in routers - let global handlers do it
