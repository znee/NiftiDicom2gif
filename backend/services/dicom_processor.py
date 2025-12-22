"""
DICOM file processing service.
Converts DICOM series (multiple 2D images) to slice sequences for GIF generation.
Supports both 2D series (rotating MIP, time series) and 3D volume reconstruction.
"""
import io
import logging
from typing import List, Tuple, Optional, Literal

import numpy as np
import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut

from utils.image_ops import resize_slice_for_aspect_ratio

WindowMode = Literal["auto", "manual"]
Orientation = Literal["axial", "coronal", "sagittal"]

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

    # Time-based attributes for DSA, angiography, and other time series
    if hasattr(ds, 'AcquisitionTime'):
        metadata['acquisition_time'] = str(ds.AcquisitionTime)
    if hasattr(ds, 'ContentTime'):
        metadata['content_time'] = str(ds.ContentTime)
    if hasattr(ds, 'AcquisitionNumber'):
        metadata['acquisition_number'] = int(ds.AcquisitionNumber)
    if hasattr(ds, 'TemporalPositionIdentifier'):
        metadata['temporal_position'] = int(ds.TemporalPositionIdentifier)
    if hasattr(ds, 'FrameTime'):
        metadata['frame_time'] = float(ds.FrameTime)
    # Series number can help distinguish separate acquisitions
    if hasattr(ds, 'SeriesNumber'):
        metadata['series_number'] = int(ds.SeriesNumber)

    # Extract position and orientation for proper sorting
    if hasattr(ds, 'ImagePositionPatient'):
        metadata['image_position'] = [float(x) for x in ds.ImagePositionPatient]
    if hasattr(ds, 'ImageOrientationPatient'):
        metadata['image_orientation'] = [float(x) for x in ds.ImageOrientationPatient]

    # Extract pixel spacing information
    if hasattr(ds, 'PixelSpacing'):
        metadata['pixel_spacing'] = [float(x) for x in ds.PixelSpacing]  # [row_spacing, col_spacing]
    if hasattr(ds, 'SliceThickness'):
        metadata['slice_thickness'] = float(ds.SliceThickness)
    if hasattr(ds, 'SpacingBetweenSlices'):
        metadata['spacing_between_slices'] = float(ds.SpacingBetweenSlices)

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


def parse_dicom_time(time_str: str) -> float:
    """
    Parse DICOM time string to a sortable float value.
    DICOM time format: HHMMSS.FFFFFF (fractional seconds optional)

    Args:
        time_str: Time string in DICOM format

    Returns:
        Float value representing time in seconds
    """
    try:
        time_str = str(time_str).strip()
        # Handle fractional seconds
        if '.' in time_str:
            main_part, frac = time_str.split('.')
            frac = float('0.' + frac)
        else:
            main_part = time_str
            frac = 0.0

        # Pad to 6 characters (HHMMSS)
        main_part = main_part.ljust(6, '0')[:6]

        hours = int(main_part[0:2])
        minutes = int(main_part[2:4])
        seconds = int(main_part[4:6])

        return hours * 3600 + minutes * 60 + seconds + frac
    except Exception:
        return 0.0


def sort_dicom_files(
    files_data: List[Tuple[bytes, str]]
) -> List[Tuple[bytes, np.ndarray, dict]]:
    """
    Sort DICOM files by the most appropriate attribute.

    Priority for time-based series (DSA, angiography, cine):
    1. AcquisitionNumber (if varying)
    2. AcquisitionTime / ContentTime
    3. TemporalPositionIdentifier
    4. InstanceNumber

    Priority for 3D volume stacks:
    1. ImagePositionPatient (spatial position along normal)

    Fallback:
    - InstanceNumber, SliceLocation, filename

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
    has_acq_time = all(item[2].get('acquisition_time') for item in loaded)
    has_content_time = all(item[2].get('content_time') for item in loaded)
    has_acq_number = all(item[2].get('acquisition_number') is not None for item in loaded)
    has_temporal_pos = all(item[2].get('temporal_position') is not None for item in loaded)

    # Check if acquisition numbers vary (indicates time series)
    acq_numbers_vary = False
    if has_acq_number and len(loaded) > 1:
        acq_nums = [item[2].get('acquisition_number', 0) for item in loaded]
        acq_numbers_vary = len(set(acq_nums)) > 1

    # Check if orientations are consistent (true 3D stack vs rotating/2D series)
    is_consistent_orientation = False
    if has_position and len(loaded) > 1:
        orientations = [
            tuple(item[2].get('image_orientation', []))
            for item in loaded
            if item[2].get('image_orientation')
        ]
        if orientations:
            first_orient = orientations[0]
            is_consistent_orientation = all(
                len(o) == len(first_orient) and
                all(abs(a - b) < 0.01 for a, b in zip(o, first_orient))
                for o in orientations
            )

    # Check if times vary (indicates time series like DSA)
    times_vary = False
    if has_acq_time or has_content_time:
        time_key = 'acquisition_time' if has_acq_time else 'content_time'
        times = [parse_dicom_time(item[2].get(time_key, '')) for item in loaded]
        times_vary = len(set(times)) > 1

    def sort_key(item):
        _, _, meta = item

        # For true 3D stacks (consistent orientation), use spatial position
        if has_position and is_consistent_orientation:
            return (0, meta.get('computed_position', 0), 0, 0, '')

        # For time-based series (DSA, angiography) - prioritize time ordering
        if acq_numbers_vary:
            # AcquisitionNumber is the most reliable for time series
            return (1, meta.get('acquisition_number', 0), 0, 0, '')

        if has_temporal_pos:
            # TemporalPositionIdentifier explicitly indicates time ordering
            return (2, meta.get('temporal_position', 0), 0, 0, '')

        if times_vary and has_acq_time:
            # Use acquisition time for time-based sorting
            return (3, parse_dicom_time(meta.get('acquisition_time', '')), 0, 0, '')

        if times_vary and has_content_time:
            # Fallback to content time
            return (4, parse_dicom_time(meta.get('content_time', '')), 0, 0, '')

        # For 2D series without time info, prefer InstanceNumber
        if has_instance:
            return (5, meta.get('instance_number', 0), 0, 0, '')

        if has_position:
            return (6, meta.get('computed_position', 0), 0, 0, '')

        # Ultimate fallback
        return (
            7,
            meta.get('slice_location') or 0,
            meta.get('instance_number', 0),
            0,
            meta.get('filename', '')
        )

    loaded.sort(key=sort_key)

    return loaded


def detect_acquisition_plane(orientation: List[float]) -> str:
    """
    Detect the acquisition plane from ImageOrientationPatient.

    Args:
        orientation: 6-element list [row_x, row_y, row_z, col_x, col_y, col_z]

    Returns:
        "axial", "coronal", or "sagittal"
    """
    row_cosine = np.array(orientation[:3])
    col_cosine = np.array(orientation[3:])
    normal = np.cross(row_cosine, col_cosine)

    abs_normal = np.abs(normal)
    max_idx = np.argmax(abs_normal)

    # Normal direction indicates acquisition plane:
    # X (L-R) dominant -> Sagittal
    # Y (A-P) dominant -> Coronal
    # Z (S-I) dominant -> Axial
    planes = ["sagittal", "coronal", "axial"]
    return planes[max_idx]


def compute_voxel_spacing(
    sorted_files: List[Tuple[bytes, np.ndarray, dict]]
) -> Tuple[float, float, float]:
    """
    Compute voxel spacing (row, col, slice) from DICOM metadata.

    Args:
        sorted_files: Sorted list of (content, pixel_array, metadata) tuples

    Returns:
        Tuple of (row_spacing, col_spacing, slice_spacing) in mm
    """
    first_meta = sorted_files[0][2]

    # Get in-plane pixel spacing
    pixel_spacing = first_meta.get('pixel_spacing', [1.0, 1.0])
    row_spacing = pixel_spacing[0]
    col_spacing = pixel_spacing[1]

    # Calculate slice spacing from positions if available
    slice_spacing = first_meta.get('slice_thickness', 1.0)

    if len(sorted_files) > 1:
        first_pos = first_meta.get('image_position')
        second_meta = sorted_files[1][2]
        second_pos = second_meta.get('image_position')

        if first_pos and second_pos:
            # Calculate actual spacing between slices
            pos1 = np.array(first_pos)
            pos2 = np.array(second_pos)
            slice_spacing = float(np.linalg.norm(pos2 - pos1))

    return row_spacing, col_spacing, slice_spacing


def get_orientation_transforms(orientation: List[float]) -> Tuple[bool, bool, int]:
    """
    Determine the transforms needed to display DICOM slice in radiological convention.

    DICOM ImageOrientationPatient gives row and column direction cosines.
    - Row cosine: direction of increasing column index (left-to-right in displayed image)
    - Col cosine: direction of increasing row index (top-to-bottom in displayed image)

    Standard radiological conventions:
    - Axial: Patient's Right on viewer's Left, Anterior at top (viewed from feet)
    - Coronal: Patient's Right on viewer's Left, Superior at top (viewed from front)
    - Sagittal: Anterior on viewer's Left, Superior at top (viewed from patient's right)

    LPS coordinate system used by DICOM:
    - X: Right (+) to Left (-)  [positive = left side of patient]
    - Y: Anterior (+) to Posterior (-) [positive = back of patient]
    - Z: Inferior (+) to Superior (-) [positive = head]

    Note: Some DICOM uses LPS, others RAS. We check the actual direction cosines.

    Args:
        orientation: 6-element list [row_x, row_y, row_z, col_x, col_y, col_z]

    Returns:
        Tuple of (flip_horizontal, flip_vertical, rotation_90_count)
    """
    row_cosine = np.array(orientation[:3])  # Direction of increasing column (horiz)
    col_cosine = np.array(orientation[3:])  # Direction of increasing row (vert)

    # Determine acquisition plane from normal vector
    normal = np.cross(row_cosine, col_cosine)
    abs_normal = np.abs(normal)
    plane_idx = np.argmax(abs_normal)  # 0=sagittal, 1=coronal, 2=axial

    flip_h = False
    flip_v = False

    # Get the actual direction each axis represents
    # For each image axis, find which anatomical direction it most closely aligns with
    row_dominant_axis = np.argmax(np.abs(row_cosine))  # 0=X(L/R), 1=Y(A/P), 2=Z(I/S)
    col_dominant_axis = np.argmax(np.abs(col_cosine))

    # The sign tells us which direction it points
    # In standard DICOM (LPS): +X=Left, +Y=Posterior, +Z=Superior
    row_direction = row_cosine[row_dominant_axis]  # positive/negative
    col_direction = col_cosine[col_dominant_axis]

    if plane_idx == 2:  # Axial plane (normal along Z/Superior-Inferior)
        # Standard: R on left, A at top
        # Row axis should be L-R: for R on left, we want row to go L->R (positive X)
        # Col axis should be A-P: for A at top, we want col to go P->A (negative Y)
        if row_dominant_axis == 0:  # Row is along X (Left-Right)
            if row_direction < 0:  # Points Right (decreasing X), flip to get R on left
                flip_h = True
        if col_dominant_axis == 1:  # Col is along Y (Anterior-Posterior)
            if col_direction > 0:  # Points Posterior, flip to get A at top
                flip_v = True

    elif plane_idx == 1:  # Coronal plane (normal along Y/Anterior-Posterior)
        # Standard: R on left, S at top
        # Row axis should be L-R: for R on left, we want row to go L->R (positive X)
        # Col axis should be S-I: for S at top, we want col to go I->S (positive Z)
        if row_dominant_axis == 0:  # Row is along X (Left-Right)
            if row_direction < 0:  # Points Right, flip to get R on left
                flip_h = True
        if col_dominant_axis == 2:  # Col is along Z (Superior-Inferior)
            if col_direction < 0:  # Points Inferior, flip to get S at top
                flip_v = True

    elif plane_idx == 0:  # Sagittal plane (normal along X/Left-Right)
        # Standard: A on left, S at top
        # Row axis should be A-P: for A on left, we want row to go P->A (negative Y)
        # Col axis should be S-I: for S at top, we want col to go I->S (positive Z)
        if row_dominant_axis == 1:  # Row is along Y (Anterior-Posterior)
            if row_direction > 0:  # Points Posterior, flip to get A on left
                flip_h = True
        if col_dominant_axis == 2:  # Col is along Z (Superior-Inferior)
            if col_direction < 0:  # Points Inferior, flip to get S at top
                flip_v = True

    return flip_h, flip_v, 0


def build_3d_volume(
    sorted_files: List[Tuple[bytes, np.ndarray, dict]]
) -> Tuple[np.ndarray, dict, str, Tuple[float, float, float], Tuple[bool, bool, int]]:
    """
    Build a 3D volume from sorted DICOM slices.

    Args:
        sorted_files: Sorted list of (content, pixel_array, metadata) tuples

    Returns:
        Tuple of (3D volume array, metadata dict, acquisition_plane, voxel_spacing, orientation_transforms)
        voxel_spacing is (row_spacing, col_spacing, slice_spacing) in mm
        orientation_transforms is (flip_h, flip_v, rot90_count) for display
    """
    if not sorted_files:
        raise ValueError("No DICOM files to build volume")

    first_meta = sorted_files[0][2]

    # Detect acquisition plane from first slice
    acquisition_plane = "axial"  # default
    orientation_transforms = (False, False, 0)

    if first_meta.get('image_orientation'):
        acquisition_plane = detect_acquisition_plane(first_meta['image_orientation'])
        orientation_transforms = get_orientation_transforms(first_meta['image_orientation'])

    # Compute voxel spacing
    voxel_spacing = compute_voxel_spacing(sorted_files)

    # Stack slices into 3D volume
    slices_2d = [item[1] for item in sorted_files]
    volume = np.stack(slices_2d, axis=-1)  # Shape: (rows, cols, num_slices)

    metadata = {
        "modality": first_meta.get('modality', 'Unknown'),
        "rows": first_meta.get('rows', volume.shape[0]),
        "columns": first_meta.get('columns', volume.shape[1]),
        "num_slices": volume.shape[2],
        "acquisition_plane": acquisition_plane,
        "voxel_spacing": list(voxel_spacing),
        "window_center": first_meta.get('window_center'),
        "window_width": first_meta.get('window_width'),
    }

    return volume, metadata, acquisition_plane, voxel_spacing, orientation_transforms


def extract_slices_from_volume(
    volume: np.ndarray,
    acquisition_plane: str,
    target_orientation: Orientation,
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0)
) -> List[np.ndarray]:
    """
    Extract 2D slices from a 3D volume along the specified orientation.
    Applies aspect ratio correction based on voxel spacing.

    Note: Does NOT apply automatic orientation transforms.
    User can adjust orientation manually using flip/rotate controls.

    Args:
        volume: 3D numpy array (rows, cols, slices)
        acquisition_plane: Original acquisition plane ("axial", "coronal", "sagittal")
        target_orientation: Desired slice orientation
        voxel_spacing: (row_spacing, col_spacing, slice_spacing) in mm

    Returns:
        List of 2D slices with correct aspect ratio
    """
    row_sp, col_sp, slice_sp = voxel_spacing
    slices = []

    if acquisition_plane == target_orientation:
        # Same as acquisition - iterate through slices in order
        for i in range(volume.shape[2]):
            slice_2d = volume[:, :, i]
            slice_2d = resize_slice_for_aspect_ratio(slice_2d, col_sp, row_sp)
            slices.append(slice_2d)

    elif acquisition_plane == "axial":
        if target_orientation == "coronal":
            for i in range(volume.shape[0]):
                slice_2d = volume[i, :, :].T
                slice_2d = resize_slice_for_aspect_ratio(slice_2d, col_sp, slice_sp)
                slices.append(slice_2d)
        elif target_orientation == "sagittal":
            for i in range(volume.shape[1]):
                slice_2d = volume[:, i, :].T
                slice_2d = resize_slice_for_aspect_ratio(slice_2d, row_sp, slice_sp)
                slices.append(slice_2d)

    elif acquisition_plane == "coronal":
        if target_orientation == "axial":
            for i in range(volume.shape[0]):
                slice_2d = volume[i, :, :].T
                slice_2d = resize_slice_for_aspect_ratio(slice_2d, col_sp, slice_sp)
                slices.append(slice_2d)
        elif target_orientation == "sagittal":
            for i in range(volume.shape[1]):
                slice_2d = volume[:, i, :].T
                slice_2d = resize_slice_for_aspect_ratio(slice_2d, row_sp, slice_sp)
                slices.append(slice_2d)

    elif acquisition_plane == "sagittal":
        if target_orientation == "axial":
            for i in range(volume.shape[0]):
                slice_2d = volume[i, :, :].T
                slice_2d = resize_slice_for_aspect_ratio(slice_2d, col_sp, slice_sp)
                slices.append(slice_2d)
        elif target_orientation == "coronal":
            for i in range(volume.shape[1]):
                slice_2d = volume[:, i, :].T
                slice_2d = resize_slice_for_aspect_ratio(slice_2d, row_sp, slice_sp)
                slices.append(slice_2d)

    return slices


def normalize_to_full_range(
    pixel_array: np.ndarray,
    percentile_low: float = 1,
    percentile_high: float = 99
) -> Tuple[np.ndarray, float, float]:
    """
    Normalize pixel array to 0-255 using full data range (with percentile clipping).
    Returns normalized array and the actual min/max values for client-side windowing.

    Args:
        pixel_array: Raw pixel data
        percentile_low: Lower percentile for clipping outliers
        percentile_high: Upper percentile for clipping outliers

    Returns:
        Tuple of (normalized uint8 array, data_min, data_max)
    """
    # Use float32 for faster processing and lower memory usage
    arr = pixel_array.astype(np.float32)
    vmin = float(np.percentile(arr, percentile_low))
    vmax = float(np.percentile(arr, percentile_high))

    # Clip and normalize
    arr_clipped = np.clip(arr, vmin, vmax)
    if vmax > vmin:
        normalized = ((arr_clipped - vmin) / (vmax - vmin) * 255).astype(np.uint8)
    else:
        normalized = np.zeros_like(arr, dtype=np.uint8)

    return normalized, vmin, vmax


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
    # Use float32 for faster processing and lower memory usage
    arr = pixel_array.astype(np.float32)

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


def normalize_volume(
    volume: np.ndarray,
    window_mode: WindowMode = "auto",
    window_width: int = 98,
    window_level: int = 50
) -> np.ndarray:
    """
    Normalize a 3D volume to 0-255 range.

    Args:
        volume: 3D numpy array
        window_mode: "auto" for percentile-based, "manual" for absolute HU values
        window_width: Window width (percentile range for auto, HU for manual)
        window_level: Window level (percentile center for auto, HU for manual)

    Returns:
        Normalized uint8 3D array
    """
    # Use float32 for faster processing and lower memory usage
    arr = volume.astype(np.float32)

    if window_mode == "auto":
        half_width = window_width / 2
        lower_pct = max(0, window_level - half_width)
        upper_pct = min(100, window_level + half_width)
        vmin = np.percentile(arr, lower_pct)
        vmax = np.percentile(arr, upper_pct)
    else:
        vmin = window_level - window_width / 2
        vmax = window_level + window_width / 2

    arr = np.clip(arr, vmin, vmax)
    if vmax > vmin:
        arr = ((arr - vmin) / (vmax - vmin) * 255).astype(np.uint8)
    else:
        arr = np.zeros_like(arr, dtype=np.uint8)

    return arr


def process_dicom_series(
    files_data: List[Tuple[bytes, str]],
    mode: str = "volume",
    orientation: Orientation = "axial",
    window_mode: WindowMode = "auto",
    window_width: int = 98,
    window_level: int = 50
) -> Tuple[List[np.ndarray], dict]:
    """
    Process a series of DICOM files into normalized slices.

    For 3D volumes (mode="volume"): Builds a 3D array and reslices by orientation.
    For 2D series (mode="series"): Returns slices in acquisition order (for rotating MIP, etc).

    Args:
        files_data: List of (file_content, filename) tuples
        mode: "volume" for 3D reslicing, "series" for 2D sequence
        orientation: Target slice orientation (axial, coronal, sagittal)
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

    first_meta = sorted_files[0][2]

    # Check if orientations are consistent (true 3D volume)
    is_3d_volume = False
    if len(sorted_files) > 1:
        orientations = [
            tuple(item[2].get('image_orientation', []))
            for item in sorted_files
            if item[2].get('image_orientation')
        ]
        if orientations:
            first_orient = orientations[0]
            is_3d_volume = all(
                len(o) == len(first_orient) and
                all(abs(a - b) < 0.01 for a, b in zip(o, first_orient))
                for o in orientations
            )

    if mode == "volume" and is_3d_volume:
        # 3D volume mode: build volume and reslice by orientation
        volume, vol_meta, acquisition_plane, voxel_spacing, _ = build_3d_volume(sorted_files)

        # Normalize the entire volume for consistent windowing
        volume_normalized = normalize_volume(
            volume,
            window_mode=window_mode,
            window_width=window_width,
            window_level=window_level
        )

        # Extract slices along requested orientation with aspect ratio correction
        # Note: No automatic orientation transforms - user can adjust manually
        slices = extract_slices_from_volume(
            volume_normalized,
            acquisition_plane,
            orientation,
            voxel_spacing
        )

        metadata = {
            "num_slices": len(slices),
            "modality": vol_meta.get('modality', 'Unknown'),
            "shape": list(volume.shape),
            "file_type": "dicom_volume",
            "acquisition_plane": acquisition_plane,
            "view_orientation": orientation,
            "voxel_spacing_mm": vol_meta.get('voxel_spacing'),
            "window_mode": window_mode,
            "window_wl": f"W:{window_width} L:{window_level}",
        }

    else:
        # 2D series mode: return slices in sorted order (for rotating MIP, time series)
        # No automatic orientation transforms - user can adjust manually
        slices = []

        # Get pixel spacing for aspect ratio correction
        pixel_spacing = first_meta.get('pixel_spacing', [1.0, 1.0])
        row_sp, col_sp = pixel_spacing[0], pixel_spacing[1]

        for content, pixel_array, meta in sorted_files:
            normalized = normalize_dicom_array(
                pixel_array,
                dicom_window_center=meta.get('window_center'),
                dicom_window_width=meta.get('window_width'),
                window_mode=window_mode,
                user_window_width=window_width,
                user_window_level=window_level
            )
            # Apply aspect ratio correction
            normalized = resize_slice_for_aspect_ratio(normalized, col_sp, row_sp)
            slices.append(normalized)

        metadata = {
            "num_slices": len(slices),
            "modality": first_meta.get('modality', 'Unknown'),
            "shape": [first_meta.get('rows', 0), first_meta.get('columns', 0), len(slices)],
            "file_type": "dicom_series",
            "pixel_spacing_mm": pixel_spacing,
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

    # Get pixel spacing for aspect ratio correction
    if hasattr(ds, 'PixelSpacing'):
        pixel_spacing = [float(x) for x in ds.PixelSpacing]
    else:
        pixel_spacing = [1.0, 1.0]
    row_sp, col_sp = pixel_spacing[0], pixel_spacing[1]

    # Note: No automatic orientation transforms - user can adjust manually

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
            # Apply aspect ratio correction
            normalized = resize_slice_for_aspect_ratio(normalized, col_sp, row_sp)
            frames.append(normalized)

        metadata = {
            "num_slices": len(frames),
            "modality": str(getattr(ds, 'Modality', 'Unknown')),
            "shape": list(pixel_array.shape),
            "file_type": "dicom_multiframe",
            "pixel_spacing_mm": pixel_spacing,
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
        # Apply aspect ratio correction
        normalized = resize_slice_for_aspect_ratio(normalized, col_sp, row_sp)

        metadata = {
            "num_slices": 1,
            "modality": str(getattr(ds, 'Modality', 'Unknown')),
            "shape": list(pixel_array.shape),
            "file_type": "dicom_single",
            "pixel_spacing_mm": pixel_spacing,
            "window_mode": window_mode,
            "window_wl": f"W:{window_width} L:{window_level}",
        }
        return [normalized], metadata
