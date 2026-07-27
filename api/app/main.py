import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx
import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import Scope

from .api import router
from .config import get_settings
from .database import engine
from .logging_config import configure_logging

settings = get_settings()
configure_logging()
logger = structlog.get_logger()

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.release_sha,
        send_default_pii=False,
        traces_sample_rate=0.1,
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(
    title="Miami Beach Emergency Management Dashboard API",
    version="1.0.0",
    docs_url="/docs" if settings.docs_enabled and not settings.production else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.docs_enabled and not settings.production else None,
    lifespan=lifespan,
)
app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
if not settings.production:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID"],
    )


@app.middleware("http")
async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    started = time.monotonic()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    try:
        if request.url.path.startswith("/api/"):
            try:
                forwarded = request.headers.get("cf-connecting-ip") or (
                    request.client.host if request.client else "unknown"
                )
                bucket = int(time.time() // 60)
                key = f"eoc:rate:{forwarded}:{bucket}"
                count = await request.app.state.redis.incr(key)
                if count == 1:
                    await request.app.state.redis.expire(key, 90)
                if count > settings.rate_limit_per_minute:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Request rate limit exceeded. Try again shortly.",
                            "request_id": request_id,
                        },
                        headers={"Retry-After": "60"},
                    )
            except Exception:
                logger.warning("rate_limit_backend_unavailable")
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled_request_error", path=request.url.path)
        response = JSONResponse(
            status_code=500,
            content={
                "detail": "The dashboard could not complete this request.",
                "request_id": request_id,
            },
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://maps.googleapis.com https://maps.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: blob: https://*.googleapis.com https://*.gstatic.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' https://maps.googleapis.com https://maps.gstatic.com; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'none'; object-src 'none'"
    )
    response.headers["Cache-Control"] = (
        "no-store" if request.url.path.startswith("/api/") else "public, max-age=300"
    )
    logger.info(
        "request_complete",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.monotonic() - started) * 1000, 2),
    )
    structlog.contextvars.clear_contextvars()
    return response


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "alive", "time": datetime.now(UTC).isoformat()}


@app.get("/health/ready")
async def ready(request: Request) -> JSONResponse:
    checks: dict[str, str] = {}
    critical_healthy = True
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            pulsepoint_state = await connection.scalar(
                text("SELECT state FROM source_health WHERE source_id = 'pulsepoint-x1012'")
            )
        checks["postgres"] = "healthy"
        checks["pulsepoint"] = str(pulsepoint_state or "not_yet_polled")
    except Exception:
        checks["postgres"] = "unavailable"
        checks["pulsepoint"] = "unavailable"
        critical_healthy = False
    try:
        checks["redis"] = "healthy" if await request.app.state.redis.ping() else "unavailable"
    except Exception:
        checks["redis"] = "unavailable"
        critical_healthy = False
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{str(settings.ollama_url).rstrip('/')}/api/tags",
                timeout=3,
            )
            response.raise_for_status()
            model_names = {
                model.get("name")
                for model in response.json().get("models", [])
                if isinstance(model, dict)
            }
            checks["ollama"] = (
                "healthy" if settings.ollama_model in model_names else "model_unavailable"
            )
        except (httpx.HTTPError, ValueError, TypeError):
            checks["ollama"] = "unavailable"
        if settings.maxun_enabled:
            try:
                response = await client.get(
                    str(settings.maxun_url).rstrip("/"),
                    timeout=3,
                )
                checks["maxun"] = "healthy" if response.is_success else "unavailable"
            except httpx.HTTPError:
                checks["maxun"] = "unavailable"
        else:
            checks["maxun"] = "disabled"
        if settings.hermes_health_url:
            try:
                response = await client.get(settings.hermes_health_url, timeout=3)
                checks["hermes"] = "healthy" if response.is_success else "unavailable"
            except httpx.HTTPError:
                checks["hermes"] = "unavailable"
        else:
            checks["hermes"] = "not_configured"
    status = 200 if critical_healthy else 503
    return JSONResponse(
        status_code=status,
        content={"status": "ready" if status == 200 else "not_ready", "checks": checks},
    )


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(router)


class SpaStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        if scope["type"] != "http" or scope["method"] not in {"GET", "HEAD"}:
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and "." not in Path(path).name:
                if self.directory is None:
                    raise
                return FileResponse(Path(self.directory) / "index.html")
            raise


if settings.static_dir and settings.static_dir.is_dir():
    app.mount("/", SpaStaticFiles(directory=str(settings.static_dir), html=True), name="spa")
