"""
NIfTI file processing service.
Converts 3D NIfTI volumes to 2D slice sequences for GIF generation.
Supports both 'volume' mode (slicing through 3D) and 'series' mode (4D time series).
"""
from typing import Literal, Tuple, List

import numpy as np
import nibabel as nib
from nibabel.orientations import aff2axcodes, axcodes2ornt, ornt_transform, apply_orientation

from utils.image_ops import resize_slice_for_aspect_ratio


Orientation = Literal["axial", "coronal", "sagittal"]
Mode = Literal["volume", "series"]
WindowMode = Literal["auto", "manual"]


def get_voxel_spacing(affine: np.ndarray) -> Tuple[float, float, float]:
    """
    Extract voxel spacing from NIfTI affine matrix.

    Args:
        affine: 4x4 affine transformation matrix

    Returns:
        Tuple of (x_spacing, y_spacing, z_spacing) in mm
    """
    # Voxel spacing is the norm of each column of the rotation/scale part
    spacing = np.sqrt(np.sum(affine[:3, :3] ** 2, axis=0))
    return float(spacing[0]), float(spacing[1]), float(spacing[2])


def load_nifti_from_path(file_path: str) -> Tuple[np.ndarray, dict, np.ndarray, Tuple[float, float, float]]:
    """
    Load NIfTI file from file path.

    Args:
        file_path: Path to the NIfTI file

    Returns:
        Tuple of (data array, metadata dict, affine matrix, voxel_spacing)
        voxel_spacing is (x_spacing, y_spacing, z_spacing) in mm
    """
    img = nib.load(file_path)
    # Use float32 instead of float64 for faster processing and lower memory usage
    # This is sufficient precision for medical imaging visualization
    data = img.get_fdata(dtype=np.float32)
    voxel_spacing = get_voxel_spacing(img.affine)

    metadata = {
        "shape": list(data.shape),
        "ndim": data.ndim,
        "dtype": str(data.dtype),
        "is_4d": data.ndim == 4,
        "num_timepoints": data.shape[3] if data.ndim == 4 else 1,
        "voxel_spacing_mm": list(voxel_spacing),
    }

    return data, metadata, img.affine, voxel_spacing


def reorient_to_ras(data: np.ndarray, affine: np.ndarray) -> np.ndarray:
    """
    Reorient data to RAS+ orientation for consistent slicing.

    Args:
        data: 3D or 4D numpy array
        affine: Affine transformation matrix

    Returns:
        Reoriented data array
    """
    # Get current orientation
    current_ornt = nib.orientations.io_orientation(affine)
    # Target RAS orientation
    ras_ornt = axcodes2ornt(('R', 'A', 'S'))

    # Handle 4D data - reorient each volume
    if data.ndim == 4:
        transform = ornt_transform(current_ornt, ras_ornt)
        reoriented_volumes = []
        for t in range(data.shape[3]):
            vol = apply_orientation(data[:, :, :, t], transform)
            reoriented_volumes.append(vol)
        return np.stack(reoriented_volumes, axis=3)
    else:
        transform = ornt_transform(current_ornt, ras_ornt)
        return apply_orientation(data, transform)


def extract_slices_volume(
    data: np.ndarray,
    orientation: Orientation = "axial",
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0)
) -> List[np.ndarray]:
    """
    Extract 2D slices from a 3D volume along specified orientation.
    For 4D data, uses the first timepoint.
    Applies aspect ratio correction based on voxel spacing.

    Radiological convention (standard medical imaging display):
    - Axial: viewed from below, patient's right on viewer's left, anterior up
    - Coronal: viewed from front, patient's right on viewer's left, superior up
    - Sagittal: viewed from patient's right, anterior on viewer's left, superior up

    Note: Slices are returned in natural order. Use "Reverse" control to change direction.

    Args:
        data: 3D or 4D numpy array (in RAS orientation: x=R→L, y=P→A, z=I→S)
        orientation: Slice orientation - "axial", "coronal", or "sagittal"
        voxel_spacing: (x_spacing, y_spacing, z_spacing) in mm

    Returns:
        List of 2D numpy arrays (slices) with correct aspect ratio
    """
    # For 4D data in volume mode, use first timepoint
    if data.ndim == 4:
        data = data[:, :, :, 0]

    if data.ndim != 3:
        raise ValueError(f"Expected 3D data, got {data.ndim}D")

    x_sp, y_sp, z_sp = voxel_spacing
    slices = []

    if orientation == "axial":
        # Axial: slice perpendicular to z (S-I axis)
        # RAS data[x,y,z]: x=R→L, y=P→A, z=I→S
        # Radiological: R on left, A at top
        for i in range(data.shape[2]):
            slice_2d = data[:, :, i]  # shape (x, y)
            slice_2d = slice_2d.T  # now (y, x) - rows=y(P→A), cols=x(R→L)
            slice_2d = np.flipud(slice_2d)  # rows now A→P (A at top)
            # cols are R→L, for radiological R on left, this is correct
            slice_2d = resize_slice_for_aspect_ratio(slice_2d, x_sp, y_sp)
            slices.append(slice_2d)
    elif orientation == "coronal":
        # Coronal: slice perpendicular to y (A-P axis)
        # RAS data[x,y,z]: x=R→L, y=P→A, z=I→S
        # Radiological: R on left, S on top
        for i in range(data.shape[1]):
            slice_2d = data[:, i, :]  # shape (x, z)
            slice_2d = slice_2d.T  # now (z, x) - rows=z(I→S), cols=x(R→L)
            slice_2d = np.flipud(slice_2d)  # rows now S→I (S at top)
            # cols are R→L, for radiological R on left, this is correct
            slice_2d = resize_slice_for_aspect_ratio(slice_2d, x_sp, z_sp)
            slices.append(slice_2d)
    elif orientation == "sagittal":
        # Sagittal: slice perpendicular to x (R-L axis)
        # RAS data[x,y,z]: x=R→L, y=P→A, z=I→S
        # Radiological: A on left, S on top (viewing from patient's right side)
        for i in range(data.shape[0]):
            slice_2d = data[i, :, :]  # shape (y, z)
            slice_2d = slice_2d.T  # now (z, y) - rows=z(I→S), cols=y(P→A)
            slice_2d = np.flipud(slice_2d)  # rows now S→I (S at top)
            slice_2d = np.fliplr(slice_2d)  # cols now A→P (A on left)
            slice_2d = resize_slice_for_aspect_ratio(slice_2d, y_sp, z_sp)
            slices.append(slice_2d)
    else:
        raise ValueError(f"Unknown orientation: {orientation}")

    return slices


def extract_slices_series(
    data: np.ndarray,
    orientation: Orientation = "axial",
    slice_index: int = None,
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0)
) -> List[np.ndarray]:
    """
    Extract 2D slices from a 4D time series (animate over time dimension).
    Takes a single slice position and extracts it across all timepoints.
    Applies aspect ratio correction based on voxel spacing.

    Uses same radiological convention as extract_slices_volume.

    Args:
        data: 4D numpy array (x, y, z, time) in RAS orientation
        orientation: Slice orientation for selecting which plane
        slice_index: Which slice to extract (default: middle slice)
        voxel_spacing: (x_spacing, y_spacing, z_spacing) in mm

    Returns:
        List of 2D numpy arrays (one per timepoint) with correct aspect ratio
    """
    if data.ndim != 4:
        raise ValueError(f"Series mode requires 4D data, got {data.ndim}D. Use 'volume' mode instead.")

    num_timepoints = data.shape[3]
    x_sp, y_sp, z_sp = voxel_spacing
    slices = []

    # Determine slice index (default to middle)
    if orientation == "axial":
        max_idx = data.shape[2]
        idx = slice_index if slice_index is not None else max_idx // 2
        idx = min(max(0, idx), max_idx - 1)
        for t in range(num_timepoints):
            slice_2d = data[:, :, idx, t]  # shape (x, y)
            slice_2d = slice_2d.T  # now (y, x)
            slice_2d = np.flipud(slice_2d)  # A at top
            slice_2d = resize_slice_for_aspect_ratio(slice_2d, x_sp, y_sp)
            slices.append(slice_2d)
    elif orientation == "coronal":
        max_idx = data.shape[1]
        idx = slice_index if slice_index is not None else max_idx // 2
        idx = min(max(0, idx), max_idx - 1)
        for t in range(num_timepoints):
            slice_2d = data[:, idx, :, t]  # shape (x, z)
            slice_2d = slice_2d.T  # now (z, x)
            slice_2d = np.flipud(slice_2d)  # S at top
            slice_2d = resize_slice_for_aspect_ratio(slice_2d, x_sp, z_sp)
            slices.append(slice_2d)
    elif orientation == "sagittal":
        max_idx = data.shape[0]
        idx = slice_index if slice_index is not None else max_idx // 2
        idx = min(max(0, idx), max_idx - 1)
        for t in range(num_timepoints):
            slice_2d = data[idx, :, :, t]  # shape (y, z)
            slice_2d = slice_2d.T  # now (z, y)
            slice_2d = np.flipud(slice_2d)  # S at top
            slice_2d = np.fliplr(slice_2d)  # A on left
            slice_2d = resize_slice_for_aspect_ratio(slice_2d, y_sp, z_sp)
            slices.append(slice_2d)
    else:
        raise ValueError(f"Unknown orientation: {orientation}")

    return slices


def normalize_slices(
    slices: List[np.ndarray],
    window_mode: WindowMode = "auto",
    window_width: int = 400,
    window_level: int = 40,
    sample_size: int = 100000
) -> List[np.ndarray]:
    """
    Normalize slice values to 0-255 range for image conversion.
    Uses sampling for memory efficiency on large volumes.

    Args:
        slices: List of 2D numpy arrays
        window_mode: "auto" for percentile-based, "manual" for absolute HU values
        window_width: Window width (range) - for manual mode, absolute HU; for auto, percentile range
        window_level: Window level (center) - for manual mode, absolute HU; for auto, percentile center
        sample_size: Max number of pixels to sample for percentile calculation

    Returns:
        List of normalized 2D arrays (uint8)
    """
    if not slices:
        return []

    # Sample pixels for percentile/range calculation (memory efficient)
    total_pixels = sum(s.size for s in slices)
    if total_pixels <= sample_size:
        all_values = np.concatenate([s.ravel() for s in slices])
    else:
        # Random sampling across slices
        samples_per_slice = max(1, sample_size // len(slices))
        sampled = []
        for s in slices:
            flat = s.ravel()
            if len(flat) <= samples_per_slice:
                sampled.append(flat)
            else:
                indices = np.random.choice(len(flat), samples_per_slice, replace=False)
                sampled.append(flat[indices])
        all_values = np.concatenate(sampled)

    if window_mode == "auto":
        # Percentile-based windowing (works with any modality including MRI)
        # Use width/level as percentiles: level is center percentile, width is range
        # Default auto: level=50 (median), width=98 (1st to 99th percentile)
        half_width = window_width / 2
        lower_pct = max(0, window_level - half_width)
        upper_pct = min(100, window_level + half_width)
        vmin = np.percentile(all_values, lower_pct)
        vmax = np.percentile(all_values, upper_pct)
    else:
        # Manual mode: Use absolute window width/level (HU for CT)
        # vmin = level - width/2, vmax = level + width/2
        vmin = window_level - window_width / 2
        vmax = window_level + window_width / 2

    normalized = []
    for s in slices:
        clipped = np.clip(s, vmin, vmax)
        if vmax > vmin:
            norm = ((clipped - vmin) / (vmax - vmin) * 255).astype(np.uint8)
        else:
            norm = np.zeros_like(clipped, dtype=np.uint8)
        normalized.append(norm)

    return normalized


def process_nifti_from_path(
    file_path: str,
    mode: Mode = "volume",
    orientation: Orientation = "axial",
    slice_index: int = None,
    window_mode: WindowMode = "auto",
    window_width: int = 98,
    window_level: int = 50
) -> Tuple[List[np.ndarray], dict]:
    """
    Full pipeline from file path: load NIfTI, extract and normalize slices.

    Args:
        file_path: Path to the NIfTI file
        mode: "volume" (slice through 3D) or "series" (animate 4D over time)
        orientation: Slice orientation
        slice_index: For series mode, which slice to show (default: middle)
        window_mode: "auto" for percentile-based, "manual" for absolute HU values
        window_width: Window width (percentile range for auto, HU range for manual)
        window_level: Window level (percentile center for auto, HU center for manual)

    Returns:
        Tuple of (list of normalized 2D slices, metadata dict)
    """
    data, metadata, affine, voxel_spacing = load_nifti_from_path(file_path)

    # Reorient to RAS for consistent slicing
    try:
        data = reorient_to_ras(data, affine)
        metadata["reoriented"] = True
    except Exception:
        metadata["reoriented"] = False

    # Extract slices based on mode with aspect ratio correction
    if mode == "series" and data.ndim == 4:
        slices = extract_slices_series(data, orientation, slice_index, voxel_spacing)
        metadata["mode"] = "series"
        metadata["slice_index"] = slice_index if slice_index is not None else data.shape[2] // 2
    else:
        # Default to volume mode (or if 3D data with series mode requested)
        slices = extract_slices_volume(data, orientation, voxel_spacing)
        metadata["mode"] = "volume"
        if mode == "series" and data.ndim != 4:
            metadata["mode_fallback"] = "3D data - using volume mode"

    normalized = normalize_slices(slices, window_mode, window_width, window_level)

    metadata["num_slices"] = len(normalized)
    metadata["orientation"] = orientation
    metadata["file_type"] = "nifti"
    metadata["window_mode"] = window_mode
    metadata["window_wl"] = f"W:{window_width} L:{window_level}"

    return normalized, metadata
