"""API endpoints for managing alert sources."""

from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nozzle.db.session import get_db
from nozzle.domain.models import Source
from nozzle.domain.enums import SourceType, SourceStatus
from nozzle.domain.schemas import SourceConfig, SourceResponse
from nozzle.ingestion.registry import get_adapter

router = APIRouter()


@router.get("/", response_model=list[SourceResponse])
async def list_sources(db: AsyncSession = Depends(get_db)):
    """List all configured sources."""
    result = await db.execute(select(Source).order_by(Source.created_at.desc()))
    sources = result.scalars().all()
    return [
        SourceResponse(
            id=s.id,
            name=s.name,
            type=s.type,
            status=s.status,
            last_polled_at=s.last_polled_at,
            created_at=s.created_at,
        )
        for s in sources
    ]


@router.post("/", response_model=SourceResponse, status_code=201)
async def create_source(
    payload: SourceConfig,
    db: AsyncSession = Depends(get_db),
):
    """Create a new alert source and test the connection."""
    # Validate source type
    if payload.type not in SourceType:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source type: {payload.type}. Supported: {[t.value for t in SourceType]}",
        )

    # Create source record
    source = Source(
        id=uuid4(),
        name=payload.name,
        type=payload.type,
        config=payload.config,
        status=SourceStatus.DISABLED,
        created_at=datetime.utcnow(),
    )
    db.add(source)
    await db.flush()

    # Test connection
    try:
        adapter = get_adapter(
            source_type=payload.type,
            source_id=str(source.id),
            config=payload.config,
        )
        connected = await adapter.connect()
        if connected:
            source.status = SourceStatus.ACTIVE
        else:
            source.status = SourceStatus.ERROR
        await adapter.disconnect()
    except Exception as e:
        source.status = SourceStatus.ERROR

    await db.commit()
    await db.refresh(source)

    return SourceResponse(
        id=source.id,
        name=source.name,
        type=source.type,
        status=source.status,
        last_polled_at=source.last_polled_at,
        created_at=source.created_at,
    )


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific source by ID."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    return SourceResponse(
        id=source.id,
        name=source.name,
        type=source.type,
        status=source.status,
        last_polled_at=source.last_polled_at,
        created_at=source.created_at,
    )


@router.post("/{source_id}/test", response_model=dict)
async def test_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Test connection to a specific source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        adapter = get_adapter(
            source_type=source.type,
            source_id=str(source.id),
            config=source.config,
        )
        is_healthy = await adapter.health_check()
        await adapter.connect()
        await adapter.disconnect()
        return {
            "source_id": str(source.id),
            "status": "healthy" if is_healthy else "unhealthy",
            "connected": True,
        }
    except Exception as e:
        return {
            "source_id": str(source.id),
            "status": "error",
            "connected": False,
            "error": str(e),
        }


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a source configuration."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    await db.delete(source)
    await db.commit()
