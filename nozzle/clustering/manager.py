"""Clustering manager — orchestrates multiple strategies."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from nozzle.domain.models import Alert, Cluster
from nozzle.domain.enums import AlertStatus, ClusterStatus
from nozzle.domain.schemas import NormalizedAlert, ClusterCandidate
from nozzle.clustering.registry import get_strategy

logger = logging.getLogger(__name__)


class ClusteringManager:
    """Runs clustering strategies on unclustered alerts."""

    def __init__(
        self,
        db: AsyncSession,
        strategy_name: str = "rule_based",
        window_minutes: int = 5,
        min_alerts: int = 3,
    ):
        self.db = db
        self.strategy = get_strategy(
            strategy_name,
            window_minutes=window_minutes,
            min_alerts=min_alerts,
        )

    async def run(
        self, source_id: UUID | None = None, hours_back: int = 24
    ) -> dict:
        """Run clustering on unclustered alerts and persist results."""
        # Fetch unclustered alerts
        query = select(Alert).options(selectinload(Alert.source)).where(
            Alert.status == AlertStatus.NEW,
            Alert.cluster_id.is_(None),
            Alert.received_at >= datetime.utcnow() - timedelta(hours=hours_back),
        )
        if source_id:
            query = query.where(Alert.source_id == str(source_id))

        result = await self.db.execute(query)
        alert_models = result.scalars().all()

        if not alert_models:
            return {"clusters_created": 0, "alerts_clustered": 0}

        # Convert to NormalizedAlert
        normalized_alerts = [
            NormalizedAlert(
                id=UUID(a.id),
                external_id=a.external_id,
                source_type=a.source.type if a.source else "wazuh",
                source_id=UUID(a.source_id),
                rule_id=a.rule_id,
                rule_name=a.rule_name,
                severity=a.severity if a.severity in (0,3,5,8,12,15) else 0,
                agent_name=a.agent_name,
                agent_id=a.agent_id,
                source_ip=a.source_ip,
                source_hostname=a.source_hostname,
                destination_ip=a.destination_ip,
                description=a.description,
                full_log=a.full_log,
                raw_json=a.raw_json,
                status=a.status,
                cluster_id=None,
                received_at=a.received_at,
                normalized_at=a.normalized_at,
                extra_data=a.extra_data,
            )
            for a in alert_models
        ]

        # Run strategy
        candidates = await self.strategy.cluster(normalized_alerts)

        # Persist clusters
        alert_id_map = {str(a.id): a for a in alert_models}
        clusters_created = 0
        alerts_clustered = 0

        for candidate in candidates:
            cluster = Cluster(
                id=str(candidate.id),
                name=candidate.name,
                description=candidate.description,
                strategy=self.strategy.name,
                confidence=candidate.confidence,
                alert_count=candidate.alert_count,
                status=ClusterStatus.OPEN,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                extra_data={},
            )
            self.db.add(cluster)

            # Update alerts to point to this cluster
            alert_ids_to_update = [
                str(aid) for aid in candidate.alert_ids
            ]
            await self.db.execute(
                update(Alert)
                .where(Alert.id.in_(alert_ids_to_update))
                .values(
                    cluster_id=str(candidate.id),
                    status=AlertStatus.CLUSTERED,
                )
            )

            clusters_created += 1
            alerts_clustered += candidate.alert_count

        await self.db.commit()

        return {
            "clusters_created": clusters_created,
            "alerts_clustered": alerts_clustered,
            "alerts_remaining": len(alert_models) - alerts_clustered,
        }
