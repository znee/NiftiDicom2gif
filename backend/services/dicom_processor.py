"""
DICOM file processing service.
Converts DICOM series (multiple 2D images) to slice sequences for GIF generation.
"""
import io
import logging
from typing import List, Tuple, Optional, Literal

import numpy as np

WindowMode = Literal["auto", "manual"]
import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut

logger = logging.getLogger(__name__)


def load_dicom(file_content: bytes) -> Tuple[np.ndarray, dict, pydicom.Dataset]:
    """
    Load a single DICOM file from bytes content.

    Args:
        file_content: Raw bytes of the DICOM file

    Returns:
        Tuple of (pixel array, metadata dict, pydicom dataset)
    """
    file_obj = io.BytesIO(file_content)
    ds = pydicom.dcmread(file_obj)

    # Get pixel data
    pixel_array = ds.pixel_array

    # Apply modality LUT (converts to Hounsfield Units for CT)
    pixel_array = apply_modality_lut(pixel_array, ds)

    # Apply VOI LUT (window/level) if available
    try:
        pixel_array = apply_voi_lut(pixel_array, ds)
    except Exception:
        pass  # VOI LUT not available

    metadata = {
        "patient_name": str(getattr(ds, 'PatientName', 'Unknown')),
        "modality": str(getattr(ds, 'Modality', 'Unknown')),
        "instance_number": int(getattr(ds, 'InstanceNumber', 0)) if hasattr(ds, 'InstanceNumber') else 0,
        "slice_location": float(ds.SliceLocation) if hasattr(ds, 'SliceLocation') else None,
        "rows": int(getattr(ds, 'Rows', 0)),
        "columns": int(getattr(ds, 'Columns', 0)),
        "window_center": getattr(ds, 'WindowCenter', None),
        "window_width": getattr(ds, 'WindowWidth', None),
    }

    # Extract position and orientation for proper sorting
    if hasattr(ds, 'ImagePositionPatient'):
        metadata['image_position'] = [float(x) for x in ds.ImagePositionPatient]
    if hasattr(ds, 'ImageOrientationPatient'):
        metadata['image_orientation'] = [float(x) for x in ds.ImageOrientationPatient]

    return pixel_array, metadata, ds


def compute_slice_position(metadata: dict) -> Optional[float]:
    """
    Compute slice position along the normal axis for proper sorting.
    Uses ImagePositionPatient and ImageOrientationPatient when available.

    Args:
        metadata: DICOM metadata dict

    Returns:
        Slice position value or None
    """
    if 'image_position' not in metadata or 'image_orientation' not in metadata:
        return metadata.get('slice_location')

    try:
        pos = np.array(metadata['image_position'])
        orient = metadata['image_orientation']

        # Row and column direction cosines
        row_cosine = np.array(orient[:3])
        col_cosine = np.array(orient[3:])

        # Normal to the image plane
        normal = np.cross(row_cosine, col_cosine)

        # Project position onto normal to get slice position
        slice_pos = np.dot(pos, normal)
        return float(slice_pos)
    except Exception:
        return metadata.get('slice_location')


def sort_dicom_files(
    files_data: List[Tuple[bytes, str]]
) -> List[Tuple[bytes, np.ndarray, dict]]:
    """
    Sort DICOM files by spatial position or instance number.
    Uses ImagePositionPatient for accurate 3D sorting when available.

    Args:
        files_data: List of (file_content, filename) tuples

    Returns:
        Sorted list of (file_content, pixel_array, metadata) tuples
    """
    loaded = []
    for content, filename in files_data:
        try:
            pixel_array, metadata, _ = load_dicom(content)
            metadata['filename'] = filename
            metadata['computed_position'] = compute_slice_position(metadata)
            loaded.append((content, pixel_array, metadata))
        except Exception as e:
            logger.warning(f"Could not load {filename}: {e}")
            continue

    if not loaded:
        return []

    # Determine best sorting method
    has_position = all(item[2].get('computed_position') is not None for item in loaded)
    has_instance = all(item[2].get('instance_number', 0) > 0 for item in loaded)

    def sort_key(item):
        _, _, meta = item
        if has_position:
            return (meta.get('computed_position', 0),)
        elif has_instance:
            return (meta.get('instance_number', 0),)
        else:
            # Fallback to slice_location then instance_number
            return (
                meta.get('slice_location') or 0,
                meta.get('instance_number', 0)
            )

    loaded.sort(key=sort_key)

    return loaded


def normalize_dicom_array(
    pixel_array: np.ndarray,
    window_center: Optional[float] = None,
    window_width: Optional[float] = None,
    window_mode: WindowMode = "auto",
    window_min: int = 1,
    window_max: int = 99
) -> np.ndarray:
    """
    Normalize DICOM pixel array to 0-255 range.

    Args:
        pixel_array: Raw pixel data
        window_center: Window center (level) from DICOM metadata
        window_width: Window width from DICOM metadata
        window_mode: "auto" for percentile-based, "manual" for absolute range
        window_min: Lower bound (percentile for auto, % of range for manual)
        window_max: Upper bound (percentile for auto, % of range for manual)

    Returns:
        Normalized uint8 array
    """
    arr = pixel_array.astype(np.float64)

    if window_mode == "auto":
        # Percentile-based windowing (ignore DICOM window settings)
        vmin = np.percentile(arr, window_min)
        vmax = np.percentile(arr, window_max)
    else:
        # Manual mode: use percentage of data range
        data_min = np.min(arr)
        data_max = np.max(arr)
        data_range = data_max - data_min
        vmin = data_min + (data_range * window_min / 100)
        vmax = data_min + (data_range * window_max / 100)

    # Clip and normalize
    arr = np.clip(arr, vmin, vmax)
    if vmax > vmin:
        arr = ((arr - vmin) / (vmax - vmin) * 255).astype(np.uint8)
    else:
        arr = np.zeros_like(arr, dtype=np.uint8)

    return arr


def process_dicom_series(
    files_data: List[Tuple[bytes, str]],
    window_mode: WindowMode = "auto",
    window_min: int = 1,
    window_max: int = 99
) -> Tuple[List[np.ndarray], dict]:
    """
    Process a series of DICOM files into normalized slices.

    Args:
        files_data: List of (file_content, filename) tuples
        window_mode: "auto" for percentile-based, "manual" for absolute range
        window_min: Lower bound (percentile for auto, % of range for manual)
        window_max: Upper bound (percentile for auto, % of range for manual)

    Returns:
        Tuple of (list of normalized 2D slices, metadata dict)
    """
    if not files_data:
        raise ValueError("No DICOM files provided")

    # Sort files using improved sorting
    sorted_files = sort_dicom_files(files_data)

    if not sorted_files:
        raise ValueError("No valid DICOM files could be loaded")

    slices = []
    first_meta = None

    for content, pixel_array, meta in sorted_files:
        if first_meta is None:
            first_meta = meta

        # Normalize each slice with user-defined window settings
        normalized = normalize_dicom_array(
            pixel_array,
            window_center=meta.get('window_center'),
            window_width=meta.get('window_width'),
            window_mode=window_mode,
            window_min=window_min,
            window_max=window_max
        )
        slices.append(normalized)

    metadata = {
        "num_slices": len(slices),
        "modality": first_meta.get('modality', 'Unknown'),
        "shape": [first_meta.get('rows', 0), first_meta.get('columns', 0), len(slices)],
        "file_type": "dicom",
        "window_mode": window_mode,
        "window_range": f"{window_min}-{window_max}",
    }

    return slices, metadata


def process_single_dicom(
    file_content: bytes,
    window_mode: WindowMode = "auto",
    window_min: int = 1,
    window_max: int = 99
) -> Tuple[List[np.ndarray], dict]:
    """
    Process a single DICOM file (for 2D images or cine loops).

    Args:
        file_content: Raw bytes of the DICOM file
        window_mode: "auto" for percentile-based, "manual" for absolute range
        window_min: Lower bound (percentile for auto, % of range for manual)
        window_max: Upper bound (percentile for auto, % of range for manual)

    Returns:
        Tuple of (list of normalized 2D slices, metadata dict)
    """
    file_obj = io.BytesIO(file_content)
    ds = pydicom.dcmread(file_obj)

    pixel_array = ds.pixel_array

    # Check if it's a multi-frame DICOM (cine loop)
    if pixel_array.ndim == 3:
        # Multi-frame: shape is (frames, rows, cols)
        frames = []
        for i in range(pixel_array.shape[0]):
            frame = pixel_array[i]
            frame = apply_modality_lut(frame, ds)
            normalized = normalize_dicom_array(
                frame,
                window_center=getattr(ds, 'WindowCenter', None),
                window_width=getattr(ds, 'WindowWidth', None),
                window_mode=window_mode,
                window_min=window_min,
                window_max=window_max
            )
            frames.append(normalized)

        metadata = {
            "num_slices": len(frames),
            "modality": str(getattr(ds, 'Modality', 'Unknown')),
            "shape": list(pixel_array.shape),
            "file_type": "dicom_multiframe",
            "window_mode": window_mode,
            "window_range": f"{window_min}-{window_max}",
        }
        return frames, metadata
    else:
        # Single frame - just return as a list with one element
        pixel_array = apply_modality_lut(pixel_array, ds)
        normalized = normalize_dicom_array(
            pixel_array,
            window_center=getattr(ds, 'WindowCenter', None),
            window_width=getattr(ds, 'WindowWidth', None),
            window_mode=window_mode,
            window_min=window_min,
            window_max=window_max
        )

        metadata = {
            "num_slices": 1,
            "modality": str(getattr(ds, 'Modality', 'Unknown')),
            "shape": list(pixel_array.shape),
            "file_type": "dicom_single",
            "window_mode": window_mode,
            "window_range": f"{window_min}-{window_max}",
        }
        return [normalized], metadata
