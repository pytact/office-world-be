"""Business logic for Employee Management module.

Service layer - all business logic, validation, and orchestration.
Based on F5_api_spec.md - Employee Management (F-005).
"""

from uuid import UUID
from typing import Optional
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.employees.models import Employee
from src.employees.repository import EmployeeRepository
from src.employees.schemas import (
    EmployeeListQuery,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeSummary,
    EmployeeDetail,
    EmployeePaginatedResponse,
    UserSummary,
)
from src.employees.exceptions import (
    EmployeeNotFound,
    UserNotFound,
    DuplicateEmployee,
    DuplicateWorkEmail,
    SeparationFieldsRequired,
    CannotSoftDeleteOwnEmployee,
    CannotDeactivateOwnEmployee,
    UserDifferentCompany,
    InsufficientPermissions,
    SuperAdminNoAccess,
    PreconditionRequired,
    PreconditionFailed,
)
from src.employees.constants import (
    VALID_SORT_FIELDS,
    VALID_SORT_ORDERS,
    EMPLOYMENT_STATUS_VALUES,
    DEPARTMENT_VALUES,
    EMPLOYMENT_TYPE_VALUES,
    EMPLOYMENT_LEVEL_VALUES,
    GENDER_VALUES,
    MARITAL_STATUS_VALUES,
    BLOOD_GROUP_VALUES,
    DOCUMENT_TYPE_VALUES,
    ROLE_CEO,
    ROLE_HR,
    ROLE_MANAGER,
    ROLE_EMPLOYEE,
    ROLE_SUPERADMIN,
)
from src.users.models import User
from src.permissions.models import UserRoleAssignment
from src.employees.utils import generate_etag, format_last_modified
from src.config import settings
from fastapi import status
from fastapi.responses import Response as FastAPIResponse
from src.exceptions import ValidationError
from src.permissions.constants import VALID_ROLE_CODES


class EmployeeService:
    """Service for employee management business logic.
    
    Based on F5_api_spec.md - All business rules in service layer.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = EmployeeRepository(session)

    def _validate_sort_field(self, sort_by: str) -> None:
        """Validate sort field."""
        if sort_by not in VALID_SORT_FIELDS:
            raise ValidationError(
                message=f"Invalid sort field: {sort_by}. Valid fields: {', '.join(VALID_SORT_FIELDS)}",
                error_code="INVALID_SORT_FIELD",
                details=[{"field": "sort_by", "issue": f"Invalid sort field: {sort_by}"}],
            )

    def _validate_sort_order(self, sort_order: str) -> None:
        """Validate sort order."""
        if sort_order not in VALID_SORT_ORDERS:
            raise ValidationError(
                message=f"Invalid sort order: {sort_order}. Valid orders: {', '.join(VALID_SORT_ORDERS)}",
                error_code="INVALID_SORT_ORDER",
                details=[{"field": "sort_order", "issue": f"Invalid sort order: {sort_order}"}],
            )

    def _validate_enum_value(self, value: Optional[str], valid_values: list[str], field_name: str) -> None:
        """Validate ENUM value."""
        if value is not None and value not in valid_values:
            raise ValidationError(
                message=f"Invalid {field_name}: {value}. Valid values: {', '.join(valid_values)}",
                error_code=f"INVALID_{field_name.upper()}",
                details=[{"field": field_name, "issue": f"Invalid {field_name}: {value}"}],
            )

    def _validate_separation_fields(self, employment_status: str, separation_initiated_date: Optional[date], separation_reason: Optional[str]) -> None:
        """Validate separation fields are required when employment_status is RESIGNED or TERMINATED."""
        if employment_status in ["RESIGNED", "TERMINATED"]:
            if separation_initiated_date is None or separation_reason is None:
                raise SeparationFieldsRequired()

    def _check_permissions(self, role: str, action: str) -> None:
        """Check if role has permission for action.
        
        Actions: list, create, get, update, delete
        
        Permissions:
        - list: CEO, HR, Manager, Employee (all company employees can view list)
        - create: CEO, HR only
        - get: CEO, HR, Manager, Employee (all company employees can view details)
        - update: CEO, HR only
        - delete: CEO, HR only
        """
        if role == ROLE_SUPERADMIN:
            raise SuperAdminNoAccess()
        
        # Allow employees for list and get actions
        if role == ROLE_EMPLOYEE and action not in ["list", "get"]:
            raise InsufficientPermissions()
        
        if action == "create" and role not in [ROLE_CEO, ROLE_HR]:
            raise InsufficientPermissions()
        
        if action == "update" and role not in [ROLE_CEO, ROLE_HR]:
            raise InsufficientPermissions()
        
        if action == "delete" and role not in [ROLE_CEO, ROLE_HR]:
            raise InsufficientPermissions()

    async def _get_user_with_company(self, user_id: UUID, company_id: UUID) -> tuple[User, bool]:
        """Get user and check if user belongs to company.
        
        Returns tuple of (User, belongs_to_company).
        """
        # Get user with role assignments
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.role_assignments))
            .where(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFound(str(user_id))
        
        # Check if user has active role assignment in this company
        belongs_to_company = False
        for assignment in user.role_assignments:
            if (
                assignment.is_active
                and assignment.deleted_at is None
                and assignment.company_id == company_id
            ):
                belongs_to_company = True
                break
        
        return user, belongs_to_company

    async def list_employees(
        self,
        company_id: Optional[UUID],
        query: EmployeeListQuery,
        role: str,
    ) -> EmployeePaginatedResponse:
        """List employees with pagination, filtering, and sorting.
        
        Based on F5_api_spec.md Section 5.1 - GET /api/v1/company/employees.
        """
        # Check permissions (raises SuperAdminNoAccess if role is superadmin)
        self._check_permissions(role, "list")
        
        # Company ID is required for employee endpoints (SuperAdmin excluded)
        if company_id is None:
            raise SuperAdminNoAccess()
        
        # Validate inputs
        self._validate_sort_field(query.sort_by)
        self._validate_sort_order(query.sort_order)
        
        # Validate role_code if provided
        if query.role_code is not None:
            if query.role_code.lower() not in VALID_ROLE_CODES:
                raise ValidationError(
                    message=f"Invalid role_code: {query.role_code}. Valid values: {', '.join(VALID_ROLE_CODES)}",
                    error_code="VALIDATION_FAILED",
                    details=[{"field": "role_code", "issue": f"Invalid role_code '{query.role_code}'. Valid values: {', '.join(VALID_ROLE_CODES)}"}],
                )
        
        # For Manager and Employee roles, exclude CEO and HR employees
        # BUT: If filtering by role_code=hr or role_code=ceo, don't exclude them (user specifically wants them)
        exclude_ceo_hr = role in [ROLE_MANAGER, ROLE_EMPLOYEE] and (
            query.role_code is None or query.role_code.lower() not in ["hr", "ceo"]
        )
        
        # Get employees from repository
        items, total = await self.repository.list_with_pagination(
            company_id=company_id,
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            department=query.department,
            employment_status=query.employment_status,
            exclude_ceo_hr=exclude_ceo_hr,
            role_code=query.role_code,  # Pass role_code filter from query
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        
        # Convert to response schemas
        employee_summaries = []
        for item in items:
            employee_summaries.append(
                EmployeeSummary(
                    employee_id=item.id,
                    user=UserSummary(
                        user_id=item.user.id,
                        email=item.user.email,
                        first_name=item.user.first_name,
                        last_name=item.user.last_name,
                    ),
                    job_title=item.job_title,
                    department=item.department,
                    employment_status=item.employment_status,
                    is_active=item.is_active,
                    joining_date=item.joining_date,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )
        
        # Calculate pagination metadata
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        
        # Build pagination URLs
        base_path = f"/api{settings.api_prefix}/company/employees"
        
        next_page = None
        prev_page = None
        
        if query.page < total_pages:
            # Build next_page URL with all query parameters
            next_params = []
            if query.page_size != 20:
                next_params.append(f"page_size={query.page_size}")
            if query.search is not None:
                next_params.append(f"search={query.search}")
            if query.department is not None:
                next_params.append(f"department={query.department}")
            if query.employment_status is not None:
                next_params.append(f"employment_status={query.employment_status}")
            if query.role_code is not None:
                next_params.append(f"role_code={query.role_code}")
            if query.sort_by != "created_at":
                next_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                next_params.append(f"sort_order={query.sort_order}")
            next_params.append(f"page={query.page + 1}")
            next_page = f"{base_path}?{'&'.join(next_params)}"
        
        if query.page > 1:
            # Build prev_page URL with all query parameters
            prev_params = []
            if query.page_size != 20:
                prev_params.append(f"page_size={query.page_size}")
            if query.search is not None:
                prev_params.append(f"search={query.search}")
            if query.department is not None:
                prev_params.append(f"department={query.department}")
            if query.employment_status is not None:
                prev_params.append(f"employment_status={query.employment_status}")
            if query.role_code is not None:
                prev_params.append(f"role_code={query.role_code}")
            if query.sort_by != "created_at":
                prev_params.append(f"sort_by={query.sort_by}")
            if query.sort_order != "desc":
                prev_params.append(f"sort_order={query.sort_order}")
            prev_params.append(f"page={query.page - 1}")
            prev_page = f"{base_path}?{'&'.join(prev_params)}"
        
        return EmployeePaginatedResponse(
            items=employee_summaries,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )

    async def get_employee_by_id(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        role: str,
        if_none_match: Optional[str] = None,
    ) -> EmployeeDetail | FastAPIResponse:
        """Get employee by ID with role-based field visibility and ETag support.
        
        Based on F5_api_spec.md Section 5.3 - GET /api/v1/company/employees/{employee_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        # Check permissions (raises SuperAdminNoAccess if role is superadmin)
        self._check_permissions(role, "get")
        
        # Company ID is required for employee endpoints (SuperAdmin excluded)
        if company_id is None:
            raise SuperAdminNoAccess()
        
        # Get employee from repository
        employee = await self.repository.get_by_id(employee_id, company_id=company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Generate ETag in service (business logic)
        etag = generate_etag(employee.updated_at)
        
        # Check If-None-Match in service (version validation)
        if if_none_match and if_none_match == etag:
            # Return 304 in service (business logic decision)
            return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
        
        # Calculate derived fields
        can_edit_employee = role in [ROLE_CEO, ROLE_HR]
        can_deactivate = role in [ROLE_CEO, ROLE_HR]  # Cannot deactivate own employee checked in update
        can_soft_delete = role in [ROLE_CEO, ROLE_HR]  # Cannot soft delete own employee checked in delete
        
        result = EmployeeDetail(
            employee_id=employee.id,
            user_id=employee.user_id,
            company_id=employee.company_id,
            joining_date=employee.joining_date,
            employment_status=employee.employment_status,
            job_title=employee.job_title,
            department=employee.department,
            employment_type=employee.employment_type,
            employment_level=employee.employment_level,
            work_email=employee.work_email,
            gender=employee.gender,
            marital_status=employee.marital_status,
            blood_group=employee.blood_group,
            nationality=employee.nationality,
            address=employee.address,
            city=employee.city,
            state=employee.state,
            country=employee.country,
            document_type=employee.document_type,
            document_number=employee.document_number,
            separation_initiated_date=employee.separation_initiated_date,
            separation_reason=employee.separation_reason,
            last_working_day=employee.last_working_day,
            notice_period_days=employee.notice_period_days,
            is_active=employee.is_active,
            is_deleted=employee.is_deleted,
            user=UserSummary(
                user_id=employee.user.id,
                email=employee.user.email,
                first_name=employee.user.first_name,
                last_name=employee.user.last_name,
            ),
            can_edit_employee=can_edit_employee,
            can_deactivate=can_deactivate,
            can_soft_delete=can_soft_delete,
            created_at=employee.created_at,
            updated_at=employee.updated_at,
            created_by=employee.created_by,
            updated_by=employee.updated_by,
        )
        # Attach ETag and Last-Modified for router
        result.etag = etag
        result.last_modified = employee.updated_at
        return result

    async def create_employee(
        self,
        data: EmployeeCreate,
        company_id: Optional[UUID],
        created_by: UUID,
    ) -> EmployeeDetail:
        """Create a new employee.
        
        Based on F5_api_spec.md Section 5.2 - POST /api/v1/company/employees.
        """
        # Company ID is required for employee endpoints (SuperAdmin excluded)
        if company_id is None:
            raise SuperAdminNoAccess()
        
        # Validate ENUM fields
        self._validate_enum_value(data.employment_status, EMPLOYMENT_STATUS_VALUES, "employment_status")
        if data.department is not None:
            self._validate_enum_value(data.department, DEPARTMENT_VALUES, "department")
        if data.employment_type is not None:
            self._validate_enum_value(data.employment_type, EMPLOYMENT_TYPE_VALUES, "employment_type")
        if data.employment_level is not None:
            self._validate_enum_value(data.employment_level, EMPLOYMENT_LEVEL_VALUES, "employment_level")
        if data.gender is not None:
            self._validate_enum_value(data.gender, GENDER_VALUES, "gender")
        if data.marital_status is not None:
            self._validate_enum_value(data.marital_status, MARITAL_STATUS_VALUES, "marital_status")
        if data.blood_group is not None:
            self._validate_enum_value(data.blood_group, BLOOD_GROUP_VALUES, "blood_group")
        if data.document_type is not None:
            self._validate_enum_value(data.document_type, DOCUMENT_TYPE_VALUES, "document_type")
        
        # Validate separation fields if needed
        self._validate_separation_fields(
            data.employment_status,
            data.separation_initiated_date,
            data.separation_reason,
        )
        
        # Validate joining_date is not in the future
        if data.joining_date > date.today():
            raise ValidationError(
                message="Joining date cannot be in the future",
                error_code="INVALID_JOINING_DATE",
                details=[{"field": "joining_date", "issue": "Joining date cannot be in the future"}],
            )
        
        # Check if user exists and belongs to company
        user, belongs_to_company = await self._get_user_with_company(data.user_id, company_id)
        if not belongs_to_company:
            raise UserDifferentCompany(str(data.user_id))
        
        # Check if user already has an employee record (one-to-one constraint)
        existing_employee = await self.repository.get_by_user_id(data.user_id, company_id=None)
        if existing_employee:
            raise DuplicateEmployee(str(data.user_id))
        
        # Check if work_email already exists in company (case-insensitive)
        if data.work_email:
            if await self.repository.check_work_email_exists(data.work_email, company_id):
                raise DuplicateWorkEmail(data.work_email)
        
        # Create employee
        employee = Employee(
            user_id=data.user_id,
            company_id=company_id,
            joining_date=data.joining_date,
            employment_status=data.employment_status,
            job_title=data.job_title,
            department=data.department,
            employment_type=data.employment_type,
            employment_level=data.employment_level,
            work_email=data.work_email,
            gender=data.gender,
            marital_status=data.marital_status,
            blood_group=data.blood_group,
            nationality=data.nationality,
            address=data.address,
            city=data.city,
            state=data.state,
            country=data.country,
            document_type=data.document_type,
            document_number=data.document_number,
            separation_initiated_date=data.separation_initiated_date,
            separation_reason=data.separation_reason,
            last_working_day=data.last_working_day,
            notice_period_days=data.notice_period_days,
            is_active=data.is_active if data.is_active is not None else True,
            is_deleted=False,
            created_by=created_by,
            updated_by=created_by,
        )
        
        employee = await self.repository.create(employee)
        
        # Return employee detail with ETag
        result = await self.get_employee_by_id(employee.id, company_id, ROLE_CEO, if_none_match=None)  # Use CEO role for full access
        # Attach ETag for newly created employee
        if isinstance(result, EmployeeDetail):
            result._etag = generate_etag(employee.updated_at)
            result._last_modified = employee.updated_at
        return result

    async def update_employee(
        self,
        employee_id: UUID,
        data: EmployeeUpdate,
        company_id: Optional[UUID],
        updated_by: UUID,
        role: str,
        if_match: Optional[str] = None,
    ) -> EmployeeDetail:
        """Update an employee with ETag validation.
        
        Based on F5_api_spec.md Section 5.4 - PATCH /api/v1/company/employees/{employee_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        # Check permissions (raises SuperAdminNoAccess if role is superadmin)
        self._check_permissions(role, "update")
        
        # Company ID is required for employee endpoints (SuperAdmin excluded)
        if company_id is None:
            raise SuperAdminNoAccess()
        
        # Get employee from repository
        employee = await self.repository.get_by_id(employee_id, company_id=company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Generate ETag in service
        current_etag = generate_etag(employee.updated_at)
        
        # Validate If-Match in service (business logic)
        if not if_match:
            raise PreconditionRequired()
        
        if if_match != current_etag:
            # Raise exception in service (business logic validation)
            raise PreconditionFailed()
        
        # Check if trying to deactivate own employee
        if data.is_active is False and employee.user_id == updated_by:
            raise CannotDeactivateOwnEmployee()
        
        # Validate ENUM fields if provided
        if data.employment_status is not None:
            self._validate_enum_value(data.employment_status, EMPLOYMENT_STATUS_VALUES, "employment_status")
        if data.department is not None:
            self._validate_enum_value(data.department, DEPARTMENT_VALUES, "department")
        if data.employment_type is not None:
            self._validate_enum_value(data.employment_type, EMPLOYMENT_TYPE_VALUES, "employment_type")
        if data.employment_level is not None:
            self._validate_enum_value(data.employment_level, EMPLOYMENT_LEVEL_VALUES, "employment_level")
        if data.gender is not None:
            self._validate_enum_value(data.gender, GENDER_VALUES, "gender")
        if data.marital_status is not None:
            self._validate_enum_value(data.marital_status, MARITAL_STATUS_VALUES, "marital_status")
        if data.blood_group is not None:
            self._validate_enum_value(data.blood_group, BLOOD_GROUP_VALUES, "blood_group")
        if data.document_type is not None:
            self._validate_enum_value(data.document_type, DOCUMENT_TYPE_VALUES, "document_type")
        
        # Validate separation fields if employment_status changes to RESIGNED or TERMINATED
        employment_status = data.employment_status or employee.employment_status
        separation_initiated_date = data.separation_initiated_date if data.separation_initiated_date is not None else employee.separation_initiated_date
        separation_reason = data.separation_reason if data.separation_reason is not None else employee.separation_reason
        
        self._validate_separation_fields(employment_status, separation_initiated_date, separation_reason)
        
        # Check if work_email already exists in company (case-insensitive, exclude current employee)
        if data.work_email and data.work_email != employee.work_email:
            if await self.repository.check_work_email_exists(data.work_email, company_id, exclude_employee_id=employee_id):
                raise DuplicateWorkEmail(data.work_email)
        
        # Update employee fields
        if data.employment_status is not None:
            employee.employment_status = data.employment_status
        if data.job_title is not None:
            employee.job_title = data.job_title
        if data.department is not None:
            employee.department = data.department
        if data.employment_type is not None:
            employee.employment_type = data.employment_type
        if data.employment_level is not None:
            employee.employment_level = data.employment_level
        if data.work_email is not None:
            employee.work_email = data.work_email
        if data.gender is not None:
            employee.gender = data.gender
        if data.marital_status is not None:
            employee.marital_status = data.marital_status
        if data.blood_group is not None:
            employee.blood_group = data.blood_group
        if data.nationality is not None:
            employee.nationality = data.nationality
        if data.address is not None:
            employee.address = data.address
        if data.city is not None:
            employee.city = data.city
        if data.state is not None:
            employee.state = data.state
        if data.country is not None:
            employee.country = data.country
        if data.document_type is not None:
            employee.document_type = data.document_type
        if data.document_number is not None:
            employee.document_number = data.document_number
        if data.separation_initiated_date is not None:
            employee.separation_initiated_date = data.separation_initiated_date
        if data.separation_reason is not None:
            employee.separation_reason = data.separation_reason
        if data.last_working_day is not None:
            employee.last_working_day = data.last_working_day
        if data.notice_period_days is not None:
            employee.notice_period_days = data.notice_period_days
        if data.is_active is not None:
            employee.is_active = data.is_active
        
        employee.updated_by = updated_by
        
        employee = await self.repository.update(employee)
        
        # Return employee detail with new ETag
        result = await self.get_employee_by_id(employee.id, company_id, role, if_none_match=None)
        # Attach new ETag after update
        if isinstance(result, EmployeeDetail):
            result._etag = generate_etag(employee.updated_at)
            result._last_modified = employee.updated_at
        return result

    async def soft_delete_employee(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        user_id: UUID,
        if_match: Optional[str] = None,
    ) -> None:
        """Soft delete an employee with ETag validation.
        
        Based on F5_api_spec.md Section 5.5 - DELETE /api/v1/employees/{employee_id}.
        ETag logic in service layer per error_prevention.md RULE 19.
        """
        # Company ID is required for employee endpoints (SuperAdmin excluded)
        if company_id is None:
            raise SuperAdminNoAccess()
        
        # Get employee from repository
        employee = await self.repository.get_by_id(employee_id, company_id=company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Generate ETag in service
        current_etag = generate_etag(employee.updated_at)
        
        # Validate If-Match in service (business logic)
        if not if_match:
            raise PreconditionRequired()
        
        if if_match != current_etag:
            # Raise exception in service (business logic validation)
            raise PreconditionFailed()
        
        # Check if trying to soft delete own employee
        if employee.user_id == user_id:
            raise CannotSoftDeleteOwnEmployee()
        
        # Soft delete employee
        await self.repository.soft_delete(employee)
