"""Meta Graph API v19 client for Instagram and Facebook."""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://graph.facebook.com/v19.0"


class MetaGraphClient:
    """Async client for Meta Graph API (Instagram + Facebook).

    All methods expect a decrypted access_token.
    """

    def __init__(self, access_token: str, timeout: float = 30.0):
        self.access_token = access_token
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=timeout,
            params={"access_token": access_token},
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ── Account Info ──

    async def get_me(self) -> dict[str, Any]:
        """Get basic info about the authenticated user/page."""
        resp = await self._client.get("/me", params={"fields": "id,name,username"})
        resp.raise_for_status()
        return resp.json()

    async def get_page_info(self, page_id: str) -> dict[str, Any]:
        """Get page details."""
        resp = await self._client.get(f"/{page_id}", params={"fields": "id,name,fan_count,followers_count"})
        resp.raise_for_status()
        return resp.json()

    async def get_instagram_account(self, page_id: str) -> dict[str, Any]:
        """Get the Instagram Business Account linked to a Facebook Page."""
        resp = await self._client.get(
            f"/{page_id}",
            params={"fields": "instagram_business_account{id,username,followers_count,media_count}"},
        )
        resp.raise_for_status()
        return resp.json()

    # ── Publishing ──

    async def publish_photo(self, ig_user_id: str, image_url: str, caption: str = "") -> dict[str, Any]:
        """Publish a photo to Instagram (2-step: create container → publish).

        Step 1: Create media container
        Step 2: Publish container
        """
        # Step 1
        container_resp = await self._client.post(
            f"/{ig_user_id}/media",
            data={"image_url": image_url, "caption": caption},
        )
        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        # Step 2
        publish_resp = await self._client.post(
            f"/{ig_user_id}/media_publish",
            data={"creation_id": container_id},
        )
        publish_resp.raise_for_status()
        return publish_resp.json()

    async def publish_reel(self, ig_user_id: str, video_url: str, caption: str = "") -> dict[str, Any]:
        """Publish a reel to Instagram."""
        container_resp = await self._client.post(
            f"/{ig_user_id}/media",
            data={
                "video_url": video_url,
                "caption": caption,
                "media_type": "REELS",
            },
        )
        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        publish_resp = await self._client.post(
            f"/{ig_user_id}/media_publish",
            data={"creation_id": container_id},
        )
        publish_resp.raise_for_status()
        return publish_resp.json()

    async def publish_story(self, ig_user_id: str, media_url: str, is_video: bool = False) -> dict[str, Any]:
        """Publish a story to Instagram."""
        data: dict[str, str] = {"media_type": "STORIES"}
        if is_video:
            data["video_url"] = media_url
        else:
            data["image_url"] = media_url

        container_resp = await self._client.post(f"/{ig_user_id}/media", data=data)
        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        publish_resp = await self._client.post(
            f"/{ig_user_id}/media_publish",
            data={"creation_id": container_id},
        )
        publish_resp.raise_for_status()
        return publish_resp.json()

    async def publish_facebook_post(self, page_id: str, message: str, link: str | None = None) -> dict[str, Any]:
        """Publish a post to a Facebook Page."""
        data: dict[str, str] = {"message": message}
        if link:
            data["link"] = link
        resp = await self._client.post(f"/{page_id}/feed", data=data)
        resp.raise_for_status()
        return resp.json()

    # ── Comments ──

    async def get_comments(
        self, media_id: str, after: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        """Get comments on a media object."""
        params: dict[str, Any] = {
            "fields": "id,text,username,timestamp,like_count,replies{id,text,username,timestamp}",
            "limit": limit,
        }
        if after:
            params["after"] = after
        resp = await self._client.get(f"/{media_id}/comments", params=params)
        resp.raise_for_status()
        return resp.json()

    async def reply_to_comment(self, comment_id: str, message: str) -> dict[str, Any]:
        """Reply to a comment."""
        resp = await self._client.post(
            f"/{comment_id}/replies",
            data={"message": message},
        )
        resp.raise_for_status()
        return resp.json()

    async def hide_comment(self, comment_id: str, hide: bool = True) -> dict[str, Any]:
        """Hide or unhide a comment."""
        resp = await self._client.post(f"/{comment_id}", data={"hide": str(hide).lower()})
        resp.raise_for_status()
        return resp.json()

    # ── Insights ──

    async def get_media_insights(self, media_id: str) -> dict[str, Any]:
        """Get insights for a specific media."""
        resp = await self._client.get(
            f"/{media_id}/insights",
            params={"metric": "impressions,reach,engagement,saved,shares"},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_account_insights(
        self, ig_user_id: str, metrics: list[str], period: str = "day", since: str | None = None, until: str | None = None
    ) -> dict[str, Any]:
        """Get account-level insights."""
        params: dict[str, Any] = {
            "metric": ",".join(metrics),
            "period": period,
        }
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        resp = await self._client.get(f"/{ig_user_id}/insights", params=params)
        resp.raise_for_status()
        return resp.json()

    # ── OAuth ──

    async def exchange_short_lived_token(self, short_token: str, app_id: str, app_secret: str) -> dict[str, Any]:
        """Exchange short-lived token for long-lived token."""
        resp = await self._client.get(
            "/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def refresh_long_lived_token(self, app_id: str, app_secret: str) -> dict[str, Any]:
        """Refresh a long-lived token (valid for 60 days)."""
        resp = await self._client.get(
            "/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": self.access_token,
            },
        )
        resp.raise_for_status()
        return resp.json()
