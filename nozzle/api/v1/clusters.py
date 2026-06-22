"""API endpoints for clusters and feedback."""

from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from nozzle.db.session import get_db
from nozzle.clustering.manager import ClusteringManager
from nozzle.domain.models import Cluster, Alert, Feedback
from nozzle.domain.enums import AlertStatus, ClusterStatus, Decision, FeedbackSource
from nozzle.domain.schemas import (
    ClusterResponse,
    ClusterDetailResponse,
    AlertResponse,
    FeedbackRequest,
    FeedbackResponse,
)

router = APIRouter()


@router.post("/run", response_model=dict)
async def run_clustering(
    source_id: UUID | None = None,
    hours_back: int = Query(24, ge=1, le=168),
    strategy: str = Query("rule_based"),
    db: AsyncSession = Depends(get_db),
):
    """Run clustering on unclustered alerts."""
    manager = ClusteringManager(db, strategy_name=strategy)
    result = await manager.run(source_id=source_id, hours_back=hours_back)
    return result


@router.get("/", response_model=list[ClusterResponse])
async def list_clusters(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List clusters."""
    query = select(Cluster).order_by(Cluster.created_at.desc()).limit(limit)
    if status:
        query = query.where(Cluster.status == status)
    result = await db.execute(query)
    clusters = result.scalars().all()
    return [
        ClusterResponse(
            id=c.id, name=c.name, description=c.description,
            strategy=c.strategy, confidence=c.confidence,
            alert_count=c.alert_count, status=c.status,
            created_at=c.created_at, updated_at=c.updated_at,
        ) for c in clusters
    ]


@router.get("/{cluster_id}", response_model=ClusterDetailResponse)
async def get_cluster(cluster_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get cluster details with alerts."""
    result = await db.execute(select(Cluster).where(Cluster.id == str(cluster_id)))
    cluster = result.scalar_one_or_none()
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    alerts_result = await db.execute(select(Alert).where(Alert.cluster_id == str(cluster_id)))
    alerts = alerts_result.scalars().all()
    return ClusterDetailResponse(
        id=cluster.id, name=cluster.name, description=cluster.description,
        strategy=cluster.strategy, confidence=cluster.confidence,
        alert_count=cluster.alert_count, status=cluster.status,
        created_at=cluster.created_at, updated_at=cluster.updated_at,
        alerts=[AlertResponse(
            id=a.id, external_id=a.external_id,
            source_type=a.source.type.value if a.source else "unknown",
            rule_id=a.rule_id, rule_name=a.rule_name, severity=a.severity,
            agent_name=a.agent_name, source_ip=a.source_ip,
            description=a.description, status=a.status,
            cluster_id=a.cluster_id, received_at=a.received_at,
        ) for a in alerts],
    )


@router.post("/{cluster_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    cluster_id: UUID,
    payload: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback on a cluster."""
    result = await db.execute(select(Cluster).where(Cluster.id == str(cluster_id)))
    cluster = result.scalar_one_or_none()
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    feedback = Feedback(
        id=str(uuid4()), cluster_id=str(cluster_id), alert_id=None,
        user_id="00000000-0000-0000-0000-000000000000",
        decision=payload.decision, source=FeedbackSource.EXPLICIT,
        comment=payload.comment, created_at=datetime.utcnow(), extra_data={},
    )
    db.add(feedback)

    if payload.decision == Decision.CONFIRMED_NOISE:
        cluster.status = ClusterStatus.DISMISSED
    else:
        cluster.status = ClusterStatus.ESCALATED

    new_status = AlertStatus.DISMISSED if payload.decision == Decision.CONFIRMED_NOISE else AlertStatus.ESCALATED
    await db.execute(
        update(Alert).where(Alert.cluster_id == str(cluster_id)).values(status=new_status)
    )

    from nozzle.domain.models import RuleStats
    alerts_result = await db.execute(select(Alert).where(Alert.cluster_id == str(cluster_id)))
    for alert in alerts_result.scalars().all():
        stats_result = await db.execute(
            select(RuleStats).where(
                RuleStats.source_id == alert.source_id,
                RuleStats.external_rule_id == alert.rule_id,
            )
        )
        stats = stats_result.scalar_one_or_none()
        if stats:
            if payload.decision == Decision.CONFIRMED_NOISE:
                stats.noise_score = min(1.0, stats.noise_score + 0.1)
            else:
                stats.noise_score = max(0.0, stats.noise_score - 0.2)
                stats.times_escalated += 1
            stats.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(feedback)
    return FeedbackResponse(
        id=feedback.id, alert_id=feedback.alert_id, cluster_id=feedback.cluster_id,
        decision=feedback.decision, source=feedback.source, created_at=feedback.created_at,
    )
