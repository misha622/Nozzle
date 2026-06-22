"""API endpoints for alerts."""

from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from nozzle.db.session import get_db
from nozzle.domain.models import Alert
from nozzle.domain.schemas import AlertResponse, AlertListResponse
from nozzle.services.ingestion_service import IngestionService

router = APIRouter()


class IngestRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=5000)


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str | None = None,
    source_id: UUID | None = None,
    rule_id: str | None = None,
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
):
    """List alerts with optional filters."""
    query = select(Alert).options(selectinload(Alert.source))
    since = datetime.utcnow() - timedelta(hours=hours)
    query = query.where(Alert.received_at >= since)
    if status:
        query = query.where(Alert.status == status)
    if source_id:
        query = query.where(Alert.source_id == source_id)
    if rule_id:
        query = query.where(Alert.rule_id == rule_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Alert.received_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            AlertResponse(
                id=a.id,
                external_id=a.external_id,
                source_type=a.source.type if a.source else "unknown",
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


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific alert by ID."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    return AlertResponse(
        id=alert.id,
        external_id=alert.external_id,
        source_type=alert.source.type if alert.source else "unknown",
        rule_id=alert.rule_id,
        rule_name=alert.rule_name,
        severity=alert.severity,
        agent_name=alert.agent_name,
        source_ip=alert.source_ip,
        description=alert.description,
        status=alert.status,
        cluster_id=alert.cluster_id,
        received_at=alert.received_at,
    )


@router.post("/ingest/{source_id}", response_model=dict)
async def ingest_alerts(
    source_id: UUID,
    body: IngestRequest = IngestRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Trigger alert ingestion from a specific source."""
    service = IngestionService(db)
    stats = await service.ingest_from_source(
        source_id=str(source_id),
        limit=body.limit,
    )
    return stats
