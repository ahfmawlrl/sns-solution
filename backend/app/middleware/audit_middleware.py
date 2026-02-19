"""Audit logging middleware for automatic CUD operation tracking.

Records all Create, Update, Delete operations and approval/publishing actions
to the audit_logs table.
"""
import logging
import uuid as _uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.database import async_session_factory
from app.models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)

# Methods that trigger audit logging
AUDITABLE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths to skip (health checks, auth, reads)
SKIP_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
}

# Map HTTP method to action
METHOD_ACTION_MAP = {
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


def _extract_resource_info(path: str) -> tuple[str, str | None]:
    """Extract resource type and ID from API path.

    Examples:
        /api/v1/contents -> ("content", None)
        /api/v1/contents/abc-123 -> ("content", "abc-123")
        /api/v1/contents/abc-123/status -> ("content", "abc-123")
    """
    parts = path.strip("/").split("/")

    # Find the resource part (after api/v1/)
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
        resource = parts[2].rstrip("s")  # "contents" -> "content"
        resource_id = parts[3] if len(parts) > 3 else None
        # Validate if resource_id looks like a UUID
        if resource_id:
            try:
                _uuid.UUID(resource_id)
            except (ValueError, AttributeError):
                resource_id = None
        return resource, resource_id

    return "unknown", None


def _extract_user_id(request: Request) -> str | None:
    """Extract user ID from request state (set by auth dependency)."""
    # Check if user was set by auth middleware
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return str(user.id)
    return None


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that automatically logs CUD operations to audit_logs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only audit CUD operations
        if request.method not in AUDITABLE_METHODS:
            return await call_next(request)

        path = request.url.path

        # Skip non-API and excluded paths
        if not path.startswith("/api/") or path in SKIP_PATHS:
            return await call_next(request)

        # Execute the request
        response = await call_next(request)

        # Only log successful operations
        if response.status_code >= 400:
            return response

        try:
            resource_type, resource_id = _extract_resource_info(path)
            action = METHOD_ACTION_MAP.get(request.method, "unknown")
            user_id = _extract_user_id(request)

            # Determine specific action from path
            if "status" in path:
                action = "update"
            elif "approve" in path or "approval" in path:
                action = "approve"
            elif "publish" in path:
                action = "publish"
            elif "reject" in path:
                action = "reject"

            # Map action string to AuditAction enum
            action_map = {
                "create": AuditAction.CREATE,
                "update": AuditAction.UPDATE,
                "delete": AuditAction.DELETE,
                "approve": AuditAction.APPROVE,
                "reject": AuditAction.REJECT,
                "publish": AuditAction.PUBLISH,
            }
            audit_action = action_map.get(action, AuditAction.UPDATE)

            # Only write audit log if we have a user
            if not user_id:
                return response

            client_host = request.client.host if request.client else "unknown"

            async with async_session_factory() as session:
                log_entry = AuditLog(
                    user_id=_uuid.UUID(user_id),
                    action=audit_action,
                    entity_type=resource_type,
                    entity_id=_uuid.UUID(resource_id) if resource_id else None,
                    changes={
                        "method": request.method,
                        "path": path,
                        "status_code": response.status_code,
                    },
                    ip_address=client_host,
                )
                session.add(log_entry)
                await session.commit()

        except Exception as e:
            # Never let audit logging break the actual request
            logger.warning("Failed to write audit log: %s", e)

        return response
