"""Analytics API - 5 endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_role
from app.models.user import User
from app.schemas.analytics import (
    ContentPerfItem,
    DashboardKPI,
    ReportRequest,
    ReportResponse,
    TrendPoint,
)
from app.schemas.common import APIResponse
from app.services import analytics_service

router = APIRouter()


# GET /analytics/dashboard
@router.get("/dashboard", response_model=APIResponse)
async def get_dashboard(
    client_id: uuid.UUID | None = None,
    platform: str | None = None,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    kpi = await analytics_service.get_dashboard_kpi(db, client_id, platform, period)
    return APIResponse(status="success", data=kpi.model_dump())


# GET /analytics/trends
@router.get("/trends", response_model=APIResponse)
async def get_trends(
    client_id: uuid.UUID | None = None,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trends = await analytics_service.get_trends(db, client_id, period)
    return APIResponse(
        status="success",
        data=[t.model_dump() for t in trends],
    )


# GET /analytics/content-perf
@router.get("/content-perf", response_model=APIResponse)
async def get_content_perf(
    client_id: uuid.UUID | None = None,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    perf = await analytics_service.get_content_performance(db, client_id, period)
    return APIResponse(
        status="success",
        data=[p.model_dump() for p in perf],
    )


# POST /analytics/report — admin, manager
@router.post("/report", response_model=APIResponse, status_code=201)
async def create_report(
    body: ReportRequest,
    _caller: User = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db),
):
    # Stub: real report generation via Celery in later steps
    import uuid as _uuid
    from datetime import datetime, timezone
    report_id = _uuid.uuid4()
    return APIResponse(
        status="success",
        data={
            "id": str(report_id),
            "client_id": str(body.client_id),
            "status": "processing",
            "summary": None,
            "generated_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        message="Report generation started",
    )


# GET /analytics/report/{id}
@router.get("/report/{report_id}", response_model=APIResponse)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Stub: reports table not yet created, return placeholder
    return APIResponse(
        status="success",
        data={
            "id": str(report_id),
            "status": "processing",
            "summary": None,
        },
    )
