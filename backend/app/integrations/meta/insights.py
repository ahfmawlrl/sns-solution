"""Meta insights collector — gathers analytics from Instagram/Facebook."""
import logging
from typing import Any

from app.integrations.meta.client import MetaGraphClient

logger = logging.getLogger(__name__)

# Default Instagram account metrics
IG_ACCOUNT_METRICS = [
    "impressions",
    "reach",
    "follower_count",
    "profile_views",
]

# Default Instagram media metrics
IG_MEDIA_METRICS = [
    "impressions",
    "reach",
    "engagement",
    "saved",
    "shares",
]


class MetaInsightsCollector:
    """Collect and normalize insights data from Meta platforms."""

    def __init__(self, client: MetaGraphClient):
        self.client = client

    async def collect_account_insights(
        self,
        ig_user_id: str,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """Collect account-level insights for an Instagram account.

        Returns normalized dict with metric name → value.
        """
        raw = await self.client.get_account_insights(
            ig_user_id,
            metrics=IG_ACCOUNT_METRICS,
            period="day",
            since=since,
            until=until,
        )

        metrics: dict[str, Any] = {}
        for item in raw.get("data", []):
            name = item["name"]
            values = item.get("values", [])
            if values:
                metrics[name] = values[-1].get("value", 0)

        logger.info("Collected account insights for %s: %d metrics", ig_user_id, len(metrics))
        return metrics

    async def collect_media_insights(self, media_id: str) -> dict[str, Any]:
        """Collect insights for a specific media post.

        Returns normalized dict with metric name → value.
        """
        raw = await self.client.get_media_insights(media_id)

        metrics: dict[str, Any] = {}
        for item in raw.get("data", []):
            metrics[item["name"]] = item.get("values", [{}])[0].get("value", 0)

        logger.info("Collected media insights for %s: %d metrics", media_id, len(metrics))
        return metrics

    async def collect_page_insights(self, page_id: str) -> dict[str, Any]:
        """Collect basic page info as insights (Facebook)."""
        info = await self.client.get_page_info(page_id)
        return {
            "followers": info.get("followers_count", 0),
            "fans": info.get("fan_count", 0),
        }
