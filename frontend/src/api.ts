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
  formData.append('window_min', settings.windowMin.toString());
  formData.append('window_max', settings.windowMax.toString());
  // Flip
  formData.append('flip_horizontal', settings.flipHorizontal.toString());

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
