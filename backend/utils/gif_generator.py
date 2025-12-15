"""
GIF generation utility.
Creates animated GIFs from sequences of 2D image slices.
"""
import io
import base64
from typing import List, Literal

import numpy as np
import imageio.v3 as iio
from PIL import Image
import matplotlib.pyplot as plt


Colormap = Literal["gray", "viridis", "plasma", "hot", "bone", "jet"]


def apply_colormap(
    slices: List[np.ndarray],
    colormap: Colormap = "gray"
) -> List[np.ndarray]:
    """
    Apply a colormap to grayscale slices.

    Args:
        slices: List of 2D uint8 arrays (0-255)
        colormap: Matplotlib colormap name

    Returns:
        List of RGB arrays (H, W, 3) as uint8
    """
    if colormap == "gray":
        # Convert grayscale to RGB by stacking
        return [np.stack([s, s, s], axis=-1) for s in slices]

    # Get matplotlib colormap (using colormaps instead of deprecated get_cmap)
    cmap = plt.colormaps[colormap]

    colored = []
    for s in slices:
        # Normalize to 0-1 for colormap
        normalized = s.astype(np.float32) / 255.0
        # Apply colormap (returns RGBA)
        rgba = cmap(normalized)
        # Convert to uint8 RGB
        rgb = (rgba[:, :, :3] * 255).astype(np.uint8)
        colored.append(rgb)

    return colored


def resize_slices(
    slices: List[np.ndarray],
    max_size: int = 512
) -> List[np.ndarray]:
    """
    Resize slices to fit within max_size while preserving aspect ratio.

    Args:
        slices: List of 2D or 3D arrays
        max_size: Maximum dimension size

    Returns:
        List of resized arrays
    """
    if not slices:
        return slices

    h, w = slices[0].shape[:2]
    if max(h, w) <= max_size:
        return slices

    # Calculate new size
    if h > w:
        new_h = max_size
        new_w = int(w * max_size / h)
    else:
        new_w = max_size
        new_h = int(h * max_size / w)

    resized = []
    for s in slices:
        img = Image.fromarray(s)
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        resized.append(np.array(img_resized))

    return resized


def generate_gif(
    slices: List[np.ndarray],
    output_path: str,
    fps: int = 10,
    colormap: Colormap = "gray",
    loop: int = 0,
    max_size: int = 512
) -> str:
    """
    Generate an animated GIF from a sequence of slices.

    Args:
        slices: List of 2D numpy arrays (grayscale)
        output_path: Path to save the GIF
        fps: Frames per second
        colormap: Colormap to apply
        loop: Number of loops (0 = infinite)
        max_size: Maximum dimension for resizing

    Returns:
        Path to the generated GIF
    """
    if not slices:
        raise ValueError("No slices provided")

    # Apply colormap
    colored = apply_colormap(slices, colormap)

    # Resize if needed
    resized = resize_slices(colored, max_size)

    # Calculate duration in milliseconds
    duration = int(1000 / fps)

    # Save GIF
    iio.imwrite(
        output_path,
        resized,
        extension=".gif",
        duration=duration,
        loop=loop
    )

    return output_path


def get_preview_frames(
    slices: List[np.ndarray],
    num_frames: int = 5,
    colormap: Colormap = "gray",
    max_size: int = 256
) -> List[str]:
    """
    Get a few frames as base64-encoded PNGs for preview.

    Args:
        slices: List of 2D numpy arrays
        num_frames: Number of preview frames to generate
        colormap: Colormap to apply
        max_size: Maximum dimension for resizing

    Returns:
        List of base64-encoded PNG strings
    """
    if not slices:
        return []

    # Select evenly spaced frames
    n = len(slices)
    if n <= num_frames:
        indices = list(range(n))
    else:
        step = n / num_frames
        indices = [int(i * step) for i in range(num_frames)]

    selected = [slices[i] for i in indices]

    # Apply colormap
    colored = apply_colormap(selected, colormap)

    # Resize
    resized = resize_slices(colored, max_size)

    # Convert to base64 PNGs
    previews = []
    for frame in resized:
        img = Image.fromarray(frame)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        previews.append(f"data:image/png;base64,{b64}")

    return previews
