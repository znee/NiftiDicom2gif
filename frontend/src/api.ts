import axios from 'axios';
import type { ConversionSettings } from './components/ConversionOptions';

// Use relative path - Vite proxy handles forwarding to backend
// Override with VITE_API_BASE env var for production or other environments
const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export interface ConversionResponse {
  success: boolean;
  task_id: string;
  gif_url: string;
  preview_frames: string[];
  metadata: {
    shape?: number[];
    num_slices?: number;
    file_type?: string;
    orientation?: string;
    modality?: string;
  };
}

export interface PreviewResponse {
  success: boolean;
  task_id: string;
  all_frames: string[];  // Grayscale frames - colormap applied client-side
  total_frames: number;
  original_total: number;  // Total before any filtering
  metadata: {
    shape?: number[];
    num_slices?: number;
    num_frames?: number;
    file_type?: string;
    orientation?: string;
    modality?: string;
  };
}

export async function convertToGif(
  files: File[],
  settings: ConversionSettings
): Promise<ConversionResponse> {
  const formData = new FormData();

  // Add files
  files.forEach((file) => {
    formData.append('files', file);
  });

  // Add settings
  formData.append('mode', settings.mode);
  formData.append('orientation', settings.orientation);
  formData.append('fps', settings.fps.toString());
  formData.append('colormap', settings.colormap);
  // Slice range
  formData.append('slice_start', settings.sliceStart.toString());
  formData.append('slice_end', settings.sliceEnd.toString());
  // Window/Level (dynamic range)
  formData.append('window_mode', settings.windowMode);
  formData.append('window_width', settings.windowWidth.toString());
  formData.append('window_level', settings.windowLevel.toString());
  // Image transform controls
  formData.append('flip_horizontal', settings.flipHorizontal.toString());
  formData.append('flip_vertical', settings.flipVertical.toString());
  formData.append('rotate90', settings.rotate90.toString());
  formData.append('reverse_slices', settings.reverseSlices.toString());
  // GIF size options
  formData.append('max_gif_size', settings.maxGifSize.toString());
  formData.append('max_frames', settings.maxFrames.toString());

  const response = await axios.post<ConversionResponse>(
    `${API_BASE}/convert`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
}

export function getGifUrl(taskId: string): string {
  return `${API_BASE}/download/${taskId}`;
}

export async function clearTask(taskId: string): Promise<void> {
  await axios.delete(`${API_BASE}/clear/${taskId}`);
}

export async function clearAll(): Promise<void> {
  await axios.delete(`${API_BASE}/clear`);
}

export interface PreviewSettings {
  mode: 'volume' | 'series';
  orientation: 'axial' | 'coronal' | 'sagittal';
  windowMode: 'auto' | 'manual';
  windowWidth: number;
  windowLevel: number;
  previewSize?: number;
}

export async function getPreviewFrames(
  files: File[],
  settings: PreviewSettings
): Promise<PreviewResponse> {
  const formData = new FormData();

  files.forEach((file) => {
    formData.append('files', file);
  });

  formData.append('mode', settings.mode);
  formData.append('orientation', settings.orientation);
  // Colormap and slice range are applied client-side for interactivity
  formData.append('window_mode', settings.windowMode);
  formData.append('window_width', settings.windowWidth.toString());
  formData.append('window_level', settings.windowLevel.toString());
  formData.append('preview_size', (settings.previewSize || 256).toString());

  const response = await axios.post<PreviewResponse>(
    `${API_BASE}/preview`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
}
