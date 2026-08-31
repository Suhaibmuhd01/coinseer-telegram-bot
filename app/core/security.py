import hmac
import re
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.core.redis import RedisCache


def secure_compare(val_a: Optional[str], val_b: Optional[str]) -> bool:
    """Constant-time string comparison to mitigate timing attacks on secrets."""
    if val_a is None or val_b is None:
        return False
    return hmac.compare_digest(val_a.encode("utf-8"), val_b.encode("utf-8"))


def escape_markdown(text: str) -> str:
    """Escape special characters to prevent Telegram Markdown injection attacks."""
    if not text:
        return ""
    # Characters that require escaping in standard Telegram Markdown
    escape_chars = r"_*`["
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", str(text))


def sanitize_input(text: Optional[str], max_length: int = 64) -> str:
    """Strict input sanitization for user inputs to prevent injection & malformed payloads."""
    if not text:
        return ""
    # Allow alphanumeric, hyphen, underscore, dot, and spaces
    sanitized = re.sub(r"[^a-zA-Z0-9\s.\-_]", "", str(text).strip())
    return sanitized[:max_length]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces zero-trust HTTP security headers, CORS restrictions, and CSP."""

    async def dispatch(self, request: Request, call_next):
        # 1. Enforce payload size limit (max 2MB to prevent memory exhaustion DDoS)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Payload exceeds maximum permitted size (2MB)",
            )

        response = await call_next(request)

        # 2. Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content-Security-Policy (Allow Telegram WebApp SDK and TradingView embeds)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https://telegram.org https://*.telegram.org; "
            "script-src 'self' 'unsafe-inline' https://telegram.org https://cdn.jsdelivr.net https://s.tradingview.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "frame-src 'self' https://s.tradingview.com https://*.tradingview.com; "
            "connect-src 'self' https:;"
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Distributed IP & user rate limiting middleware backed by Redis."""

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        # Skip rate limit on metrics/health internal endpoints
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        # 60 requests per minute per IP
        is_limited = await RedisCache.is_rate_limited(f"ip:{client_ip}", limit=60, window_secs=60)
        if is_limited:
            logger.warning("rate_limit_exceeded_ip", ip=client_ip, path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please throttle your requests.",
            )

        return await call_next(request)
