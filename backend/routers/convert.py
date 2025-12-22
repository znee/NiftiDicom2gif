"""
API routes for file conversion.
"""
import gc
import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import List, Literal

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.nifti_processor import process_nifti_from_path
from services.dicom_processor import process_dicom_series, process_single_dicom
from utils.gif_generator import generate_gif, get_preview_frames, get_all_preview_frames, Colormap

logger = logging.getLogger(__name__)

# Check if production mode
IS_PRODUCTION = os.getenv("PRODUCTION", "").lower() in ("true", "1", "yes")


def sanitize_error_message(error: str) -> str:
    """Remove file paths and sensitive info from error messages."""
    # Remove file paths (Unix and Windows)
    error = re.sub(r'[/\\][\w\-./\\]+\.(nii|nii\.gz|dcm|dicom|gif|png)', '[file]', error, flags=re.IGNORECASE)
    error = re.sub(r'[/\\][\w\-./\\]+temp[/\\][\w\-]+', '[temp]', error)
    # Remove UUIDs that might be in paths
    error = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '[id]', error, flags=re.IGNORECASE)
    return error

router = APIRouter()

# Store for generated GIFs (task_id -> file_path)
GENERATED_GIFS: dict[str, str] = {}

# Temp directory
TEMP_DIR = Path(__file__).parent.parent / "temp"

# Limits
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB per file
MAX_FILES = 1000  # Max number of files in a series
MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB total

# Cloud-specific limits (Render free tier: 512MB RAM, 0.1 CPU, ~30s timeout)
# With ~150MB for Python/FastAPI overhead, we have ~350MB for processing
# A NIfTI volume uses: voxels × 4 bytes (float32) + processing overhead (~2x)
# Safe limit: 350MB / 8 bytes = ~44M voxels, but use 20M for safety margin
CLOUD_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB compressed (can expand 10x+)
CLOUD_MAX_PREVIEW_FRAMES = 50  # Limit preview frames to reduce memory
CLOUD_MAX_GIF_SIZE = 320  # Smaller max GIF size for cloud
# Max voxels: ~256×256×200 = 13M voxels uses ~100MB RAM (float32 + overhead)
# Conservative limit for 512MB free tier
CLOUD_MAX_VOXELS = 15 * 1024 * 1024  # 15 million voxels max for cloud


class ConversionResponse(BaseModel):
    success: bool
    task_id: str
    gif_url: str
    preview_frames: List[str]
    metadata: dict


class PreviewResponse(BaseModel):
    success: bool
    task_id: str
    all_frames: List[str]
    total_frames: int
    original_total: int  # Total frames before slice filtering (for client-side filtering)
    metadata: dict


def detect_file_type(filename: str) -> Literal["nifti", "dicom"]:
    """Detect file type from filename."""
    lower = filename.lower()
    if lower.endswith(('.nii', '.nii.gz')):
        return "nifti"
    elif lower.endswith(('.dcm', '.dicom')) or '.' not in lower:
        # DICOM files often have no extension
        return "dicom"
    else:
        raise ValueError(f"Unsupported file type: {filename}. Use .nii, .nii.gz, or .dcm files.")


@router.post("/convert", response_model=ConversionResponse)
async def convert_to_gif(
    files: List[UploadFile] = File(...),
    mode: Literal["volume", "series"] = Form("volume"),
    orientation: Literal["axial", "coronal", "sagittal"] = Form("axial"),
    fps: int = Form(10),
    colormap: Colormap = Form("gray"),
    # Slice range (percentage 0-100)
    slice_start: int = Form(0),
    slice_end: int = Form(100),
    # Window/Level settings
    # Auto mode: width/level are percentiles (default 98/50 = 1st-99th percentile range centered on median)
    # Manual mode: width/level are absolute HU values (CT)
    window_mode: Literal["auto", "manual"] = Form("auto"),
    window_width: int = Form(98),
    window_level: int = Form(50),
    # Image transform controls
    flip_horizontal: bool = Form(False),
    flip_vertical: bool = Form(False),
    rotate90: int = Form(0),  # 0, 1, 2, or 3 (number of 90-degree CW rotations)
    reverse_slices: bool = Form(False),
    # GIF optimization settings
    max_gif_size: int = Form(512),
    max_frames: int = Form(0),
):
    """
    Convert uploaded NIfTI or DICOM files to animated GIF.

    - **files**: NIfTI (.nii, .nii.gz) or DICOM files
    - **mode**: "volume" for 3D→slices (or 4D first timepoint), "series" for 4D time animation or 2D DICOM sequence
    - **orientation**: Slice orientation (axial, coronal, sagittal)
    - **fps**: Animation speed (1-30 frames per second)
    - **colormap**: Color scheme (gray, viridis, plasma, hot, bone, jet)
    - **slice_start**: Start percentage of slices to include (0-100)
    - **slice_end**: End percentage of slices to include (0-100)
    - **window_mode**: "auto" for percentile-based, "manual" for absolute HU values
    - **window_width**: Window width (range)
    - **window_level**: Window level (center)
    - **flip_horizontal**: Flip images left-right
    - **flip_vertical**: Flip images up-down
    - **rotate90**: Number of 90-degree clockwise rotations (0-3)
    - **reverse_slices**: Reverse the slice order
    - **max_gif_size**: Maximum GIF dimension in pixels (default 512)
    - **max_frames**: Maximum number of frames (0 = no limit)
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Use stricter limits in production (cloud deployment has timeouts and memory limits)
    effective_max_file_size = CLOUD_MAX_FILE_SIZE if IS_PRODUCTION else MAX_FILE_SIZE
    effective_max_gif_size = CLOUD_MAX_GIF_SIZE if IS_PRODUCTION else 2048

    # Validate and clamp input parameters
    slice_start = max(0, min(100, slice_start))
    slice_end = max(0, min(100, slice_end))
    if slice_end <= slice_start:
        slice_end = min(100, slice_start + 1)
    rotate90 = rotate90 % 4  # Normalize to 0-3
    max_gif_size = max(64, min(effective_max_gif_size, max_gif_size))
    max_frames = max(0, min(1000, max_frames))

    # Validate file count
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {MAX_FILES} files allowed."
        )

    # Validate FPS
    fps = max(1, min(30, fps))

    # Ensure temp directory exists
    TEMP_DIR.mkdir(exist_ok=True)

    # Generate task ID
    task_id = str(uuid.uuid4())

    try:
        # Detect file type from first file
        first_filename = files[0].filename or "unknown"
        file_type = detect_file_type(first_filename)

        if file_type == "nifti":
            # Read and validate file size
            content = await files[0].read()
            if len(content) > effective_max_file_size:
                size_mb = effective_max_file_size // (1024*1024)
                if IS_PRODUCTION:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large for cloud processing (max {size_mb}MB). For larger files, run locally."
                    )
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size is {size_mb} MB."
                )

            # Save to temp file with correct extension (nibabel needs file path)
            # Use original extension to avoid treating .nii as gzipped
            suffix = ".nii.gz" if first_filename.lower().endswith(".nii.gz") else ".nii"
            temp_path = TEMP_DIR / f"{task_id}_input{suffix}"
            with open(temp_path, "wb") as f:
                f.write(content)

            try:
                # Process NIfTI with mode parameter
                max_voxels = CLOUD_MAX_VOXELS if IS_PRODUCTION else 0
                slices, metadata = process_nifti_from_path(
                    str(temp_path),
                    mode=mode,
                    orientation=orientation,
                    window_mode=window_mode,
                    window_width=window_width,
                    window_level=window_level,
                    max_voxels=max_voxels
                )
            finally:
                # Clean up temp input
                temp_path.unlink(missing_ok=True)

        elif file_type == "dicom":
            if len(files) == 1:
                # Single DICOM file (possibly multi-frame)
                content = await files[0].read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB."
                    )
                slices, metadata = process_single_dicom(
                    content,
                    window_mode=window_mode,
                    window_width=window_width,
                    window_level=window_level
                )
            else:
                # Multiple DICOM files (series)
                files_data = []
                total_size = 0

                for f in files:
                    content = await f.read()
                    total_size += len(content)

                    if total_size > MAX_TOTAL_SIZE:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Total upload size exceeds {MAX_TOTAL_SIZE // (1024*1024*1024)} GB limit."
                        )

                    files_data.append((content, f.filename or "unknown"))

                slices, metadata = process_dicom_series(
                    files_data,
                    mode=mode,
                    orientation=orientation,
                    window_mode=window_mode,
                    window_width=window_width,
                    window_level=window_level
                )

        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        if not slices:
            raise HTTPException(
                status_code=400,
                detail="No image data found. Please check your file is a valid NIfTI or DICOM."
            )

        # Apply slice range filtering
        if slice_start > 0 or slice_end < 100:
            total_slices = len(slices)
            start_idx = int(total_slices * slice_start / 100)
            end_idx = int(total_slices * slice_end / 100)
            # Ensure at least one slice
            end_idx = max(start_idx + 1, end_idx)
            slices = slices[start_idx:end_idx]
            metadata["slice_range"] = f"{slice_start}%-{slice_end}%"
            metadata["slices_after_filter"] = len(slices)

        # Apply image transforms
        import numpy as np
        transforms_applied = []

        # Reverse slice order if requested
        if reverse_slices:
            slices = slices[::-1]
            transforms_applied.append("reversed")

        # Apply rotation (0, 1, 2, or 3 times 90 degrees CW)
        if rotate90 > 0:
            rotate90 = rotate90 % 4  # Ensure 0-3
            slices = [np.rot90(s, k=-rotate90) for s in slices]  # negative k for CW
            transforms_applied.append(f"rotated_{rotate90 * 90}deg")

        # Apply flips
        if flip_vertical:
            slices = [np.flipud(s) for s in slices]
            transforms_applied.append("flip_vertical")

        if flip_horizontal:
            slices = [np.fliplr(s) for s in slices]
            transforms_applied.append("flip_horizontal")

        if transforms_applied:
            metadata["transforms"] = transforms_applied

        # Generate preview frames
        preview_frames = get_preview_frames(slices, num_frames=5, colormap=colormap, max_size=min(256, max_gif_size))

        # Generate GIF with optimization
        gif_path = TEMP_DIR / f"{task_id}.gif"
        generate_gif(
            slices,
            output_path=str(gif_path),
            fps=fps,
            colormap=colormap,
            max_size=max_gif_size,
            max_frames=max_frames,
            optimize=True
        )

        # Free memory from slices (important for cloud with limited RAM)
        del slices
        if IS_PRODUCTION:
            gc.collect()

        # Store reference
        GENERATED_GIFS[task_id] = str(gif_path)

        return ConversionResponse(
            success=True,
            task_id=task_id,
            gif_url=f"/api/download/{task_id}",
            preview_frames=preview_frames,
            metadata=metadata
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(str(e)))
    except HTTPException:
        raise
    except MemoryError:
        logger.error(f"Memory error for task {task_id[:8]}")
        raise HTTPException(
            status_code=413,
            detail="File too large to process in memory. Try a smaller file or fewer slices."
        )
    except OSError as e:
        logger.error(f"OS error for task {task_id[:8]}: {type(e).__name__}")
        error_msg = str(e).lower()
        if "timed out" in error_msg or "timeout" in error_msg:
            raise HTTPException(
                status_code=504,
                detail="File upload timed out. If loading from network storage, try copying the file locally first."
            )
        elif "permission" in error_msg:
            raise HTTPException(
                status_code=403,
                detail="Permission denied reading file. Check file permissions."
            )
        # Hide full path in production
        detail = "File system error occurred" if IS_PRODUCTION else f"File system error: {sanitize_error_message(str(e))}"
        raise HTTPException(status_code=500, detail=detail)
    except Exception as e:
        logger.error(f"Processing error for task {task_id[:8]}: {type(e).__name__}")
        # Hide detailed error in production
        detail = "Processing error occurred. Please check your file and try again." if IS_PRODUCTION else f"Processing error: {sanitize_error_message(str(e))}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/preview", response_model=PreviewResponse)
async def get_interactive_preview(
    files: List[UploadFile] = File(...),
    mode: Literal["volume", "series"] = Form("volume"),
    orientation: Literal["axial", "coronal", "sagittal"] = Form("axial"),
    # Window/Level settings
    window_mode: Literal["auto", "manual"] = Form("auto"),
    window_width: int = Form(98),
    window_level: int = Form(50),
    # Preview size (smaller for faster loading)
    preview_size: int = Form(256),
):
    """
    Get all frames as grayscale base64 images for interactive preview.

    Slice filtering, colormap, and transforms are applied client-side for instant feedback.
    Returns ALL frames in grayscale - client applies colormap and slice range.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum {MAX_FILES} files allowed."
        )

    # Use stricter limits in production (cloud deployment has timeouts)
    effective_max_file_size = CLOUD_MAX_FILE_SIZE if IS_PRODUCTION else MAX_FILE_SIZE
    max_preview_frames = CLOUD_MAX_PREVIEW_FRAMES if IS_PRODUCTION else 500

    # Validate and clamp preview_size (smaller for cloud to speed up)
    max_preview_size = 256 if IS_PRODUCTION else 512
    preview_size = max(64, min(max_preview_size, preview_size))

    TEMP_DIR.mkdir(exist_ok=True)
    task_id = str(uuid.uuid4())

    try:
        first_filename = files[0].filename or "unknown"
        file_type = detect_file_type(first_filename)

        if file_type == "nifti":
            content = await files[0].read()
            if len(content) > effective_max_file_size:
                size_mb = effective_max_file_size // (1024*1024)
                if IS_PRODUCTION:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large for cloud processing (max {size_mb}MB). For larger files, run locally."
                    )
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size is {size_mb} MB."
                )

            suffix = ".nii.gz" if first_filename.lower().endswith(".nii.gz") else ".nii"
            temp_path = TEMP_DIR / f"{task_id}_preview{suffix}"
            with open(temp_path, "wb") as f:
                f.write(content)

            try:
                max_voxels = CLOUD_MAX_VOXELS if IS_PRODUCTION else 0
                slices, metadata = process_nifti_from_path(
                    str(temp_path),
                    mode=mode,
                    orientation=orientation,
                    window_mode=window_mode,
                    window_width=window_width,
                    window_level=window_level,
                    max_voxels=max_voxels
                )
            finally:
                temp_path.unlink(missing_ok=True)

        elif file_type == "dicom":
            if len(files) == 1:
                content = await files[0].read()
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB."
                    )
                slices, metadata = process_single_dicom(
                    content,
                    window_mode=window_mode,
                    window_width=window_width,
                    window_level=window_level
                )
            else:
                files_data = []
                total_size = 0

                for f in files:
                    content = await f.read()
                    total_size += len(content)

                    if total_size > MAX_TOTAL_SIZE:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Total upload size exceeds {MAX_TOTAL_SIZE // (1024*1024*1024)} GB limit."
                        )

                    files_data.append((content, f.filename or "unknown"))

                slices, metadata = process_dicom_series(
                    files_data,
                    mode=mode,
                    orientation=orientation,
                    window_mode=window_mode,
                    window_width=window_width,
                    window_level=window_level
                )
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        if not slices:
            raise HTTPException(
                status_code=400,
                detail="No image data found."
            )

        original_total = len(slices)

        # Subsample frames if too many (for cloud processing speed)
        if len(slices) > max_preview_frames:
            step = len(slices) / max_preview_frames
            indices = [int(i * step) for i in range(max_preview_frames)]
            slices = [slices[i] for i in indices]
            metadata["subsampled"] = True
            metadata["original_frames"] = original_total

        # Get all frames as grayscale base64 (colormap and slice range applied client-side)
        all_frames = get_all_preview_frames(slices, max_size=preview_size, return_grayscale=True)

        # Free memory from slices (important for cloud with limited RAM)
        del slices
        if IS_PRODUCTION:
            gc.collect()

        metadata["num_frames"] = len(all_frames)
        metadata["preview_size"] = preview_size

        return PreviewResponse(
            success=True,
            task_id=task_id,
            all_frames=all_frames,
            total_frames=len(all_frames),
            original_total=original_total,
            metadata=metadata
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=sanitize_error_message(str(e)))
    except HTTPException:
        raise
    except MemoryError:
        logger.error(f"Memory error for preview task {task_id[:8]}")
        gc.collect()  # Try to free memory
        raise HTTPException(
            status_code=413,
            detail="File too large for cloud processing. For large files, run locally."
        )
    except Exception as e:
        logger.error(f"Preview error for task {task_id[:8]}: {type(e).__name__}")
        detail = "Preview error occurred. Please check your file and try again." if IS_PRODUCTION else f"Preview error: {sanitize_error_message(str(e))}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/download/{task_id}")
async def download_gif(task_id: str):
    """
    Download the generated GIF file.
    """
    if task_id not in GENERATED_GIFS:
        raise HTTPException(status_code=404, detail="GIF not found. It may have been cleared or expired.")

    gif_path = GENERATED_GIFS[task_id]

    if not os.path.exists(gif_path):
        raise HTTPException(status_code=404, detail="GIF file not found on disk. Please regenerate.")

    filename = f"converted_{task_id[:8]}.gif"
    return FileResponse(
        gif_path,
        media_type="image/gif",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.delete("/clear")
async def clear_all():
    """
    Clear all uploaded files and generated GIFs (privacy feature).
    Removes all files and subdirectories in the temp directory.
    """
    global GENERATED_GIFS

    cleared_count = 0

    # Delete all tracked GIF files
    for task_id, path in list(GENERATED_GIFS.items()):
        try:
            if os.path.exists(path):
                os.remove(path)
                cleared_count += 1
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {e}")

    GENERATED_GIFS.clear()

    # Thoroughly clean temp directory (files and subdirectories)
    if TEMP_DIR.exists():
        for item in TEMP_DIR.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    cleared_count += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    cleared_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {item}: {e}")

    logger.info(f"Clear all: removed {cleared_count} items from temp directory")
    return {"success": True, "message": f"Cleared {cleared_count} files"}


@router.delete("/clear/{task_id}")
async def clear_task(task_id: str):
    """
    Clear a specific task's GIF.
    """
    if task_id not in GENERATED_GIFS:
        return {"success": True, "message": "Task not found or already cleared"}

    path = GENERATED_GIFS[task_id]
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning(f"Failed to delete {path}: {e}")

    del GENERATED_GIFS[task_id]

    return {"success": True, "message": f"Task {task_id[:8]} cleared"}
