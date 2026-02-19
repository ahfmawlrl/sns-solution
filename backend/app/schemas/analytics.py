"""Analytics request/response schemas."""
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class DashboardQuery(BaseModel):
    client_id: uuid.UUID | None = None
    platform: str | None = None
    period: Literal["7d", "30d", "90d"] = "30d"


class MetricWithChange(BaseModel):
    value: float
    change_percent: float = 0.0
    trend: Literal["up", "down", "flat"] = "flat"


class ContentSummary(BaseModel):
    id: uuid.UUID
    title: str
    engagement_rate: float = 0.0


class DashboardKPI(BaseModel):
    reach: MetricWithChange
    engagement_rate: MetricWithChange
    follower_change: MetricWithChange
    video_views: MetricWithChange
    top_content: list[ContentSummary] = []
    worst_content: list[ContentSummary] = []


class TrendPoint(BaseModel):
    date: date
    reach: int = 0
    engagement: int = 0
    followers: int = 0


class ContentPerfItem(BaseModel):
    content_type: str
    count: int = 0
    avg_engagement_rate: float = 0.0
    total_reach: int = 0


class ReportRequest(BaseModel):
    client_id: uuid.UUID
    period: Literal["7d", "30d", "90d"] = "30d"
    platform: str | None = None


class ReportResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    status: str
    summary: str | None = None
    generated_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsSnapshotResponse(BaseModel):
    id: uuid.UUID
    platform_account_id: uuid.UUID
    snapshot_date: date
    metrics: dict
    content_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
