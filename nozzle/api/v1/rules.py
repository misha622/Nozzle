"""API endpoints for rule statistics."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from nozzle.db.session import get_db
from nozzle.db.queries import stats as stats_queries

router = APIRouter()


@router.get("/top-noisy")
async def top_noisy_rules(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get the noisiest rules."""
    rules = await stats_queries.get_top_noisy_rules(db, limit=limit)
    return {"items": rules}
