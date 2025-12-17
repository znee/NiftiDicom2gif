"""
Shared image processing utilities.
Used by both NIfTI and DICOM processors.
"""
import numpy as np
from PIL import Image


def resize_slice_for_aspect_ratio(
    slice_2d: np.ndarray,
    pixel_spacing_h: float,
    pixel_spacing_v: float
) -> np.ndarray:
    """
    Resize a 2D slice to correct for non-isotropic voxels.

    Args:
        slice_2d: 2D numpy array
        pixel_spacing_h: Pixel spacing in horizontal direction (mm)
        pixel_spacing_v: Pixel spacing in vertical direction (mm)

    Returns:
        Resized 2D array with correct aspect ratio
    """
    if abs(pixel_spacing_h - pixel_spacing_v) < 0.01:
        # Already isotropic, no need to resize
        return slice_2d

    h, w = slice_2d.shape[:2]

    # Calculate new dimensions to make isotropic
    # Use the smaller spacing as reference
    target_spacing = min(pixel_spacing_h, pixel_spacing_v)

    new_w = int(round(w * pixel_spacing_h / target_spacing))
    new_h = int(round(h * pixel_spacing_v / target_spacing))

    # Resize using PIL for better interpolation
    img = Image.fromarray(slice_2d)
    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    return np.array(img_resized)
