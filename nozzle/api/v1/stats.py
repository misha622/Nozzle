"""API endpoints for dashboard statistics."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from nozzle.db.session import get_db
from nozzle.db.queries import stats as stats_queries

router = APIRouter()


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    """Get all dashboard stats."""
    total_alerts = await stats_queries.get_total_alerts_24h(db)
    total_clusters = await stats_queries.get_total_clusters(db)
    clustered = await stats_queries.get_alerts_clustered(db)
    noise_pct = await stats_queries.get_noise_reduction_pct(db)
    top_noisy = await stats_queries.get_top_noisy_rules(db)

    return {
        "total_alerts_24h": total_alerts,
        "total_clusters_24h": total_clusters,
        "alerts_clustered": clustered,
        "alerts_saved_pct": noise_pct,
        "top_noisy_rules": top_noisy,
        "false_positive_rate": 0.0,
        "avg_cluster_confidence": 0.0,
        "incidents_missed": 0,
    }
