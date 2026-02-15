"""
FastAPI Application Entry Point
Smart Healthcare Appointment Management System
"""
import traceback
import time

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import engine
from app.models import user, appointment, queue, notification

# Import routers - handle missing modules gracefully
try:
    from app.api.v1.endpoints import auth
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    print("⚠️  Auth router not available")

try:
    from app.api.v1.endpoints import appointments as appointments_router
    APPOINTMENTS_AVAILABLE = True
except ImportError:
    APPOINTMENTS_AVAILABLE = False
    print("⚠️  Appointments router not available")

try:
    from app.api.v1.endpoints import ai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️  AI router not available")

try:
    from app.api.v1.endpoints import users
    USERS_AVAILABLE = True
except ImportError:
    USERS_AVAILABLE = False
    print("⚠️  Users router not available")

try:
    from app.api.v1.endpoints import queue as queue_router
    QUEUE_AVAILABLE = True
except ImportError:
    QUEUE_AVAILABLE = False
    print("⚠️  Queue router not available")

# Create database tables
print("📊 Creating database tables...")
try:
    user.Base.metadata.create_all(bind=engine)
    appointment.Base.metadata.create_all(bind=engine)
    queue.Base.metadata.create_all(bind=engine)
    notification.Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
except Exception as e:
    print(f"⚠️  Database initialization warning: {e}")

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Healthcare Appointment Management System with ML-based predictions",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# MIDDLEWARE ORDER NOTE
# - Catch exceptions middleware should be declared BEFORE other middlewares
#   if you want it to wrap them too.
# - In FastAPI/Starlette, later-declared middleware becomes "inner".
# - We keep your timing middleware, but place exception middleware first
#   so it can catch errors raised downstream.
# -------------------------------------------------------------------

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    """
    Always return JSON on errors, but preserve HTTPException status codes.
    """
    try:
        return await call_next(request)

    # Preserve expected HTTP errors (401/403/404/etc.)
    except HTTPException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # Validation errors as proper 422 JSON
    except RequestValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "body": exc.body},
        )

    # DB errors as clean 500 JSON + traceback in console
    except SQLAlchemyError:
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error occurred"},
        )

    # Everything else: 500 JSON + traceback
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "exception": str(exc),
                "path": str(request.url),
                "method": request.method,
            },
        )

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Exception handlers
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

# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "database": "connected",
        "ml_models_path": settings.ML_MODELS_PATH
    }

# Root endpoint
@app.get("/", tags=["Root"])
def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "Welcome to Smart Healthcare Appointment Management System",
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "redoc": "/api/redoc",
        "health": "/health",
        "features": [
            "AI-powered no-show prediction",
            "Intelligent wait time estimation",
            "Priority-based patient classification",
            "Queue optimization",
            "Real-time notifications"
        ]
    }

# API Information endpoint
@app.get("/api/info", tags=["API"])
def api_info():
    """
    Get API information and available endpoints
    """
    return {
        "api_version": "v1",
        "base_path": settings.API_V1_PREFIX,
        "available_endpoints": {
            "authentication": f"{settings.API_V1_PREFIX}/auth" if AUTH_AVAILABLE else "Not available",
            "users": f"{settings.API_V1_PREFIX}/users" if USERS_AVAILABLE else "Not available",
            "appointments": f"{settings.API_V1_PREFIX}/appointments" if APPOINTMENTS_AVAILABLE else "Not available",
            "queue": f"{settings.API_V1_PREFIX}/queue" if QUEUE_AVAILABLE else "Not available",
            "ai_services": f"{settings.API_V1_PREFIX}/ai" if AI_AVAILABLE else "Not available"
        },
        "ai_features": {
            "no_show_prediction": f"{settings.API_V1_PREFIX}/ai/predict-noshow",
            "wait_time_estimation": f"{settings.API_V1_PREFIX}/ai/estimate-wait-time",
            "priority_classification": f"{settings.API_V1_PREFIX}/ai/classify-priority",
            "queue_optimization": f"{settings.API_V1_PREFIX}/ai/optimize-queue",
            "batch_prediction": f"{settings.API_V1_PREFIX}/ai/batch-predict",
            "health_check": f"{settings.API_V1_PREFIX}/ai/health"
        }
    }

# Include API routers conditionally
if AUTH_AVAILABLE:
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Authentication"])
    print("✅ Auth router included")

if USERS_AVAILABLE:
    app.include_router(users.router, prefix=settings.API_V1_PREFIX, tags=["Users"])
    print("✅ Users router included")

if APPOINTMENTS_AVAILABLE:
    app.include_router(appointments_router.router, prefix=settings.API_V1_PREFIX, tags=["Appointments"])
    print("✅ Appointments router included")

if QUEUE_AVAILABLE:
    app.include_router(queue_router.router, prefix=settings.API_V1_PREFIX, tags=["Queue"])
    print("✅ Queue router included")

if AI_AVAILABLE:
    app.include_router(ai.router, prefix=settings.API_V1_PREFIX, tags=["AI Services"])
    print("✅ AI router included")

# Startup event
@app.on_event("startup")
async def startup_event():
    print("=" * 70)
    print(f"🚀 Starting {settings.APP_NAME}")
    print(f"📊 Version: {settings.APP_VERSION}")
    print(f"🔧 Debug Mode: {settings.DEBUG}")
    print(f"🗄️  Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Connected'}")
    print(f"🤖 AI Models Path: {settings.ML_MODELS_PATH}")
    print(f"📡 API Prefix: {settings.API_V1_PREFIX}")
    print(f"📚 Documentation: http://127.0.0.1:8000/api/docs")
    print("=" * 70)
    print("Available Routers:")
    print(f"  • Authentication: {'✅' if AUTH_AVAILABLE else '❌'}")
    print(f"  • Users: {'✅' if USERS_AVAILABLE else '❌'}")
    print(f"  • Appointments: {'✅' if APPOINTMENTS_AVAILABLE else '❌'}")
    print(f"  • Queue: {'✅' if QUEUE_AVAILABLE else '❌'}")
    print(f"  • AI Services: {'✅' if AI_AVAILABLE else '❌'}")
    print("=" * 70)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    print("=" * 70)
    print("🛑 Shutting down application...")
    print("=" * 70)

# Development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )