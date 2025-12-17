import { useEffect, useRef, useState, useCallback, useMemo } from 'react';

// Colormap lookup tables (matching backend options)
const COLORMAPS: Record<string, number[][]> = {
  gray: [], // Special case - no LUT needed
  viridis: generateViridisLUT(),
  plasma: generatePlasmaLUT(),
  hot: generateHotLUT(),
  bone: generateBoneLUT(),
  jet: generateJetLUT(),
};

// Generate colormap LUTs (simplified versions)
function generateViridisLUT(): number[][] {
  const lut: number[][] = [];
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    lut.push([
      Math.round((0.267 + t * (0.329 + t * (1.260 - t * 1.856))) * 255),
      Math.round((0.004 + t * (0.873 + t * (0.688 - t * 0.565))) * 255),
      Math.round((0.329 + t * (1.579 - t * (2.931 - t * 1.023))) * 255),
    ]);
  }
  return lut;
}

function generatePlasmaLUT(): number[][] {
  const lut: number[][] = [];
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    lut.push([
      Math.round((0.050 + t * (2.735 - t * 1.785)) * 255),
      Math.round((0.030 + t * (0.214 + t * (2.120 - t * 1.364))) * 255),
      Math.round((0.528 + t * (1.088 - t * (2.952 - t * 1.336))) * 255),
    ]);
  }
  return lut;
}

function generateHotLUT(): number[][] {
  const lut: number[][] = [];
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    lut.push([
      Math.round(Math.min(1, t * 3) * 255),
      Math.round(Math.min(1, Math.max(0, t * 3 - 1)) * 255),
      Math.round(Math.min(1, Math.max(0, t * 3 - 2)) * 255),
    ]);
  }
  return lut;
}

function generateBoneLUT(): number[][] {
  const lut: number[][] = [];
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    lut.push([
      Math.round((t < 0.75 ? t * 8/9 : (t - 0.75) * 2/9 + 2/3) * 255),
      Math.round((t < 0.375 ? t * 8/9 : (t < 0.75 ? (t - 0.375) * 2/9 + 1/3 : (t - 0.75) + 2/3)) * 255),
      Math.round((t < 0.375 ? t * 10/9 : (t - 0.375) * 8/9 + 5/12) * 255),
    ]);
  }
  return lut;
}

function generateJetLUT(): number[][] {
  const lut: number[][] = [];
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    let r, g, b;
    if (t < 0.125) {
      r = 0; g = 0; b = 0.5 + t * 4;
    } else if (t < 0.375) {
      r = 0; g = (t - 0.125) * 4; b = 1;
    } else if (t < 0.625) {
      r = (t - 0.375) * 4; g = 1; b = 1 - (t - 0.375) * 4;
    } else if (t < 0.875) {
      r = 1; g = 1 - (t - 0.625) * 4; b = 0;
    } else {
      r = 1 - (t - 0.875) * 4; g = 0; b = 0;
    }
    lut.push([Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)]);
  }
  return lut;
}

interface InteractivePreviewProps {
  frames: string[];  // Grayscale base64 images
  totalFrames: number;  // Original total before any filtering
  currentSlice: number;
  onSliceChange: (slice: number) => void;
  // Image transforms
  flipHorizontal: boolean;
  flipVertical: boolean;
  rotate90: number;
  reverseSlices: boolean;
  // Slice range (percentage 0-100)
  sliceStart: number;
  sliceEnd: number;
  // Colormap
  colormap: string;
  // Animation
  isPlaying: boolean;
  fps: number;
  onPlayPauseToggle: () => void;
  metadata?: {
    num_slices?: number;
    file_type?: string;
    orientation?: string;
  } | null;
}

export function InteractivePreview({
  frames,
  totalFrames,
  currentSlice,
  onSliceChange,
  flipHorizontal,
  flipVertical,
  rotate90,
  reverseSlices,
  sliceStart,
  sliceEnd,
  colormap,
  isPlaying,
  fps,
  onPlayPauseToggle,
  metadata,
}: InteractivePreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loadedImages, setLoadedImages] = useState<HTMLImageElement[]>([]);
  const animationRef = useRef<number | null>(null);
  const lastFrameTimeRef = useRef<number>(0);

  // Calculate filtered frame indices based on slice range
  const filteredIndices = useMemo(() => {
    const total = frames.length;
    const startIdx = Math.floor(total * sliceStart / 100);
    const endIdx = Math.max(startIdx + 1, Math.floor(total * sliceEnd / 100));
    const indices: number[] = [];
    for (let i = startIdx; i < endIdx && i < total; i++) {
      indices.push(i);
    }
    return indices;
  }, [frames.length, sliceStart, sliceEnd]);

  // Number of frames after filtering
  const filteredFrameCount = filteredIndices.length;

  // Clamp current slice to valid range
  useEffect(() => {
    if (currentSlice >= filteredFrameCount) {
      onSliceChange(Math.max(0, filteredFrameCount - 1));
    }
  }, [filteredFrameCount, currentSlice, onSliceChange]);

  // Get the effective frame index (accounting for reverse and slice filtering)
  const getEffectiveIndex = useCallback((displayIdx: number) => {
    // First apply reverse if needed
    const idx = reverseSlices ? filteredFrameCount - 1 - displayIdx : displayIdx;
    // Then map to actual frame index
    return filteredIndices[Math.min(Math.max(0, idx), filteredIndices.length - 1)] ?? 0;
  }, [reverseSlices, filteredFrameCount, filteredIndices]);

  // Preload all images
  useEffect(() => {
    if (frames.length === 0) {
      setLoadedImages([]);
      return;
    }

    const images: HTMLImageElement[] = [];
    let loaded = 0;

    frames.forEach((src, idx) => {
      const img = new Image();
      img.onload = () => {
        loaded++;
        if (loaded === frames.length) {
          setLoadedImages(images);
        }
      };
      img.onerror = () => {
        loaded++;
        if (loaded === frames.length) {
          setLoadedImages(images);
        }
      };
      img.src = src;
      images[idx] = img;
    });

    return () => {
      images.forEach(img => {
        img.onload = null;
        img.onerror = null;
      });
    };
  }, [frames]);

  // Apply colormap to grayscale image data
  const applyColormap = useCallback((ctx: CanvasRenderingContext2D, width: number, height: number) => {
    if (colormap === 'gray') return; // No transformation needed

    const lut = COLORMAPS[colormap];
    if (!lut || lut.length === 0) return;

    const imageData = ctx.getImageData(0, 0, width, height);
    const data = imageData.data;

    for (let i = 0; i < data.length; i += 4) {
      const gray = data[i]; // R channel (same as G and B for grayscale)
      const [r, g, b] = lut[gray] || [gray, gray, gray];
      data[i] = r;
      data[i + 1] = g;
      data[i + 2] = b;
      // Alpha stays the same
    }

    ctx.putImageData(imageData, 0, 0);
  }, [colormap]);

  // Draw frame to canvas with transforms and colormap
  const drawFrame = useCallback((displayFrameIndex: number) => {
    const canvas = canvasRef.current;
    if (!canvas || loadedImages.length === 0 || filteredIndices.length === 0) return;

    const effectiveIdx = getEffectiveIndex(displayFrameIndex);
    const img = loadedImages[effectiveIdx];
    if (!img || !img.complete) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Determine canvas size based on rotation
    const rotated = rotate90 % 2 !== 0;
    const displayWidth = rotated ? img.height : img.width;
    const displayHeight = rotated ? img.width : img.height;

    // Set canvas size
    canvas.width = displayWidth;
    canvas.height = displayHeight;

    // Clear and apply transforms
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();

    // Move to center for rotation
    ctx.translate(canvas.width / 2, canvas.height / 2);

    // Apply rotation (negative for clockwise)
    ctx.rotate(-rotate90 * Math.PI / 2);

    // Apply flips
    const scaleX = flipHorizontal ? -1 : 1;
    const scaleY = flipVertical ? -1 : 1;
    ctx.scale(scaleX, scaleY);

    // Draw image centered
    ctx.drawImage(img, -img.width / 2, -img.height / 2);

    ctx.restore();

    // Apply colormap after drawing
    applyColormap(ctx, canvas.width, canvas.height);
  }, [loadedImages, flipHorizontal, flipVertical, rotate90, getEffectiveIndex, applyColormap, filteredIndices.length]);

  // Draw current frame when slice, transforms, or colormap change
  useEffect(() => {
    if (loadedImages.length > 0 && !isPlaying) {
      drawFrame(currentSlice);
    }
  }, [currentSlice, drawFrame, loadedImages, isPlaying, flipHorizontal, flipVertical, rotate90, reverseSlices, colormap, sliceStart, sliceEnd]);

  // Animation loop
  useEffect(() => {
    if (!isPlaying || loadedImages.length === 0 || filteredFrameCount === 0) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      return;
    }

    const frameDuration = 1000 / fps;
    let localSlice = currentSlice;

    const animate = (timestamp: number) => {
      if (timestamp - lastFrameTimeRef.current >= frameDuration) {
        localSlice = (localSlice + 1) % filteredFrameCount;
        onSliceChange(localSlice);
        drawFrame(localSlice);
        lastFrameTimeRef.current = timestamp;
      }
      animationRef.current = requestAnimationFrame(animate);
    };

    lastFrameTimeRef.current = performance.now();
    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [isPlaying, fps, filteredFrameCount, drawFrame, onSliceChange, currentSlice]);

  // Draw first frame when images load
  useEffect(() => {
    if (loadedImages.length > 0) {
      drawFrame(currentSlice);
    }
  }, [loadedImages, drawFrame, currentSlice]);

  if (frames.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
        <svg
          className="w-16 h-16 text-gray-300 mb-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        <p className="text-gray-400 text-center">
          Click "Load Preview" to see<br />interactive preview
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Canvas Preview */}
      <div className="bg-black rounded-xl overflow-hidden flex items-center justify-center p-2">
        <canvas
          ref={canvasRef}
          className="max-w-full max-h-80 object-contain"
          style={{ imageRendering: 'auto' }}
        />
      </div>

      {/* Slice Slider */}
      <div className="bg-gray-50 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-600">
            Frame {currentSlice + 1} / {filteredFrameCount}
            {filteredFrameCount !== totalFrames && (
              <span className="text-gray-400 ml-1">({sliceStart}%-{sliceEnd}%)</span>
            )}
          </span>
          <div className="flex items-center gap-2">
            {/* Step backward */}
            <button
              onClick={() => onSliceChange(Math.max(0, currentSlice - 1))}
              className="p-1 hover:bg-gray-200 rounded transition-colors"
              title="Previous frame"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            {/* Play/Pause */}
            <button
              onClick={onPlayPauseToggle}
              className={`p-1.5 rounded transition-colors ${
                isPlaying ? 'bg-blue-500 text-white' : 'hover:bg-gray-200'
              }`}
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              )}
            </button>
            {/* Step forward */}
            <button
              onClick={() => onSliceChange(Math.min(filteredFrameCount - 1, currentSlice + 1))}
              className="p-1 hover:bg-gray-200 rounded transition-colors"
              title="Next frame"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
        <input
          type="range"
          min="0"
          max={Math.max(0, filteredFrameCount - 1)}
          value={Math.min(currentSlice, filteredFrameCount - 1)}
          onChange={(e) => onSliceChange(parseInt(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
      </div>

      {/* Metadata */}
      {metadata && (
        <div className="bg-gray-50 rounded-lg p-3">
          <h4 className="text-xs font-medium text-gray-700 mb-1">Image Info</h4>
          <div className="grid grid-cols-2 gap-1 text-xs text-gray-600">
            {metadata.file_type && (
              <div>Type: <span className="font-medium">{metadata.file_type.toUpperCase()}</span></div>
            )}
            <div>Total: <span className="font-medium">{totalFrames} frames</span></div>
            {metadata.orientation && (
              <div>View: <span className="font-medium capitalize">{metadata.orientation}</span></div>
            )}
            <div>Colormap: <span className="font-medium capitalize">{colormap}</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
