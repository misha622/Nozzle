"""Service for fetching and storing alerts from sources."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nozzle.domain.models import Source, Alert
from nozzle.domain.enums import SourceStatus
from nozzle.ingestion.normalizer import AlertNormalizer
from nozzle.ingestion.registry import get_adapter

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates fetching alerts from sources and storing them."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.normalizer = AlertNormalizer()

    async def ingest_from_source(
        self,
        source_id: str,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> dict:
        """Fetch alerts from a source, normalize, and store them."""
        result = await self.db.execute(
            select(Source).where(Source.id == str(source_id))
        )
        source = result.scalar_one_or_none()
        if source is None:
            raise ValueError(f"Source not found: {source_id}")

        adapter = get_adapter(
            source_type=source.type,
            source_id=str(source.id),
            config=source.config,
        )

        stats = {"fetched": 0, "stored": 0, "duplicates": 0, "errors": 0}

        try:
            connected = await adapter.connect()
            if not connected:
                source.status = SourceStatus.ERROR
                await self.db.commit()
                return {**stats, "error": "Failed to connect"}

            source.status = SourceStatus.ACTIVE
            source.last_polled_at = datetime.utcnow()

            async for raw_alert in adapter.fetch_alerts(since=since, limit=limit):
                stats["fetched"] += 1
                try:
                    normalized = await self.normalizer.normalize(raw_alert)
                    stored = await self._store_alert(normalized)
                    if stored:
                        stats["stored"] += 1
                    else:
                        stats["duplicates"] += 1
                except Exception as e:
                    logger.error(f"Error processing alert {raw_alert.external_id}: {e}")
                    stats["errors"] += 1

            await self.db.commit()

        except Exception as e:
            logger.error(f"Ingestion failed for source {source_id}: {e}")
            source.status = SourceStatus.ERROR
            await self.db.commit()
            stats["error"] = str(e)
        finally:
            await adapter.disconnect()

        return stats

    async def _store_alert(self, normalized) -> bool:
        """Store a normalized alert in the database. Returns True if stored, False if duplicate."""
        result = await self.db.execute(
            select(Alert).where(
                Alert.source_id == normalized.source_id,
                Alert.external_id == normalized.external_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return False

        alert = Alert(
            id=normalized.id,
            source_id=normalized.source_id,
            external_id=normalized.external_id,
            rule_id=normalized.rule_id,
            rule_name=normalized.rule_name,
            severity=normalized.severity.value,
            agent_name=normalized.agent_name,
            agent_id=normalized.agent_id,
            source_ip=str(normalized.source_ip) if normalized.source_ip else None,
            source_hostname=normalized.source_hostname,
            destination_ip=str(normalized.destination_ip) if normalized.destination_ip else None,
            description=normalized.description,
            full_log=normalized.full_log,
            raw_json=normalized.raw_json,
            status=normalized.status,
            cluster_id=normalized.cluster_id,
            received_at=normalized.received_at,
            normalized_at=normalized.normalized_at,
            extra_data=normalized.extra_data,
        )
        self.db.add(alert)
        return True
