"""
NIfTI/DICOM to GIF Converter - FastAPI Backend
"""
import shutil
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import convert

# Temp directory for storing generated GIFs
TEMP_DIR = Path(__file__).parent / "temp"


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

# CORS configuration for React frontend (allow any origin for local network access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(convert.router, prefix="/api", tags=["convert"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "NIfTI/DICOM to GIF Converter API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8802, reload=True)
