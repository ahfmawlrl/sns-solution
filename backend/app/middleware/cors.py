"""CORS middleware and cookie security configuration."""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import settings


def setup_cors(app: FastAPI) -> None:
    """Register CORS middleware with allowed origins from settings."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


class CookieSecurityMiddleware(BaseHTTPMiddleware):
    """Ensure all Set-Cookie headers include SameSite=Strict and Secure flags.

    The application uses Bearer JWT tokens (not cookie-based auth), so CSRF
    is not a practical risk. This middleware is an additional defence-in-depth
    measure: if any part of the stack ever sets a cookie, it will carry safe
    defaults.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Patch any Set-Cookie headers emitted by downstream handlers
        raw_cookies = response.headers.getlist("set-cookie") if hasattr(response.headers, "getlist") else []
        if raw_cookies:
            # Rebuild cookies with security attributes
            patched: list[str] = []
            for cookie in raw_cookies:
                if "SameSite" not in cookie:
                    cookie += "; SameSite=Strict"
                if "Secure" not in cookie:
                    cookie += "; Secure"
                if "HttpOnly" not in cookie:
                    cookie += "; HttpOnly"
                patched.append(cookie)

            # Remove old Set-Cookie headers and apply patched ones
            if patched:
                # MutableHeaders doesn't support deleting repeated headers easily,
                # so we rebuild via raw scope.
                new_headers = [
                    (k, v)
                    for k, v in response.raw_headers
                    if k.lower() != b"set-cookie"
                ]
                for p in patched:
                    new_headers.append((b"set-cookie", p.encode("latin-1")))
                response.raw_headers = new_headers  # type: ignore[attr-defined]

        return response


def setup_cookie_security(app: FastAPI) -> None:
    """Register the cookie security middleware."""
    app.add_middleware(CookieSecurityMiddleware)
