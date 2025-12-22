"""Business logic for Salary Management module.

Service layer - all business logic, validation, and orchestration.
Based on F6_api_spec.md - Salary Management (F-006).
"""

from uuid import UUID
from typing import Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import status
from fastapi.responses import Response as FastAPIResponse

from src.salaries.repository import SalaryRepository
from src.salaries.schemas import (
    SalaryCreate,
    BankInfoUpsert,
    SalaryPaymentCreate,
    SalaryOverviewQuery,
    SalaryPaymentListQuery,
    SalaryOverviewResponse,
    SalaryDetailsResponse,
    BankInfoResponse,
    SalaryHistoryResponse,
    SalaryPaymentResponse,
    SalaryPaymentListItem,
    EmployeeBasicInfo,
    SalaryPaymentPaginatedResponse,
)
from src.salaries.models import BankInfo, SalaryDetails, SalaryPayment, SalaryHistory
from src.salaries.exceptions import (
    EmployeeNotFound,
    OverlappingSalaryPeriod,
    DuplicateSalaryPayment,
    NoActiveSalary,
    PreconditionRequired,
    PreconditionFailed,
    SalarySlipNotFound,
)
from src.salaries.utils import (
    generate_etag,
    format_last_modified,
    mask_account_number,
    mask_ifsc_code,
    generate_payment_period_label,
    get_latest_updated_at,
)
from src.salaries.constants import (
    SUCCESS_SALARY_OVERVIEW_RETRIEVED,
    SUCCESS_SALARY_DETAILS_CREATED,
    SUCCESS_BANK_INFO_UPDATED,
    SUCCESS_SALARY_PAYMENT_CREATED,
    SUCCESS_SALARY_PAYMENTS_RETRIEVED,
)
from src.employees.models import Employee
from src.users.models import User
from src.pagination import PagedCollection


class SalaryService:
    """Service for salary management business logic.
    
    Based on F6_api_spec.md - All business rules in service layer.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = SalaryRepository(session)

    async def _get_user_name(self, user_id: Optional[UUID]) -> Optional[str]:
        """Get user full name from user_id.
        
        Returns None if user_id is None or user not found.
        """
        if user_id is None:
            return None
        
        result = await self.session.execute(
            select(User)
            .where(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Return full name if available, otherwise email
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        elif user.first_name:
            return user.first_name
        elif user.last_name:
            return user.last_name
        else:
            return user.email

    async def get_salary_overview(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        query: SalaryOverviewQuery,
        if_none_match: Optional[str] = None,
    ) -> SalaryOverviewResponse | FastAPIResponse:
        """Get salary overview for employee with ETag support.
        
        Based on F6_api_spec.md Section 4.3.1 - GET /v1/company/employees/{employee_id}/salary.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Gets active salary details
        - Gets bank info
        - Gets salary history (if requested)
        - Gets recent payments (if requested)
        - Generates ETag from latest updated_at
        - Handles If-None-Match for cache validation
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get active salary details
        current_salary = await self.repository.get_active_salary_details(employee_id)
        
        # Get bank info
        bank_info = await self.repository.get_bank_info(employee_id)
        
        # Get salary history (if requested)
        salary_history_list = []
        if query.include_history and current_salary:
            history_records = await self.repository.get_salary_history_by_salary_details_id(current_salary.id)
            for history in history_records:
                changed_by_name = await self._get_user_name(history.changed_by)
                salary_history_list.append(
                    SalaryHistoryResponse(
                        id=history.id,
                        previous_amount=history.previous_amount,
                        new_amount=history.new_amount,
                        effective_from=history.effective_from,
                        changed_by=changed_by_name,
                        created_at=history.created_at,
                    )
                )
        
        # Get recent payments (if requested)
        recent_payments_list = []
        if query.include_payments:
            payments, _ = await self.repository.list_salary_payments(
                employee_id=employee_id,
                page=1,
                page_size=query.payment_limit,
                sort_by="paid_on",
                sort_order="desc",
            )
            for payment in payments:
                created_by_name = await self._get_user_name(payment.created_by)
                recent_payments_list.append(
                    SalaryPaymentListItem(
                        id=payment.id,
                        employee_id=payment.employee_id,
                        amount=payment.amount,
                        currency=payment.currency,
                        month=payment.month,
                        year=payment.year,
                        paid_on=payment.paid_on,
                        payment_method=payment.payment_method,
                        slip_url=payment.slip_url,
                        created_at=payment.created_at,
                        created_by=created_by_name,
                    )
                )
        
        # Build employee basic info
        employee_basic = EmployeeBasicInfo(
            id=employee.id,
            first_name=employee.user.first_name or "",
            last_name=employee.user.last_name or "",
            is_active=employee.is_active,
        )
        
        # Build current salary response (if exists)
        current_salary_response = None
        if current_salary:
            created_by_name = await self._get_user_name(current_salary.created_by)
            updated_by_name = await self._get_user_name(current_salary.updated_by)
            current_salary_response = SalaryDetailsResponse(
                id=current_salary.id,
                employee_id=current_salary.employee_id,
                amount=current_salary.amount,
                currency=current_salary.currency,
                payment_frequency=current_salary.payment_frequency,
                effective_from=current_salary.effective_from,
                effective_to=current_salary.effective_to,
                created_at=current_salary.created_at,
                updated_at=current_salary.updated_at,
                created_by=created_by_name,
                updated_by=updated_by_name,
            )
        
        # Build bank info response (if exists, with masking)
        bank_info_response = None
        masked_account_number = None
        if bank_info:
            created_by_name = await self._get_user_name(bank_info.created_by)
            updated_by_name = await self._get_user_name(bank_info.updated_by)
            bank_info_response = BankInfoResponse(
                id=bank_info.id,
                employee_id=bank_info.employee_id,
                bank_name=bank_info.bank_name,
                branch=bank_info.branch,
                account_number=mask_account_number(bank_info.account_number),  # Masked
                ifsc_code=mask_ifsc_code(bank_info.ifsc_code),  # Masked
                created_at=bank_info.created_at,
                updated_at=bank_info.updated_at,
                created_by=created_by_name,
                updated_by=updated_by_name,
            )
            masked_account_number = mask_account_number(bank_info.account_number)
        
        # Generate ETag from latest updated_at
        timestamps = []
        if current_salary:
            timestamps.append(current_salary.updated_at)
        if bank_info:
            timestamps.append(bank_info.updated_at)
        latest_updated_at = get_latest_updated_at(*timestamps)
        
        if latest_updated_at:
            etag = generate_etag(latest_updated_at)
            
            # Check If-None-Match for cache validation
            if if_none_match and if_none_match == etag:
                return FastAPIResponse(status_code=status.HTTP_304_NOT_MODIFIED)
            
            # Attach ETag to response (for router to set header)
            overview = SalaryOverviewResponse(
                employee=employee_basic,
                current_salary=current_salary_response,
                bank_info=bank_info_response,
                salary_history=salary_history_list,
                recent_payments=recent_payments_list,
                current_salary_amount=current_salary.amount if current_salary else None,
                current_salary_currency=current_salary.currency if current_salary else None,
                has_active_salary=current_salary is not None,
                masked_account_number=masked_account_number,
            )
            overview._etag = etag  # Attach for router
            overview._last_modified = latest_updated_at
            return overview
        
        # No timestamps available (no salary or bank info)
        return SalaryOverviewResponse(
            employee=employee_basic,
            current_salary=current_salary_response,
            bank_info=bank_info_response,
            salary_history=salary_history_list,
            recent_payments=recent_payments_list,
            current_salary_amount=None,
            current_salary_currency=None,
            has_active_salary=False,
            masked_account_number=masked_account_number,
        )

    async def create_or_update_salary(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: SalaryCreate,
        user_id: UUID,
        if_match: Optional[str] = None,
    ) -> SalaryDetailsResponse:
        """Create or update salary details with ETag validation.
        
        Based on F6_api_spec.md Section 4.3.2 - POST /v1/company/employees/{employee_id}/salary.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates no overlapping salary periods
        - Gets current active salary (if exists)
        - Validates ETag if updating existing salary
        - Closes previous active salary (sets effective_to)
        - Creates new salary details
        - Creates salary history entry (if previous salary existed)
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get current active salary
        current_salary = await self.repository.get_active_salary_details(employee_id)
        
        # If updating existing salary, validate ETag
        if current_salary:
            if not if_match:
                raise PreconditionRequired()
            
            current_etag = generate_etag(current_salary.updated_at)
            if if_match != current_etag:
                raise PreconditionFailed()
        
        # Validate no overlapping periods
        has_overlap = await self.repository.check_overlapping_salary_period(
            employee_id=employee_id,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            exclude_salary_details_id=current_salary.id if current_salary else None,
        )
        if has_overlap:
            raise OverlappingSalaryPeriod()
        
        # Close previous active salary (if exists)
        previous_amount = None
        if current_salary:
            previous_amount = current_salary.amount
            # Set effective_to to effective_from - 1 day
            current_salary.effective_to = data.effective_from - timedelta(days=1)
            current_salary.updated_by = user_id
            await self.repository.update_salary_details(current_salary)
        
        # Create new salary details
        new_salary = SalaryDetails(
            employee_id=employee_id,
            amount=data.amount,
            currency=data.currency,
            payment_frequency=data.payment_frequency,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            created_by=user_id,
            updated_by=user_id,
        )
        new_salary = await self.repository.create_salary_details(new_salary)
        
        # Create salary history entry (if previous salary existed)
        if current_salary:
            history = SalaryHistory(
                salary_details_id=new_salary.id,
                previous_amount=previous_amount,
                new_amount=data.amount,
                effective_from=data.effective_from,
                changed_by=user_id,
            )
            await self.repository.create_salary_history(history)
        
        # Build response
        created_by_name = await self._get_user_name(new_salary.created_by)
        updated_by_name = await self._get_user_name(new_salary.updated_by)
        
        response = SalaryDetailsResponse(
            id=new_salary.id,
            employee_id=new_salary.employee_id,
            amount=new_salary.amount,
            currency=new_salary.currency,
            payment_frequency=new_salary.payment_frequency,
            effective_from=new_salary.effective_from,
            effective_to=new_salary.effective_to,
            created_at=new_salary.created_at,
            updated_at=new_salary.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = generate_etag(new_salary.updated_at)  # Attach for router
        return response

    async def upsert_bank_info(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: BankInfoUpsert,
        user_id: UUID,
        if_match: Optional[str] = None,
    ) -> BankInfoResponse:
        """Upsert bank information with ETag validation.
        
        Based on F6_api_spec.md Section 4.3.3 - PATCH /v1/company/employees/{employee_id}/salary/bank-info.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Gets existing bank info (if exists)
        - Validates ETag if updating existing bank info
        - Creates new or updates existing bank info
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get existing bank info
        existing_bank_info = await self.repository.get_bank_info(employee_id)
        
        # If updating existing bank info, validate ETag
        if existing_bank_info:
            if not if_match:
                raise PreconditionRequired()
            
            current_etag = generate_etag(existing_bank_info.updated_at)
            if if_match != current_etag:
                raise PreconditionFailed()
            
            # Update existing bank info
            existing_bank_info.bank_name = data.bank_name
            existing_bank_info.branch = data.branch
            existing_bank_info.account_number = data.account_number
            existing_bank_info.ifsc_code = data.ifsc_code
            existing_bank_info.updated_by = user_id
            
            updated_bank_info = await self.repository.update_bank_info(existing_bank_info)
            bank_info = updated_bank_info
        else:
            # Create new bank info
            new_bank_info = BankInfo(
                employee_id=employee_id,
                bank_name=data.bank_name,
                branch=data.branch,
                account_number=data.account_number,
                ifsc_code=data.ifsc_code,
                created_by=user_id,
                updated_by=user_id,
            )
            bank_info = await self.repository.create_bank_info(new_bank_info)
        
        # Build response (with masking)
        created_by_name = await self._get_user_name(bank_info.created_by)
        updated_by_name = await self._get_user_name(bank_info.updated_by)
        
        response = BankInfoResponse(
            id=bank_info.id,
            employee_id=bank_info.employee_id,
            bank_name=bank_info.bank_name,
            branch=bank_info.branch,
            account_number=mask_account_number(bank_info.account_number),  # Masked
            ifsc_code=mask_ifsc_code(bank_info.ifsc_code),  # Masked
            created_at=bank_info.created_at,
            updated_at=bank_info.updated_at,
            created_by=created_by_name,
            updated_by=updated_by_name,
        )
        response._etag = generate_etag(bank_info.updated_at)  # Attach for router
        return response

    async def create_salary_payment(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        data: SalaryPaymentCreate,
        user_id: UUID,
    ) -> SalaryPaymentResponse:
        """Create salary payment record.
        
        Based on F6_api_spec.md Section 4.3.4 - POST /v1/company/employees/{employee_id}/salary/payments.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates no duplicate payment for same month/year
        - Gets active salary for payment month
        - Creates salary payment record
        - Returns payment with derived fields
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Check for duplicate payment
        is_duplicate = await self.repository.check_duplicate_payment(
            employee_id=employee_id,
            month=data.month,
            year=data.year,
        )
        if is_duplicate:
            raise DuplicateSalaryPayment(data.month, data.year)
        
        # Get active salary for payment month
        active_salary = await self.repository.get_active_salary_for_payment_month(
            employee_id=employee_id,
            month=data.month,
            year=data.year,
        )
        if not active_salary:
            raise NoActiveSalary()
        
        # Create salary payment
        payment = SalaryPayment(
            employee_id=employee_id,
            amount=active_salary.amount,
            currency=active_salary.currency,
            month=data.month,
            year=data.year,
            paid_on=data.paid_on,
            payment_method=data.payment_method,
            slip_url=None,  # Will be set by async slip generation
            created_by=user_id,
        )
        payment = await self.repository.create_salary_payment(payment)
        
        # Build response with derived fields
        created_by_name = await self._get_user_name(payment.created_by)
        slip_url = f"/v1/company/employees/{employee_id}/salary/payments/{payment.id}/slip" if payment.slip_url else None
        
        response = SalaryPaymentResponse(
            id=payment.id,
            employee_id=payment.employee_id,
            amount=payment.amount,
            currency=payment.currency,
            month=payment.month,
            year=payment.year,
            paid_on=payment.paid_on,
            payment_method=payment.payment_method,
            slip_url=slip_url,
            payable_amount=payment.amount,  # Derived field
            payment_period_label=generate_payment_period_label(payment.month, payment.year),  # Derived field
            created_at=payment.created_at,
            created_by=created_by_name,
        )
        return response

    async def list_salary_payments(
        self,
        employee_id: UUID,
        company_id: Optional[UUID],
        query: SalaryPaymentListQuery,
    ) -> SalaryPaymentPaginatedResponse:
        """List salary payments with pagination, filtering, and sorting.
        
        Based on F6_api_spec.md Section 4.3.5 - GET /v1/company/employees/{employee_id}/salary/payments.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Gets paginated payments from repository
        - Converts to response schemas
        - Builds pagination metadata
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get payments from repository
        items, total = await self.repository.list_salary_payments(
            employee_id=employee_id,
            page=query.page,
            page_size=query.page_size,
            year=query.year,
            month=query.month,
            payment_method=query.payment_method,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        
        # Convert to response schemas
        payment_items = []
        for payment in items:
            created_by_name = await self._get_user_name(payment.created_by)
            slip_url = f"/v1/company/employees/{employee_id}/salary/payments/{payment.id}/slip" if payment.slip_url else None
            
            payment_items.append(
                SalaryPaymentListItem(
                    id=payment.id,
                    employee_id=payment.employee_id,
                    amount=payment.amount,
                    currency=payment.currency,
                    month=payment.month,
                    year=payment.year,
                    paid_on=payment.paid_on,
                    payment_method=payment.payment_method,
                    slip_url=slip_url,
                    created_at=payment.created_at,
                    created_by=created_by_name,
                )
            )
        
        # Calculate pagination metadata
        total_pages = (total + query.page_size - 1) // query.page_size if total > 0 else 0
        
        # Build query params string with all filters (preserve pagination state)
        query_params = []
        query_params.append(f"page_size={query.page_size}")
        if query.year is not None:
            query_params.append(f"year={query.year}")
        if query.month is not None:
            query_params.append(f"month={query.month}")
        if query.payment_method is not None:
            query_params.append(f"payment_method={query.payment_method}")
        query_params.append(f"sort_by={query.sort_by}")
        query_params.append(f"sort_order={query.sort_order}")
        query_params_str = "&".join(query_params)
        
        # Build next_page and prev_page URLs with all query parameters
        next_page = None
        if query.page < total_pages:
            next_page = f"/v1/company/employees/{employee_id}/salary/payments?page={query.page + 1}&{query_params_str}"
        
        prev_page = None
        if query.page > 1:
            prev_page = f"/v1/company/employees/{employee_id}/salary/payments?page={query.page - 1}&{query_params_str}"
        
        return SalaryPaymentPaginatedResponse(
            items=payment_items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            next_page=next_page,
            prev_page=prev_page,
        )

    async def get_salary_slip(
        self,
        employee_id: UUID,
        payment_id: UUID,
        company_id: Optional[UUID],
    ) -> tuple[bytes, int, int]:
        """Get salary slip PDF file.
        
        Based on F6_api_spec.md Section 4.3.6 - GET /v1/company/employees/{employee_id}/salary/payments/{payment_id}/slip.
        
        Business Logic:
        - Validates employee exists and belongs to company
        - Validates payment exists and belongs to employee
        - Validates slip exists (slip_url is not None)
        - Returns tuple of (PDF bytes, year, month) for filename generation
        
        Note: Actual PDF generation/retrieval would be implemented here.
        For now, raises exception if slip not found.
        
        Returns:
            Tuple of (pdf_bytes: bytes, year: int, month: int) for filename generation.
        """
        # Get employee
        employee = await self.repository.get_employee_by_id(employee_id, company_id)
        if not employee:
            raise EmployeeNotFound(str(employee_id))
        
        # Get payment
        payment = await self.repository.get_salary_payment_by_id(payment_id)
        if not payment or payment.employee_id != employee_id:
            from src.salaries.exceptions import SalaryPaymentNotFound
            raise SalaryPaymentNotFound(str(payment_id))
        
        # Check if slip exists
        if not payment.slip_url:
            raise SalarySlipNotFound(str(payment_id))
        
        # TODO: Implement actual PDF file retrieval from storage
        # For now, raise exception indicating slip not generated yet
        # When implemented, return: (pdf_bytes, payment.year, payment.month)
        raise SalarySlipNotFound(str(payment_id))
