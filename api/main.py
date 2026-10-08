"""Main FastAPI application entry point for RoadX ML Service."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import api_settings
from api.routes import (
    health_router,
    ml_router,
    grievance_router,
    government_router,
    contractor_router,
    citizen_router,
    notification_router,
)
from api.schemas.responses import APIErrorDetails, APIErrorResponse
from api.service import MLInferenceService
from ml.common.logging_config import get_logger, setup_logging

logger = setup_logging(log_level=api_settings.log_level)
HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager handling application startup and shutdown tasks."""
    logger.info("Starting up %s (version %s)...", api_settings.app_name, api_settings.version)
    
    # Initialize unified ML pipeline singleton on startup
    service = MLInferenceService()
    service.initialize()
    app.state.ml_service = service

    yield

    logger.info("Shutting down %s...", api_settings.app_name)


app = FastAPI(
    title=api_settings.app_name,
    description=api_settings.app_description,
    version=api_settings.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Enable CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=api_settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_trace_middleware(request: Request, call_next):
    """HTTP middleware ensuring unique Request-ID tracing and timing metrics."""
    incoming_request_id = request.headers.get("X-Request-ID")
    request_id = incoming_request_id or f"req-{uuid.uuid4().hex[:12]}"
    request.state.request_id = request_id

    start_t = time.perf_counter()
    logger.info(
        "[%s] HTTP %s %s request received",
        request_id,
        request.method,
        request.url.path,
    )

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "[%s] HTTP %s %s completed with status %d in %.2f ms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
    except Exception as e:
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        logger.error(
            "[%s] HTTP %s %s unhandled exception after %.2f ms: %s",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
            e,
            exc_info=True,
        )
        raise e


# --- Structured Exception Handlers ---

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Format HTTP exceptions into consistent APIErrorResponse structure."""
    request_id = getattr(request.state, "request_id", None)
    
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", str(exc.detail))
        req_id = exc.detail.get("request_id", request_id)
    else:
        code = f"HTTP_{exc.status_code}"
        message = str(exc.detail)
        req_id = request_id

    error_payload = APIErrorResponse(
        error=APIErrorDetails(code=code, message=message, request_id=req_id)
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(),
        headers={"X-Request-ID": req_id} if req_id else None,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format request validation failures into HTTP 422 APIErrorResponse."""
    request_id = getattr(request.state, "request_id", None)
    # Summarize validation errors without leaking sensitive stack traces
    errors_summary = "; ".join(
        f"{' -> '.join(str(loc) for loc in err.get('loc', []))}: {err.get('msg')}"
        for err in exc.errors()
    )
    error_payload = APIErrorResponse(
        error=APIErrorDetails(
            code="VALIDATION_ERROR",
            message=f"Request schema validation failed: {errors_summary}",
            request_id=request_id,
        )
    )
    return JSONResponse(
        status_code=HTTP_422,
        content=error_payload.model_dump(),
        headers={"X-Request-ID": request_id} if request_id else None,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all handler returning sanitized HTTP 500 APIErrorResponse."""
    request_id = getattr(request.state, "request_id", None)
    logger.error("[%s] Internal server error: %s", request_id, exc, exc_info=True)
    
    error_payload = APIErrorResponse(
        error=APIErrorDetails(
            code="INTERNAL_SERVER_ERROR",
            message="An internal service error occurred. Please contact system administrator.",
            request_id=request_id,
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump(),
        headers={"X-Request-ID": request_id} if request_id else None,
    )


# Include Route Groups
app.include_router(health_router)
app.include_router(ml_router)
app.include_router(grievance_router)
app.include_router(government_router)
app.include_router(contractor_router)
app.include_router(citizen_router)
app.include_router(notification_router)

