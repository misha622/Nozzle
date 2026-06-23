"""Background task scheduler using ARQ."""

import logging
from datetime import datetime

from arq import cron
from arq.connections import RedisSettings

from nozzle.db.session import async_session_factory
from nozzle.services.ingestion_service import IngestionService
from nozzle.clustering.manager import ClusteringManager
from nozzle.notifications.slack import notify_new_critical_cluster

logger = logging.getLogger(__name__)


async def ingest_all_sources(ctx):
    """Periodic task: fetch alerts from all active sources."""
    async with async_session_factory() as db:
        from sqlalchemy import select
        from nozzle.domain.models import Source
        from nozzle.domain.enums import SourceStatus

        result = await db.execute(
            select(Source).where(Source.status == SourceStatus.ACTIVE)
        )
        sources = result.scalars().all()

        for source in sources:
            try:
                service = IngestionService(db)
                stats = await service.ingest_from_source(
                    source_id=str(source.id),
                    limit=1000,
                )
                logger.info(f"Ingested from {source.name}: {stats}")
            except Exception as e:
                logger.error(f"Failed to ingest from {source.name}: {e}")


async def run_clustering(ctx):
    """Periodic task: run clustering on unclustered alerts."""
    async with async_session_factory() as db:
        try:
            manager = ClusteringManager(db, strategy_name="hybrid")
            result = await manager.run(hours_back=24)

            if result["clusters_created"] > 0:
                logger.info(f"Clustering: {result}")

                from sqlalchemy import select
                from nozzle.domain.models import Cluster

                clusters_result = await db.execute(
                    select(Cluster).order_by(Cluster.created_at.desc()).limit(result["clusters_created"])
                )
                new_clusters = clusters_result.scalars().all()

                for cluster in new_clusters:
                    if cluster.alert_count >= 10:
                        await notify_new_critical_cluster(
                            cluster_name=cluster.name,
                            alert_count=cluster.alert_count,
                            description=cluster.description,
                        )
        except Exception as e:
            logger.error(f"Clustering failed: {e}")


async def startup(ctx):
    """Called on worker startup."""
    logger.info("Nozzle worker started")


async def shutdown(ctx):
    """Called on worker shutdown."""
    logger.info("Nozzle worker stopped")


class WorkerSettings:
    """ARQ worker configuration."""
    functions = [ingest_all_sources, run_clustering]
    cron_jobs = [
        cron(ingest_all_sources, minute="*/5", run_at_startup=False),
        cron(run_clustering, minute="*/15", run_at_startup=False),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(host="localhost", port=6379, database=0)
    poll_delay = 5
