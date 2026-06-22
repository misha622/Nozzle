"""API endpoints for clusters."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from nozzle.db.session import get_db
from nozzle.clustering.manager import ClusteringManager
from nozzle.domain.models import Cluster
from nozzle.domain.schemas import ClusterResponse, ClusterDetailResponse

router = APIRouter()


@router.post("/run", response_model=dict)
async def run_clustering(
    source_id: UUID | None = None,
    hours_back: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Run clustering on unclustered alerts."""
    manager = ClusteringManager(db)
    result = await manager.run(source_id=source_id, hours_back=hours_back)
    return result


@router.get("/", response_model=list[ClusterResponse])
async def list_clusters(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List clusters."""
    from sqlalchemy import select

    query = select(Cluster).order_by(Cluster.created_at.desc()).limit(limit)
    if status:
        query = query.where(Cluster.status == status)

    result = await db.execute(query)
    clusters = result.scalars().all()

    return [
        ClusterResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            strategy=c.strategy,
            confidence=c.confidence,
            alert_count=c.alert_count,
            status=c.status,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in clusters
    ]


@router.get("/{cluster_id}", response_model=ClusterDetailResponse)
async def get_cluster(
    cluster_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get cluster details with alerts."""
    from fastapi import HTTPException
    from sqlalchemy import select
    from nozzle.domain.models import Alert
    from nozzle.domain.schemas import AlertResponse

    result = await db.execute(
        select(Cluster).where(Cluster.id == str(cluster_id))
    )
    cluster = result.scalar_one_or_none()
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Fetch alerts in this cluster
    alerts_result = await db.execute(
        select(Alert).where(Alert.cluster_id == str(cluster_id))
    )
    alerts = alerts_result.scalars().all()

    return ClusterDetailResponse(
        id=cluster.id,
        name=cluster.name,
        description=cluster.description,
        strategy=cluster.strategy,
        confidence=cluster.confidence,
        alert_count=cluster.alert_count,
        status=cluster.status,
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
        alerts=[
            AlertResponse(
                id=a.id,
                external_id=a.external_id,
                source_type="wazuh",
                rule_id=a.rule_id,
                rule_name=a.rule_name,
                severity=a.severity,
                agent_name=a.agent_name,
                source_ip=a.source_ip,
                description=a.description,
                status=a.status,
                cluster_id=a.cluster_id,
                received_at=a.received_at,
            )
            for a in alerts
        ],
    )
