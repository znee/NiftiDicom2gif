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
    Sort DICOM files by instance number or spatial position.

    For 2D series (rotating MIP, time series), uses InstanceNumber.
    For 3D volume stacks, uses ImagePositionPatient when orientations are consistent.

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

    # Check available sorting keys
    has_instance = all(item[2].get('instance_number', 0) > 0 for item in loaded)
    has_position = all(item[2].get('computed_position') is not None for item in loaded)

    # Check if orientations are consistent (true 3D stack vs rotating/2D series)
    # For rotating MIP or 2D series, orientations vary - use InstanceNumber
    is_consistent_orientation = False
    if has_position and len(loaded) > 1:
        orientations = [
            tuple(item[2].get('image_orientation', []))
            for item in loaded
            if item[2].get('image_orientation')
        ]
        if orientations:
            # Check if all orientations are the same (within tolerance)
            first_orient = orientations[0]
            is_consistent_orientation = all(
                len(o) == len(first_orient) and
                all(abs(a - b) < 0.01 for a, b in zip(o, first_orient))
                for o in orientations
            )

    def sort_key(item):
        _, _, meta = item
        # For true 3D stacks (consistent orientation), use spatial position
        if has_position and is_consistent_orientation:
            return (meta.get('computed_position', 0),)
        # For 2D series (rotating MIP, time series), prefer InstanceNumber
        elif has_instance:
            return (meta.get('instance_number', 0),)
        elif has_position:
            return (meta.get('computed_position', 0),)
        else:
            # Fallback to slice_location, instance_number, then filename
            return (
                meta.get('slice_location') or 0,
                meta.get('instance_number', 0),
                meta.get('filename', '')
            )

    loaded.sort(key=sort_key)

    return loaded


def normalize_dicom_array(
    pixel_array: np.ndarray,
    dicom_window_center: Optional[float] = None,
    dicom_window_width: Optional[float] = None,
    window_mode: WindowMode = "auto",
    user_window_width: int = 98,
    user_window_level: int = 50
) -> np.ndarray:
    """
    Normalize DICOM pixel array to 0-255 range.

    Args:
        pixel_array: Raw pixel data
        dicom_window_center: Window center (level) from DICOM metadata
        dicom_window_width: Window width from DICOM metadata
        window_mode: "auto" for percentile-based, "manual" for absolute HU values
        user_window_width: User-specified window width (percentile range for auto, HU for manual)
        user_window_level: User-specified window level (percentile center for auto, HU for manual)

    Returns:
        Normalized uint8 array
    """
    arr = pixel_array.astype(np.float64)

    if window_mode == "auto":
        # Percentile-based windowing (works with any modality)
        # Use width/level as percentiles
        half_width = user_window_width / 2
        lower_pct = max(0, user_window_level - half_width)
        upper_pct = min(100, user_window_level + half_width)
        vmin = np.percentile(arr, lower_pct)
        vmax = np.percentile(arr, upper_pct)
    else:
        # Manual mode: Use absolute window width/level (HU for CT)
        vmin = user_window_level - user_window_width / 2
        vmax = user_window_level + user_window_width / 2

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
    window_width: int = 98,
    window_level: int = 50
) -> Tuple[List[np.ndarray], dict]:
    """
    Process a series of DICOM files into normalized slices.

    Args:
        files_data: List of (file_content, filename) tuples
        window_mode: "auto" for percentile-based, "manual" for absolute HU values
        window_width: Window width (percentile range for auto, HU for manual)
        window_level: Window level (percentile center for auto, HU for manual)

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
            dicom_window_center=meta.get('window_center'),
            dicom_window_width=meta.get('window_width'),
            window_mode=window_mode,
            user_window_width=window_width,
            user_window_level=window_level
        )
        slices.append(normalized)

    metadata = {
        "num_slices": len(slices),
        "modality": first_meta.get('modality', 'Unknown'),
        "shape": [first_meta.get('rows', 0), first_meta.get('columns', 0), len(slices)],
        "file_type": "dicom",
        "window_mode": window_mode,
        "window_wl": f"W:{window_width} L:{window_level}",
    }

    return slices, metadata


def process_single_dicom(
    file_content: bytes,
    window_mode: WindowMode = "auto",
    window_width: int = 98,
    window_level: int = 50
) -> Tuple[List[np.ndarray], dict]:
    """
    Process a single DICOM file (for 2D images or cine loops).

    Args:
        file_content: Raw bytes of the DICOM file
        window_mode: "auto" for percentile-based, "manual" for absolute HU values
        window_width: Window width (percentile range for auto, HU for manual)
        window_level: Window level (percentile center for auto, HU for manual)

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
                dicom_window_center=getattr(ds, 'WindowCenter', None),
                dicom_window_width=getattr(ds, 'WindowWidth', None),
                window_mode=window_mode,
                user_window_width=window_width,
                user_window_level=window_level
            )
            frames.append(normalized)

        metadata = {
            "num_slices": len(frames),
            "modality": str(getattr(ds, 'Modality', 'Unknown')),
            "shape": list(pixel_array.shape),
            "file_type": "dicom_multiframe",
            "window_mode": window_mode,
            "window_wl": f"W:{window_width} L:{window_level}",
        }
        return frames, metadata
    else:
        # Single frame - just return as a list with one element
        pixel_array = apply_modality_lut(pixel_array, ds)
        normalized = normalize_dicom_array(
            pixel_array,
            dicom_window_center=getattr(ds, 'WindowCenter', None),
            dicom_window_width=getattr(ds, 'WindowWidth', None),
            window_mode=window_mode,
            user_window_width=window_width,
            user_window_level=window_level
        )

        metadata = {
            "num_slices": 1,
            "modality": str(getattr(ds, 'Modality', 'Unknown')),
            "shape": list(pixel_array.shape),
            "file_type": "dicom_single",
            "window_mode": window_mode,
            "window_wl": f"W:{window_width} L:{window_level}",
        }
        return [normalized], metadata
