"""Main API router that includes all domain routers."""

from fastapi import APIRouter
from src.config import settings
from src.auth.router import router as auth_router
from src.users.router import router as users_router
from src.notifications.router import router as notifications_router
from src.permissions.router import router as permissions_router
from src.companies.router import router as companies_router, profile_router as company_profile_router
from src.employees.router import router as employees_router, delete_router as employees_delete_router
from src.salaries.router import router as salaries_router, salary_payments_router
from src.projects.router import router as projects_router
from src.tasks.router import router as tasks_router
from src.leaves.router import router as leaves_router
from src.attendance.router import router as attendance_router, company_router as attendance_company_router

# Create main API router
api_router = APIRouter(prefix=settings.api_prefix)

# Register domain routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(notifications_router)
api_router.include_router(permissions_router)
api_router.include_router(companies_router)
api_router.include_router(company_profile_router)
api_router.include_router(employees_router)
api_router.include_router(employees_delete_router)
api_router.include_router(salaries_router)
api_router.include_router(salary_payments_router)
api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(leaves_router)
api_router.include_router(attendance_router)
api_router.include_router(attendance_company_router)

# TODO: Register other domain routers when implemented:
# from src.users.router import router as users_router
# from src.companies.router import router as companies_router
# from src.employees.router import router as employees_router
# from src.projects.router import router as projects_router
# from src.tasks.router import router as tasks_router
# from src.attendance.router import router as attendance_router
# from src.leaves.router import router as leaves_router
# from src.salaries.router import router as salaries_router
# from src.permissions.router import router as permissions_router
# from src.notifications.router import router as notifications_router
# from src.audits.router import router as audits_router
# from src.dashboards.router import router as dashboards_router
#
# api_router.include_router(users_router)
# api_router.include_router(companies_router)
# api_router.include_router(employees_router)
# api_router.include_router(projects_router)
# api_router.include_router(tasks_router)
# api_router.include_router(attendance_router)
# api_router.include_router(leaves_router)
# api_router.include_router(salaries_router)
# api_router.include_router(permissions_router)
# api_router.include_router(notifications_router)
# api_router.include_router(audits_router)
# api_router.include_router(dashboards_router)
