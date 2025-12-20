"""Standard response schemas for API responses."""

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Error detail for field-level validation errors."""

    field: str = Field(..., description="Field name with error")
    issue: str = Field(..., description="Error description")


class ErrorInfo(BaseModel):
    """Error information structure."""

    code: str = Field(..., description="Error code in UPPER_SNAKE_CASE")
    details: list[ErrorDetail] = Field(default_factory=list, description="Field-level error details")


class StandardResponse(BaseModel, Generic[T]):
    """Standard API response wrapper with data and message."""

    data: T = Field(..., description="Response data payload")
    message: str = Field(..., description="Human-friendly success message")

    model_config = {"json_schema_extra": {"examples": [{"data": {}, "message": "Operation completed successfully"}]}}

