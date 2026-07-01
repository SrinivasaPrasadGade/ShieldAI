"""
Production middleware stack for ShieldAI backend.

Provides: request ID injection, request logging, rate limiting,
and global exception handling.
"""

import time
import uuid
import random
import asyncio
from typing import Callable

from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from logging_config import get_logger, request_id_ctx

logger = get_logger("shield_ai.middleware")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Generates a UUID for each request, adds it to response headers
    and injects it into the logging context for tracing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request_id_ctx.set(request_id)
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request with method, path, status code, and duration.
    Skips health check and docs endpoints to reduce noise.
    """

    SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else "unknown",
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory token bucket rate limiter per client IP.
    Configurable requests per window. Returns 429 when exceeded.
    """

    def __init__(self, app: FastAPI, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in {"/health", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        async with self._lock:
            # Clean up expired buckets with a small probability (1%) to prevent memory leaks
            if random.random() < 0.01:
                expired_ips = [
                    ip for ip, timestamps in self._buckets.items()
                    if not timestamps or now - timestamps[-1] >= self.window_seconds
                ]
                for ip in expired_ips:
                    self._buckets.pop(ip, None)

            # Get existing or create new bucket list
            bucket = self._buckets.get(client_ip, [])
            # Filter timestamps to keep only current window
            bucket = [t for t in bucket if now - t < self.window_seconds]

            if len(bucket) >= self.max_requests:
                if bucket:
                    self._buckets[client_ip] = bucket
                else:
                    self._buckets.pop(client_ip, None)
                exceeded = True
            else:
                bucket.append(now)
                self._buckets[client_ip] = bucket
                exceeded = False

        if exceeded:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Maximum {self.max_requests} requests per {self.window_seconds} seconds.",
                    "retry_after_seconds": self.window_seconds,
                },
            )

        return await call_next(request)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Firebase authentication for law-enforcement endpoints.
    Expects Authorization: Bearer <token>.
    """
    def __init__(self, app: FastAPI, protected_prefixes: tuple = ()):
        super().__init__(app)
        self.protected_prefixes = protected_prefixes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if any(request.url.path.startswith(prefix) for prefix in self.protected_prefixes):
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header.startswith("Bearer "):
                logger.warning("unauthorized_access_attempt", reason="missing_bearer", path=request.url.path, client_ip=request.client.host if request.client else "unknown")
                return JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "message": "Valid Bearer token required for law-enforcement routes."}
                )
                
            token = auth_header.split(" ")[1]
            try:
                # Verify the Firebase JWT
                decoded_token = auth.verify_id_token(token)
                
                # Check for required role
                if decoded_token.get("role") != "law_enforcement" and not decoded_token.get("admin"):
                    logger.warning("forbidden_access_attempt", reason="insufficient_permissions", uid=decoded_token.get("uid"), path=request.url.path, client_ip=request.client.host if request.client else "unknown")
                    return JSONResponse(
                        status_code=403,
                        content={"error": "forbidden", "message": "Insufficient permissions to access law-enforcement routes."}
                    )
                    
                # Optionally inject the user into the request state
                request.state.user = decoded_token
                
            except FirebaseError as e:
                logger.warning("unauthorized_access_attempt", reason="invalid_token", error=str(e), path=request.url.path, client_ip=request.client.host if request.client else "unknown")
                return JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "message": "Invalid or expired token."}
                )
                
        return await call_next(request)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches unhandled exceptions. Returns structured JSON error.
    Never exposes stack traces to clients.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "unhandled_exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
        },
    )
