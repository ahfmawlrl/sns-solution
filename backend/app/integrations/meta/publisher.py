"""Meta platform publisher — dispatches content to Instagram/Facebook."""
import logging
from typing import Any

from app.integrations.meta.client import MetaGraphClient

logger = logging.getLogger(__name__)


class MetaPublisher:
    """High-level publisher that routes content to the correct Meta API method."""

    def __init__(self, client: MetaGraphClient):
        self.client = client

    async def publish(
        self,
        platform: str,
        account_id: str,
        content_type: str,
        caption: str,
        media_url: str | None = None,
        link: str | None = None,
    ) -> dict[str, Any]:
        """Publish content to Instagram or Facebook.

        Args:
            platform: "instagram" or "facebook"
            account_id: IG user ID or FB page ID
            content_type: "feed", "reel", "story", "card_news"
            caption: Post caption/message
            media_url: URL of media to publish (image/video)
            link: URL to attach (Facebook only)

        Returns:
            Platform API response with post ID
        """
        if platform == "instagram":
            return await self._publish_instagram(account_id, content_type, caption, media_url)
        elif platform == "facebook":
            return await self._publish_facebook(account_id, content_type, caption, media_url, link)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    async def _publish_instagram(
        self, ig_user_id: str, content_type: str, caption: str, media_url: str | None
    ) -> dict[str, Any]:
        if content_type == "story":
            if not media_url:
                raise ValueError("Story requires media_url")
            is_video = media_url.lower().endswith((".mp4", ".mov"))
            return await self.client.publish_story(ig_user_id, media_url, is_video=is_video)

        if content_type == "reel":
            if not media_url:
                raise ValueError("Reel requires video media_url")
            return await self.client.publish_reel(ig_user_id, media_url, caption)

        # feed, card_news → photo post
        if not media_url:
            raise ValueError("Feed/card_news requires image media_url")
        return await self.client.publish_photo(ig_user_id, media_url, caption)

    async def _publish_facebook(
        self,
        page_id: str,
        content_type: str,
        message: str,
        media_url: str | None,
        link: str | None,
    ) -> dict[str, Any]:
        # Facebook posts are simpler — just message + optional link
        return await self.client.publish_facebook_post(page_id, message, link)
