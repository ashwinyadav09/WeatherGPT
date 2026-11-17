from __future__ import annotations

import datetime as dt
import importlib
import uuid
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from services.api.app.config import settings
from services.api.app.licence import get_licence_register
from services.api.app.modules.status.service import status_tracker

logger = structlog.get_logger()

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP Request Latency", ["endpoint"])

app = FastAPI(
    title="WeatherGPT API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception("unhandled_error", exc_info=exc, request_id=request_id)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "request_id": request_id,
            }
        },
    )


@app.get("/healthz", tags=["health"])
async def healthz() -> dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "env": settings.env,
    }


@app.get("/metrics", tags=["monitoring"])
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/sources", tags=["sources"])
async def list_sources() -> Any:
    return get_licence_register()


@app.get("/v1/status", tags=["status"])
async def system_status() -> Any:
    report = status_tracker.get_status_report()
    report["imd_connected"] = settings.imd_enabled
    report["primary_forecast_source"] = settings.forecast_primary
    return report


def discover_and_mount_routers(target_app: FastAPI) -> None:
    """Discovers router.py files across modules, conversation, and gateways, and mounts them under /v1."""
    # 1. Mount conversation router
    try:
        from services.api.app.conversation.router import router as conv_router
        target_app.include_router(conv_router, prefix="/v1")
    except ImportError as e:
        logger.warning("conversation_router_import_failed", error=str(e))

    # 2. Mount gateways routers
    try:
        from services.api.app.gateways.speech.router import router as speech_router
        target_app.include_router(speech_router, prefix="/v1")
    except ImportError as e:
        logger.warning("speech_router_import_failed", error=str(e))

    # 3. Auto-discover modules
    modules_dir = Path(__file__).resolve().parent / "modules"
    if modules_dir.exists():
        for item in modules_dir.iterdir():
            if item.is_dir() and (item / "router.py").exists():
                module_name = f"services.api.app.modules.{item.name}.router"
                try:
                    mod = importlib.import_module(module_name)
                    router = getattr(mod, "router", None)
                    if router:
                        target_app.include_router(router, prefix="/v1")
                        logger.info("mounted_router", module=item.name)
                except Exception as ex:
                    logger.warning("failed_to_mount_module_router", module=item.name, error=str(ex))


discover_and_mount_routers(app)
