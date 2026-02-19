"""YouTube Data API v3 client."""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.googleapis.com/youtube/v3"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubeClient:
    """Async client for YouTube Data API v3."""

    def __init__(self, access_token: str, api_key: str | None = None, timeout: float = 60.0):
        self.access_token = access_token
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=timeout,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ── Channel ──

    async def get_my_channel(self) -> dict[str, Any]:
        """Get the authenticated user's channel info."""
        resp = await self._client.get(
            "/channels",
            params={"part": "snippet,statistics,contentDetails", "mine": "true"},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_channel_stats(self, channel_id: str) -> dict[str, Any]:
        """Get channel statistics."""
        resp = await self._client.get(
            "/channels",
            params={"part": "statistics", "id": channel_id},
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        return items[0]["statistics"] if items else {}

    # ── Video Upload (simplified — not resumable) ──

    async def upload_video(
        self,
        video_bytes: bytes,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
        privacy_status: str = "public",
        category_id: str = "22",
    ) -> dict[str, Any]:
        """Upload a video to YouTube.

        For production, use resumable upload protocol.
        This simplified version uses direct upload for smaller files.
        """
        metadata = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
            },
        }

        async with httpx.AsyncClient(timeout=300.0) as upload_client:
            resp = await upload_client.post(
                UPLOAD_URL,
                params={"uploadType": "multipart", "part": "snippet,status"},
                headers={"Authorization": f"Bearer {self.access_token}"},
                files={
                    "": ("metadata", __import__("json").dumps(metadata), "application/json"),
                    "media": ("video.mp4", video_bytes, "video/*"),
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def update_video(self, video_id: str, title: str | None = None, description: str | None = None) -> dict[str, Any]:
        """Update video metadata."""
        body: dict[str, Any] = {"id": video_id, "snippet": {}}
        if title:
            body["snippet"]["title"] = title
        if description:
            body["snippet"]["description"] = description

        resp = await self._client.put("/videos", params={"part": "snippet"}, json=body)
        resp.raise_for_status()
        return resp.json()

    # ── Comments ──

    async def get_comments(
        self, video_id: str, page_token: str | None = None, max_results: int = 50
    ) -> dict[str, Any]:
        """Get comment threads for a video."""
        params: dict[str, Any] = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": max_results,
            "order": "time",
        }
        if page_token:
            params["pageToken"] = page_token

        resp = await self._client.get("/commentThreads", params=params)
        resp.raise_for_status()
        return resp.json()

    async def reply_to_comment(self, parent_id: str, text: str) -> dict[str, Any]:
        """Reply to a comment thread."""
        body = {
            "snippet": {
                "parentId": parent_id,
                "textOriginal": text,
            }
        }
        resp = await self._client.post("/comments", params={"part": "snippet"}, json=body)
        resp.raise_for_status()
        return resp.json()

    async def delete_comment(self, comment_id: str) -> None:
        """Delete a comment (must be owned by the authenticated user)."""
        resp = await self._client.delete("/comments", params={"id": comment_id})
        resp.raise_for_status()

    # ── Analytics ──

    async def get_video_stats(self, video_id: str) -> dict[str, Any]:
        """Get statistics for a specific video."""
        resp = await self._client.get(
            "/videos",
            params={"part": "statistics,snippet", "id": video_id},
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        return items[0] if items else {}

    async def list_videos(self, channel_id: str, max_results: int = 20) -> dict[str, Any]:
        """List recent videos from a channel."""
        resp = await self._client.get(
            "/search",
            params={
                "part": "snippet",
                "channelId": channel_id,
                "type": "video",
                "order": "date",
                "maxResults": max_results,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ── OAuth ──

    async def refresh_token(self, refresh_token: str, client_id: str, client_secret: str) -> dict[str, Any]:
        """Refresh OAuth access token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            resp.raise_for_status()
            return resp.json()
