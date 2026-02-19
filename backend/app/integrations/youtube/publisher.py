"""YouTube publisher — handles video/shorts upload."""
import logging
from typing import Any

from app.integrations.youtube.client import YouTubeClient

logger = logging.getLogger(__name__)


class YouTubePublisher:
    """High-level publisher for YouTube content."""

    def __init__(self, client: YouTubeClient):
        self.client = client

    async def publish(
        self,
        content_type: str,
        title: str,
        description: str = "",
        video_bytes: bytes | None = None,
        tags: list[str] | None = None,
        privacy_status: str = "public",
    ) -> dict[str, Any]:
        """Publish content to YouTube.

        Args:
            content_type: "short" for Shorts, otherwise regular video
            title: Video title
            description: Video description
            video_bytes: Raw video file bytes
            tags: List of tags
            privacy_status: "public", "private", or "unlisted"

        Returns:
            API response with video ID
        """
        if not video_bytes:
            raise ValueError("YouTube publishing requires video_bytes")

        if content_type == "short":
            # Shorts are regular videos with #Shorts in title/description
            if "#Shorts" not in title:
                title = f"{title} #Shorts"

        result = await self.client.upload_video(
            video_bytes=video_bytes,
            title=title,
            description=description,
            tags=tags,
            privacy_status=privacy_status,
        )

        video_id = result.get("id")
        logger.info("Published YouTube %s: %s", content_type, video_id)
        return result
