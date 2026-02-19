"""Analytics business logic."""
import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsSnapshot
from app.models.content import Content, ContentType
from app.schemas.analytics import (
    ContentPerfItem,
    ContentSummary,
    DashboardKPI,
    MetricWithChange,
    TrendPoint,
)


def _period_days(period: str) -> int:
    return {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)


async def get_dashboard_kpi(
    db: AsyncSession,
    client_id: uuid.UUID | None = None,
    platform: str | None = None,
    period: str = "30d",
) -> DashboardKPI:
    """Return KPI summary. Stub values until real data collection (STEP 14+)."""
    return DashboardKPI(
        reach=MetricWithChange(value=0, change_percent=0, trend="flat"),
        engagement_rate=MetricWithChange(value=0, change_percent=0, trend="flat"),
        follower_change=MetricWithChange(value=0, change_percent=0, trend="flat"),
        video_views=MetricWithChange(value=0, change_percent=0, trend="flat"),
        top_content=[],
        worst_content=[],
    )


async def get_trends(
    db: AsyncSession,
    client_id: uuid.UUID | None = None,
    period: str = "30d",
) -> list[TrendPoint]:
    """Return daily trend data. Stub until real collection."""
    days = _period_days(period)
    today = date.today()
    return [
        TrendPoint(date=today - timedelta(days=i))
        for i in range(days - 1, -1, -1)
    ]


async def get_content_performance(
    db: AsyncSession,
    client_id: uuid.UUID | None = None,
    period: str = "30d",
) -> list[ContentPerfItem]:
    """Return performance by content type."""
    results = []
    for ct in ContentType:
        query = select(func.count()).select_from(Content).where(Content.content_type == ct)
        if client_id:
            query = query.where(Content.client_id == client_id)
        count = (await db.execute(query)).scalar() or 0
        results.append(ContentPerfItem(
            content_type=ct.value,
            count=count,
            avg_engagement_rate=0.0,
            total_reach=0,
        ))
    return results
