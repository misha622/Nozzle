"""Aggregation queries for dashboard stats."""

from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from nozzle.domain.models import Alert, Cluster, RuleStats


async def get_total_alerts_24h(db: AsyncSession) -> int:
    """Count alerts in last 24 hours."""
    since = datetime.utcnow() - timedelta(hours=24)
    result = await db.execute(
        select(func.count()).select_from(
            select(Alert).where(Alert.received_at >= since).subquery()
        )
    )
    return result.scalar() or 0


async def get_total_clusters(db: AsyncSession) -> int:
    """Count total clusters."""
    result = await db.execute(
        select(func.count()).select_from(select(Cluster).subquery())
    )
    return result.scalar() or 0


async def get_alerts_clustered(db: AsyncSession) -> int:
    """Count alerts that are currently clustered."""
    result = await db.execute(
        select(func.count()).select_from(
            select(Alert).where(Alert.cluster_id.isnot(None)).subquery()
        )
    )
    return result.scalar() or 0


async def get_top_noisy_rules(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Get rules with highest noise score."""
    result = await db.execute(
        select(RuleStats)
        .order_by(RuleStats.noise_score.desc())
        .limit(limit)
    )
    rules = result.scalars().all()
    return [
        {
            "rule_id": r.external_rule_id,
            "rule_name": r.rule_name or f"Rule {r.external_rule_id}",
            "noise_score": round(r.noise_score, 2),
            "times_clustered": r.times_clustered,
            "times_escalated": r.times_escalated,
        }
        for r in rules
    ]


async def get_noise_reduction_pct(db: AsyncSession) -> float:
    """Calculate noise reduction percentage."""
    total = await get_total_alerts_24h(db)
    if total == 0:
        return 0.0
    clustered = await get_alerts_clustered(db)
    return round(clustered / total * 100, 1)
