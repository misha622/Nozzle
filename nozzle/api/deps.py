"""FastAPI dependencies."""

from sqlalchemy.ext.asyncio import AsyncSession

from nozzle.db.session import get_db

__all__ = ["get_db"]
