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

# Lazy-load matplotlib to reduce startup overhead
_plt = None


Colormap = Literal["gray", "viridis", "plasma", "hot", "bone", "jet"]


def _get_matplotlib_colormap(name: str):
    """Lazy-load matplotlib and get colormap."""
    global _plt
    if _plt is None:
        import matplotlib.pyplot as plt
        _plt = plt
    return _plt.colormaps[name]


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
    # Ensure all slices are 2D
    processed_slices = []
    for s in slices:
        if s.ndim == 2:
            processed_slices.append(s)
        elif s.ndim > 2:
            # Squeeze out any extra dimensions
            squeezed = np.squeeze(s)
            if squeezed.ndim == 2:
                processed_slices.append(squeezed)
            elif squeezed.ndim > 2:
                # Take first 2D slice
                processed_slices.append(squeezed[:, :, 0] if squeezed.ndim == 3 else squeezed.reshape(squeezed.shape[0], -1))

    if not processed_slices:
        return []

    if colormap == "gray":
        # Convert grayscale to RGB by stacking (no matplotlib needed)
        return [np.stack([s, s, s], axis=-1) for s in processed_slices]

    # Get matplotlib colormap (lazy-loaded)
    cmap = _get_matplotlib_colormap(colormap)

    colored = []
    for s in processed_slices:
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


def optimize_gif_frames(
    slices: List[np.ndarray],
    max_frames: int = 200,
    target_size_mb: float = 10.0
) -> List[np.ndarray]:
    """
    Optimize GIF by reducing frame count if needed.

    Args:
        slices: List of frames
        max_frames: Maximum number of frames
        target_size_mb: Target file size in MB (rough estimate)

    Returns:
        Optimized list of frames
    """
    if len(slices) <= max_frames:
        return slices

    # Calculate step to reduce frames
    step = len(slices) / max_frames
    indices = [int(i * step) for i in range(max_frames)]
    return [slices[i] for i in indices]


def generate_gif(
    slices: List[np.ndarray],
    output_path: str,
    fps: int = 10,
    colormap: Colormap = "gray",
    loop: int = 0,
    max_size: int = 512,
    max_frames: int = 0,
    optimize: bool = True
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
        max_frames: Maximum number of frames (0 = no limit)
        optimize: Whether to optimize the GIF for file size

    Returns:
        Path to the generated GIF
    """
    if not slices:
        raise ValueError("No slices provided")

    # Apply colormap
    colored = apply_colormap(slices, colormap)

    # Resize if needed
    resized = resize_slices(colored, max_size)

    # Limit frame count if specified
    if max_frames > 0:
        resized = optimize_gif_frames(resized, max_frames)

    # Calculate duration in milliseconds
    duration = int(1000 / fps)

    # Save GIF with optimization
    if optimize:
        # Use PIL for better GIF optimization
        frames_pil = [Image.fromarray(f) for f in resized]
        if frames_pil:
            frames_pil[0].save(
                output_path,
                save_all=True,
                append_images=frames_pil[1:],
                duration=duration,
                loop=loop,
                optimize=True
            )
    else:
        # Use imageio (faster but larger files)
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


def get_all_preview_frames(
    slices: List[np.ndarray],
    colormap: Colormap = "gray",
    max_size: int = 256,
    return_grayscale: bool = False
) -> List[str]:
    """
    Get ALL frames as base64-encoded PNGs for interactive preview.
    Frames are returned without transforms - transforms applied client-side.

    Args:
        slices: List of 2D numpy arrays (grayscale normalized)
        colormap: Colormap to apply (ignored if return_grayscale=True)
        max_size: Maximum dimension for resizing
        return_grayscale: If True, return grayscale images for client-side colormap

    Returns:
        List of base64-encoded PNG strings for all frames
    """
    if not slices:
        return []

    if return_grayscale:
        # Return grayscale for client-side colormap application
        # Resize first, keep as grayscale
        resized = resize_slices([np.stack([s, s, s], axis=-1) for s in slices], max_size)
        # Convert back to grayscale for smaller transfer
        all_frames = []
        for frame in resized:
            # Take just one channel since all RGB channels are the same
            gray = frame[:, :, 0]
            img = Image.fromarray(gray, mode='L')
            buffer = io.BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)
            b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            all_frames.append(f"data:image/png;base64,{b64}")
        return all_frames

    # Apply colormap
    colored = apply_colormap(slices, colormap)

    # Resize
    resized = resize_slices(colored, max_size)

    # Convert to base64 PNGs
    all_frames = []
    for frame in resized:
        img = Image.fromarray(frame)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        all_frames.append(f"data:image/png;base64,{b64}")

    return all_frames
