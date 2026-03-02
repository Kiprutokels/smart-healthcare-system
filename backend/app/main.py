"""
FastAPI Application Entry Point
Smart Healthcare Appointment Management System
"""
from __future__ import annotations

import time
import traceback

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import engine
from app.models import appointment, notification, queue, user

# ── Conditional router imports ───────────────────────────────────────────────

def _try_import(module_path: str, label: str):
    try:
        import importlib
        mod = importlib.import_module(module_path)
        print(f"✅ {label} router loaded")
        return mod
    except ImportError as exc:
        print(f"⚠️  {label} router not available: {exc}")
        return None


_auth        = _try_import("app.api.v1.endpoints.auth",         "Auth")
_users       = _try_import("app.api.v1.endpoints.users",        "Users")
_appointments= _try_import("app.api.v1.endpoints.appointments", "Appointments")
_queue       = _try_import("app.api.v1.endpoints.queue",        "Queue")
_ai          = _try_import("app.api.v1.endpoints.ai",           "AI")

# ── Database initialisation ──────────────────────────────────────────────────

print("📊 Creating database tables…")
try:
    for model in (user, appointment, queue, notification):
        model.Base.metadata.create_all(bind=engine)
    print("✅ Database tables ready")
except Exception as exc:
    print(f"⚠️  DB init warning: {exc}")

# ── FastAPI application ──────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Healthcare Appointment Management System",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Middleware ───────────────────────────────────────────────────────────────

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    """
    Global exception handler — always returns JSON.
    HTTPExceptions (401, 403, 404 …) preserve their original status codes.
    """
    try:
        return await call_next(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    except RequestValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "body": exc.body},
        )
    except SQLAlchemyError:
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error occurred"},
        )
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "detail":    "Internal Server Error",
                "exception": str(exc),
                "path":      str(request.url),
                "method":    request.method,
            },
        )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start)
    return response

# ── Exception handlers (declarative) ────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred"},
    )

# ── Core routes ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status":          "healthy",
        "app_name":        settings.APP_NAME,
        "version":         settings.APP_VERSION,
        "debug":           settings.DEBUG,
        "database":        "connected",
        "ml_models_path":  settings.ML_MODELS_PATH,
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs":    "/api/docs",
        "redoc":   "/api/redoc",
        "health":  "/health",
    }


@app.get("/api/info", tags=["API"])
def api_info():
    return {
        "api_version": "v1",
        "base_path":   settings.API_V1_PREFIX,
        "available_endpoints": {
            "authentication": f"{settings.API_V1_PREFIX}/auth"         if _auth         else "Not available",
            "users":          f"{settings.API_V1_PREFIX}/users"        if _users        else "Not available",
            "appointments":   f"{settings.API_V1_PREFIX}/appointments" if _appointments else "Not available",
            "queue":          f"{settings.API_V1_PREFIX}/queue"        if _queue        else "Not available",
            "ai_services":    f"{settings.API_V1_PREFIX}/ai"           if _ai           else "Not available",
        },
    }

# ── Register routers ─────────────────────────────────────────────────────────

if _auth:
    app.include_router(_auth.router, prefix=settings.API_V1_PREFIX)
if _users:
    app.include_router(_users.router, prefix=settings.API_V1_PREFIX)
if _appointments:
    app.include_router(_appointments.router, prefix=settings.API_V1_PREFIX)
if _queue:
    app.include_router(_queue.router, prefix=settings.API_V1_PREFIX)
if _ai:
    app.include_router(_ai.router, prefix=settings.API_V1_PREFIX)

# ── Lifecycle events ─────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    line = "=" * 70
    print(line)
    print(f"🚀  {settings.APP_NAME}  v{settings.APP_VERSION}")
    print(f"🔧  Debug         : {settings.DEBUG}")
    print(f"🗄️   Database      : {'@' + settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'connected'}")
    print(f"🤖  ML Models     : {settings.ML_MODELS_PATH}")
    print(f"📡  API Prefix    : {settings.API_V1_PREFIX}")
    print(f"🔑  Internal Auth : X-Internal-API-Key header required on /ai/* routes")
    print(line)
    print("  Auth        :", "✅" if _auth         else "❌")
    print("  Users       :", "✅" if _users        else "❌")
    print("  Appointments:", "✅" if _appointments else "❌")
    print("  Queue       :", "✅" if _queue        else "❌")
    print("  AI Services :", "✅" if _ai           else "❌")
    print(line)


@app.on_event("shutdown")
async def shutdown_event():
    print("=" * 70)
    print("🛑  Shutting down…")
    print("=" * 70)


# ── Dev entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
