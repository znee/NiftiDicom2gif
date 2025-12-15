"""
NIfTI file processing service.
Converts 3D NIfTI volumes to 2D slice sequences for GIF generation.
Supports both 'volume' mode (slicing through 3D) and 'series' mode (4D time series).
"""
from typing import Literal, Tuple, List

import numpy as np
import nibabel as nib
from nibabel.orientations import aff2axcodes, axcodes2ornt, ornt_transform, apply_orientation


Orientation = Literal["axial", "coronal", "sagittal"]
Mode = Literal["volume", "series"]
WindowMode = Literal["auto", "manual"]


def load_nifti_from_path(file_path: str) -> Tuple[np.ndarray, dict, np.ndarray]:
    """
    Load NIfTI file from file path.

    Args:
        file_path: Path to the NIfTI file

    Returns:
        Tuple of (data array, metadata dict, affine matrix)
    """
    img = nib.load(file_path)
    data = img.get_fdata()

    metadata = {
        "shape": list(data.shape),
        "ndim": data.ndim,
        "dtype": str(data.dtype),
        "is_4d": data.ndim == 4,
        "num_timepoints": data.shape[3] if data.ndim == 4 else 1,
    }

    return data, metadata, img.affine


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
    orientation: Orientation = "axial"
) -> List[np.ndarray]:
    """
    Extract 2D slices from a 3D volume along specified orientation.
    For 4D data, uses the first timepoint.

    Args:
        data: 3D or 4D numpy array
        orientation: Slice orientation - "axial", "coronal", or "sagittal"

    Returns:
        List of 2D numpy arrays (slices)
    """
    # For 4D data in volume mode, use first timepoint
    if data.ndim == 4:
        data = data[:, :, :, 0]

    if data.ndim != 3:
        raise ValueError(f"Expected 3D data, got {data.ndim}D")

    slices = []

    if orientation == "axial":
        # Slices along z-axis (superior-inferior)
        for i in range(data.shape[2]):
            slice_2d = data[:, :, i]
            slices.append(np.rot90(slice_2d))
    elif orientation == "coronal":
        # Slices along y-axis (anterior-posterior)
        for i in range(data.shape[1]):
            slice_2d = data[:, i, :]
            slices.append(np.rot90(slice_2d))
    elif orientation == "sagittal":
        # Slices along x-axis (left-right)
        for i in range(data.shape[0]):
            slice_2d = data[i, :, :]
            slices.append(np.rot90(slice_2d))
    else:
        raise ValueError(f"Unknown orientation: {orientation}")

    return slices


def extract_slices_series(
    data: np.ndarray,
    orientation: Orientation = "axial",
    slice_index: int = None
) -> List[np.ndarray]:
    """
    Extract 2D slices from a 4D time series (animate over time dimension).
    Takes a single slice position and extracts it across all timepoints.

    Args:
        data: 4D numpy array (x, y, z, time)
        orientation: Slice orientation for selecting which plane
        slice_index: Which slice to extract (default: middle slice)

    Returns:
        List of 2D numpy arrays (one per timepoint)
    """
    if data.ndim != 4:
        raise ValueError(f"Series mode requires 4D data, got {data.ndim}D. Use 'volume' mode instead.")

    num_timepoints = data.shape[3]
    slices = []

    # Determine slice index (default to middle)
    if orientation == "axial":
        max_idx = data.shape[2]
        idx = slice_index if slice_index is not None else max_idx // 2
        idx = min(max(0, idx), max_idx - 1)
        for t in range(num_timepoints):
            slice_2d = data[:, :, idx, t]
            slices.append(np.rot90(slice_2d))
    elif orientation == "coronal":
        max_idx = data.shape[1]
        idx = slice_index if slice_index is not None else max_idx // 2
        idx = min(max(0, idx), max_idx - 1)
        for t in range(num_timepoints):
            slice_2d = data[:, idx, :, t]
            slices.append(np.rot90(slice_2d))
    elif orientation == "sagittal":
        max_idx = data.shape[0]
        idx = slice_index if slice_index is not None else max_idx // 2
        idx = min(max(0, idx), max_idx - 1)
        for t in range(num_timepoints):
            slice_2d = data[idx, :, :, t]
            slices.append(np.rot90(slice_2d))
    else:
        raise ValueError(f"Unknown orientation: {orientation}")

    return slices


def normalize_slices(
    slices: List[np.ndarray],
    window_mode: WindowMode = "auto",
    window_min: int = 1,
    window_max: int = 99,
    sample_size: int = 100000
) -> List[np.ndarray]:
    """
    Normalize slice values to 0-255 range for image conversion.
    Uses sampling for memory efficiency on large volumes.

    Args:
        slices: List of 2D numpy arrays
        window_mode: "auto" for percentile-based, "manual" for absolute range
        window_min: Lower bound (percentile for auto, % of data range for manual)
        window_max: Upper bound (percentile for auto, % of data range for manual)
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
        # Percentile-based windowing
        vmin = np.percentile(all_values, window_min)
        vmax = np.percentile(all_values, window_max)
    else:
        # Manual mode: window_min/max are percentages of the data range
        data_min = np.min(all_values)
        data_max = np.max(all_values)
        data_range = data_max - data_min
        vmin = data_min + (data_range * window_min / 100)
        vmax = data_min + (data_range * window_max / 100)

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
    window_min: int = 1,
    window_max: int = 99
) -> Tuple[List[np.ndarray], dict]:
    """
    Full pipeline from file path: load NIfTI, extract and normalize slices.

    Args:
        file_path: Path to the NIfTI file
        mode: "volume" (slice through 3D) or "series" (animate 4D over time)
        orientation: Slice orientation
        slice_index: For series mode, which slice to show (default: middle)
        window_mode: "auto" for percentile-based, "manual" for absolute range
        window_min: Lower bound (percentile for auto, % of range for manual)
        window_max: Upper bound (percentile for auto, % of range for manual)

    Returns:
        Tuple of (list of normalized 2D slices, metadata dict)
    """
    data, metadata, affine = load_nifti_from_path(file_path)

    # Reorient to RAS for consistent slicing
    try:
        data = reorient_to_ras(data, affine)
        metadata["reoriented"] = True
    except Exception:
        metadata["reoriented"] = False

    # Extract slices based on mode
    if mode == "series" and data.ndim == 4:
        slices = extract_slices_series(data, orientation, slice_index)
        metadata["mode"] = "series"
        metadata["slice_index"] = slice_index if slice_index is not None else data.shape[2] // 2
    else:
        # Default to volume mode (or if 3D data with series mode requested)
        slices = extract_slices_volume(data, orientation)
        metadata["mode"] = "volume"
        if mode == "series" and data.ndim != 4:
            metadata["mode_fallback"] = "3D data - using volume mode"

    normalized = normalize_slices(slices, window_mode, window_min, window_max)

    metadata["num_slices"] = len(normalized)
    metadata["orientation"] = orientation
    metadata["file_type"] = "nifti"
    metadata["window_mode"] = window_mode
    metadata["window_range"] = f"{window_min}-{window_max}"

    return normalized, metadata
