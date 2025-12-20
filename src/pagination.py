"""Pagination schemas for API responses."""

from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PagedCollection(BaseModel, Generic[T]):
    """Paginated collection response schema.
    
    Based on F1A_api_spec.md pagination structure with items, total, page, 
    page_size, total_pages, next_page, and prev_page fields.
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    next_page: Optional[str] = None
    prev_page: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
