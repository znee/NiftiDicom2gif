"""
NIfTI/DICOM to GIF Converter - FastAPI Backend

Security notes:
- Set HOST=127.0.0.1 for localhost-only access (recommended for local use)
- Set HOST=0.0.0.0 to allow network access (use with caution)
- Set PRODUCTION=true for cloud deployments (disables docs, hides errors)
- Set CORS_ORIGINS to specific domains in production
"""
import os
import shutil
import time
from pathlib import Path
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from routers import convert
import logging

# Configure logging - avoid logging sensitive paths in production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
# Default to 127.0.0.1 (localhost only) for security - use 0.0.0.0 to allow network access
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8802"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8801,http://127.0.0.1:5173,http://127.0.0.1:8801")
IS_PRODUCTION = os.getenv("PRODUCTION", "").lower() in ("true", "1", "yes")

# Rate limiting configuration (requests per minute per IP)
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "30"))  # 30 requests per minute default
RATE_LIMIT_WINDOW = 60  # seconds

# Temp directory for storing generated GIFs
TEMP_DIR = Path(__file__).parent / "temp"

# Static files directory (for production deployment with built frontend)
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - create/cleanup temp directory."""
    TEMP_DIR.mkdir(exist_ok=True)
    yield
    # Cleanup on shutdown
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


# Disable docs in production for security
app = FastAPI(
    title="NIfTI/DICOM to GIF Converter",
    description="Convert medical images to animated GIFs",
    version="1.0.0",
    lifespan=lifespan,
    # Disable Swagger UI and ReDoc in production
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# CORS configuration
# Set CORS_ORIGINS env var to restrict origins in production (comma-separated)
# e.g., CORS_ORIGINS="https://example.com,https://app.example.com"
cors_origins = ["*"] if CORS_ORIGINS == "*" else [o.strip() for o in CORS_ORIGINS.split(",")]
# Note: allow_credentials=True is incompatible with allow_origins=["*"]
# Only enable credentials for specific origins
allow_credentials = CORS_ORIGINS != "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory rate limiter
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting middleware to prevent abuse."""
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    # Clean old entries and check rate limit
    current_time = time.time()
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip]
        if current_time - t < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT:
        logger.warning(f"Rate limit exceeded for {client_ip}")
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait a moment and try again."}
        )

    # Record this request
    _rate_limit_store[client_ip].append(current_time)

    return await call_next(request)


# Include routers
app.include_router(convert.router, prefix="/api", tags=["convert"])


# Global exception handler to hide internal details in production
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions - hide internal details in production."""
    logger = logging.getLogger(__name__)

    if IS_PRODUCTION:
        # In production, log the full error but return generic message
        logger.error(f"Unexpected error: {type(exc).__name__}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred. Please try again."}
        )
    else:
        # In development, show full error details
        logger.exception(f"Unexpected error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)}
        )


@app.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    return {"status": "ok", "message": "NIfTI/DICOM to GIF Converter API"}


# Check if we have a built frontend to serve
_has_static = STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists()
_has_assets = _has_static and (STATIC_DIR / "assets").exists()

if _has_assets:
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

if _has_static:
    # Mount the entire static directory to serve other static files (favicon, etc.)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def serve_root():
        """Serve the frontend index.html."""
        return FileResponse(STATIC_DIR / "index.html")

    # Catch-all for SPA client-side routing (but NOT for /api or /health)
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve SPA - return index.html for client-side routes only."""
        # Don't intercept API routes or health check
        if path.startswith("api") or path == "health":
            # Return 404 - let FastAPI handle these
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")

        # Try to serve static file if it exists
        file_path = STATIC_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # Otherwise return index.html for client-side routing
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        """Development mode - API only."""
        return {"status": "ok", "message": "NIfTI/DICOM to GIF Converter API (dev mode)"}


if __name__ == "__main__":
    import uvicorn

    # Security startup warnings
    print("\n" + "="*60)
    print("NIfTI/DICOM to GIF Converter - Security Info")
    print("="*60)

    if HOST == "0.0.0.0":
        print("⚠️  WARNING: Server bound to 0.0.0.0 (all interfaces)")
        print("   This allows access from other devices on your network.")
        print("   For local-only access, set HOST=127.0.0.1")
    else:
        print(f"✓ Server bound to {HOST} (localhost only)")

    if CORS_ORIGINS == "*":
        print("⚠️  WARNING: CORS allows all origins (*)")
        print("   Consider restricting to specific domains.")
    else:
        origins = [o.strip() for o in CORS_ORIGINS.split(",")]
        print(f"✓ CORS restricted to: {', '.join(origins[:3])}{'...' if len(origins) > 3 else ''}")

    if IS_PRODUCTION:
        print("✓ Production mode: API docs disabled, errors hidden")
    else:
        print(f"ℹ️  Development mode: API docs at http://{HOST}:{PORT}/docs")

    print(f"✓ Rate limit: {RATE_LIMIT} requests/minute per IP")
    print(f"✓ Upload limits: 500MB/file, 2GB total, 1000 files max")
    print("="*60 + "\n")

    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
