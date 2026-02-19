"""YouTube insights collector."""
import logging
from typing import Any

from app.integrations.youtube.client import YouTubeClient

logger = logging.getLogger(__name__)


class YouTubeInsightsCollector:
    """Collect and normalize YouTube analytics data."""

    def __init__(self, client: YouTubeClient):
        self.client = client

    async def collect_channel_insights(self, channel_id: str) -> dict[str, Any]:
        """Collect channel-level statistics."""
        stats = await self.client.get_channel_stats(channel_id)
        return {
            "subscribers": int(stats.get("subscriberCount", 0)),
            "views": int(stats.get("viewCount", 0)),
            "videos": int(stats.get("videoCount", 0)),
        }

    async def collect_video_insights(self, video_id: str) -> dict[str, Any]:
        """Collect per-video statistics."""
        data = await self.client.get_video_stats(video_id)
        stats = data.get("statistics", {})
        snippet = data.get("snippet", {})
        return {
            "title": snippet.get("title", ""),
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "published_at": snippet.get("publishedAt"),
        }

    async def collect_recent_videos_insights(
        self, channel_id: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Collect insights for recent videos."""
        search_result = await self.client.list_videos(channel_id, max_results=max_results)
        results = []
        for item in search_result.get("items", []):
            video_id = item["id"]["videoId"]
            insights = await self.collect_video_insights(video_id)
            insights["video_id"] = video_id
            results.append(insights)
        return results
