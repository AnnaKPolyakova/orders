from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Request


class PaginationService:
    """Service for pagination operations"""

    def build_paginated_response(
        self,
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
        request: Request,
    ) -> dict[str, Any]:
        """Build paginated response with prev/next page URLs"""
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        # Build base URL - use request.url without query params
        base_url = str(request.url).split("?")[0]

        # Calculate previous and next page URLs
        prev_page = None
        next_page = None

        if page > 1:
            prev_page = f"{base_url}?page={page - 1}&page_size={page_size}"

        if page < total_pages:
            next_page = f"{base_url}?page={page + 1}&page_size={page_size}"

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "prev_page": prev_page,
            "next_page": next_page,
        }


async def get_pagination_service() -> AsyncGenerator[PaginationService]:
    """Dependency for getting PaginationService instance"""
    yield PaginationService()
