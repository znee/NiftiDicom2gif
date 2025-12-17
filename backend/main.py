"""
NIfTI/DICOM to GIF Converter - FastAPI Backend
"""
import os
import shutil
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers import convert

# Environment configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8802"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")  # Comma-separated list or "*" for all

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


app = FastAPI(
    title="NIfTI/DICOM to GIF Converter",
    description="Convert medical images to animated GIFs",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
# Set CORS_ORIGINS env var to restrict origins in production (comma-separated)
# e.g., CORS_ORIGINS="https://example.com,https://app.example.com"
cors_origins = ["*"] if CORS_ORIGINS == "*" else [o.strip() for o in CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(convert.router, prefix="/api", tags=["convert"])


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
    @app.get("/")
    async def serve_root():
        """Serve the frontend index.html."""
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve SPA - return index.html for all non-API routes."""
        file_path = STATIC_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        """Development mode - API only."""
        return {"status": "ok", "message": "NIfTI/DICOM to GIF Converter API (dev mode)"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
