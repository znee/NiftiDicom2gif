import { useState, useCallback } from 'react';
import { FileUploader } from './components/FileUploader';
import { ConversionOptions, type ConversionSettings } from './components/ConversionOptions';
import { Preview } from './components/Preview';
import { InteractivePreview } from './components/InteractivePreview';
import { ActionButtons } from './components/ActionButtons';
import { convertToGif, getGifUrl, clearTask, clearAll, getPreviewFrames, type ConversionResponse, type PreviewResponse } from './api';

type Status = 'idle' | 'loading_preview' | 'previewing' | 'converting' | 'done' | 'error';

// Check if running on GitHub Pages (no backend available)
const isGitHubPages = window.location.hostname.includes('github.io');

// Check if running on cloud-hosted version (not localhost)
const isCloudHosted = !['localhost', '127.0.0.1'].includes(window.location.hostname) && !isGitHubPages;

function App() {
  const [files, setFiles] = useState<File[]>([]);
  const [settings, setSettings] = useState<ConversionSettings>({
    mode: 'volume',
    orientation: 'axial',
    fps: 10,
    colormap: 'gray',
    sliceStart: 0,
    sliceEnd: 100,
    windowMode: 'auto',
    windowLevel: 50,
    windowWidth: 98,
    // Image transform controls
    flipHorizontal: false,
    flipVertical: false,
    rotate90: 0,
    reverseSlices: false,
    // GIF options
    maxGifSize: 512,
    maxFrames: 0,
  });
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ConversionResponse | null>(null);
  const [gifUrl, setGifUrl] = useState<string | null>(null);
  // Interactive preview state
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);
  const [currentSlice, setCurrentSlice] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const handleLoadPreview = useCallback(async () => {
    if (files.length === 0) return;

    setStatus('loading_preview');
    setError(null);
    setPreviewData(null);
    setCurrentSlice(0);
    setIsPlaying(false);
    // Clear GIF result when loading new preview
    setResult(null);
    setGifUrl(null);

    try {
      const response = await getPreviewFrames(files, {
        mode: settings.mode,
        orientation: settings.orientation,
        // Colormap and slice range applied client-side for interactivity
        windowMode: settings.windowMode,
        windowWidth: settings.windowWidth,
        windowLevel: settings.windowLevel,
        previewSize: 320, // Slightly larger for better preview
      });
      setPreviewData(response);
      setCurrentSlice(0);
      setStatus('previewing');
    } catch (err) {
      setStatus('error');
      if (err instanceof Error) {
        setError(err.message);
      } else if (typeof err === 'object' && err !== null && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        setError(axiosError.response?.data?.detail || 'Failed to load preview');
      } else {
        setError('An unexpected error occurred');
      }
    }
  }, [files, settings]);

  const handleConvert = async () => {
    if (files.length === 0) return;

    setStatus('converting');
    setError(null);
    setResult(null);
    setGifUrl(null);

    try {
      const response = await convertToGif(files, settings);
      setResult(response);
      setGifUrl(getGifUrl(response.task_id));
      setStatus('done');
    } catch (err) {
      setStatus('error');
      if (err instanceof Error) {
        setError(err.message);
      } else if (typeof err === 'object' && err !== null && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        setError(axiosError.response?.data?.detail || 'Conversion failed');
      } else {
        setError('An unexpected error occurred');
      }
    }
  };

  const handleClear = async () => {
    if (result?.task_id) {
      try {
        await clearTask(result.task_id);
      } catch {
        // Ignore errors
      }
    }
    setResult(null);
    setGifUrl(null);
    setPreviewData(null);
    setCurrentSlice(0);
    setIsPlaying(false);
    setStatus('idle');
    setError(null);
  };

  const handleClearAll = async () => {
    try {
      await clearAll();
    } catch {
      // Ignore errors
    }
    setFiles([]);
    setResult(null);
    setGifUrl(null);
    setPreviewData(null);
    setCurrentSlice(0);
    setIsPlaying(false);
    setStatus('idle');
    setError(null);
  };

  const handleSliceChange = useCallback((slice: number) => {
    setCurrentSlice(slice);
  }, []);

  const handlePlayPauseToggle = useCallback(() => {
    setIsPlaying(prev => !prev);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-800">
            Medical Image to GIF Converter
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Convert NIfTI and DICOM files to animated GIFs
          </p>
        </div>
      </header>

      {/* Cloud Hosting Privacy Warning */}
      {isCloudHosted && (
        <div className="bg-red-50 border-b-2 border-red-300">
          <div className="max-w-6xl mx-auto px-4 py-3">
            <div className="flex items-start gap-3 text-red-800">
              <svg className="w-6 h-6 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div className="text-sm">
                <p className="font-bold text-red-900 mb-1">Cloud Demo - Limited Resources (512MB RAM)</p>
                <ul className="space-y-0.5 text-red-700">
                  <li>• <strong>Do NOT upload real patient data</strong> - Use only anonymized or sample files</li>
                  <li>• <strong>Small volumes only</strong> (~256×256×200 max) - Large/high-res files will fail</li>
                  <li>• For large data, <a href="https://github.com/znee/NiftiDicom2gif" className="underline font-medium" target="_blank" rel="noopener noreferrer">run locally</a> on your own machine</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* GitHub Pages Notice */}
      {isGitHubPages && (
        <div className="bg-blue-50 border-b border-blue-200">
          <div className="max-w-6xl mx-auto px-4 py-3">
            <div className="flex items-center gap-2 text-blue-800">
              <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm">
                <strong>Demo Mode:</strong> This is a static preview. To use the converter, clone the repository and run locally with the Python backend.
                See <a href="https://github.com/znee/NiftiDicom2gif" className="underline font-medium" target="_blank" rel="noopener noreferrer">GitHub</a> for instructions.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left Column - Upload & Options */}
          <div className="space-y-4">
            {/* File Upload Card */}
            <div className="bg-white rounded-2xl shadow-sm p-5">
              <h2 className="text-lg font-semibold text-gray-800 mb-3">
                Upload Files
              </h2>
              <FileUploader
                files={files}
                onFilesChange={setFiles}
                disabled={status === 'converting'}
              />
            </div>

            {/* Action Buttons - Load Preview & Convert */}
            <div className="flex gap-2">
              {/* Load Preview Button */}
              <button
                onClick={handleLoadPreview}
                disabled={status === 'converting' || status === 'loading_preview' || files.length === 0}
                className={`
                  flex-1 py-3 px-4 rounded-xl font-semibold transition-all
                  ${status === 'converting' || status === 'loading_preview' || files.length === 0
                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    : 'bg-purple-100 text-purple-700 hover:bg-purple-200 active:bg-purple-300 border border-purple-300'
                  }
                `}
              >
                {status === 'loading_preview' ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Loading...
                  </span>
                ) : (
                  'Load Preview'
                )}
              </button>

              {/* Convert Button */}
              <button
                onClick={handleConvert}
                disabled={status === 'converting' || status === 'loading_preview' || files.length === 0}
                className={`
                  flex-1 py-3 px-4 rounded-xl font-semibold text-white transition-all
                  ${status === 'converting' || status === 'loading_preview' || files.length === 0
                    ? 'bg-gray-300 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 shadow-lg hover:shadow-xl'
                  }
                `}
              >
                {status === 'converting' ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Converting...
                  </span>
                ) : (
                  'Convert to GIF'
                )}
              </button>
            </div>

            {/* Conversion Options Card */}
            <div className="bg-white rounded-2xl shadow-sm p-5">
              <h2 className="text-lg font-semibold text-gray-800 mb-3">
                Conversion Options
              </h2>
              <ConversionOptions
                settings={settings}
                onSettingsChange={setSettings}
                disabled={status === 'converting'}
              />
            </div>
          </div>

          {/* Right Column - Preview & Actions */}
          <div className="space-y-6">
            {/* Preview Card */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">
                  {gifUrl ? 'Generated GIF' : 'Interactive Preview'}
                </h2>
                {previewData && !gifUrl && (
                  <span className="text-xs text-purple-600 bg-purple-100 px-2 py-1 rounded-full">
                    Transforms applied live
                  </span>
                )}
              </div>

              {/* Show loading spinner */}
              {(status === 'converting' || status === 'loading_preview') && (
                <div className="flex flex-col items-center justify-center h-64 bg-gray-50 rounded-xl">
                  <svg className="animate-spin h-10 w-10 text-blue-500 mb-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-gray-500">
                    {status === 'loading_preview' ? 'Loading preview...' : 'Converting to GIF...'}
                  </p>
                </div>
              )}

              {/* Show final GIF when available */}
              {gifUrl && status === 'done' && (
                <Preview
                  gifUrl={gifUrl}
                  previewFrames={result?.preview_frames || []}
                  metadata={result?.metadata || null}
                  isLoading={false}
                />
              )}

              {/* Show interactive preview when we have frames but no final GIF */}
              {!gifUrl && previewData && status === 'previewing' && (
                <InteractivePreview
                  frames={previewData.all_frames}
                  totalFrames={previewData.original_total}
                  currentSlice={currentSlice}
                  onSliceChange={handleSliceChange}
                  flipHorizontal={settings.flipHorizontal}
                  flipVertical={settings.flipVertical}
                  rotate90={settings.rotate90}
                  reverseSlices={settings.reverseSlices}
                  sliceStart={settings.sliceStart}
                  sliceEnd={settings.sliceEnd}
                  colormap={settings.colormap}
                  windowMode={settings.windowMode}
                  windowWidth={settings.windowWidth}
                  windowLevel={settings.windowLevel}
                  isPlaying={isPlaying}
                  fps={settings.fps}
                  onPlayPauseToggle={handlePlayPauseToggle}
                  metadata={previewData.metadata}
                />
              )}

              {/* Show empty state */}
              {status === 'idle' && !previewData && !gifUrl && (
                <div className="flex flex-col items-center justify-center h-64 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
                  <svg className="w-16 h-16 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <p className="text-gray-400 text-center text-sm">
                    Upload files, then click<br />"Load Preview" for interactive mode
                  </p>
                </div>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                <div className="flex items-center gap-2 text-red-700">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <span className="font-medium">Error</span>
                </div>
                <p className="text-red-600 text-sm mt-1">{error}</p>
              </div>
            )}

            {/* Action Buttons Card */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">
                Actions
              </h2>
              <ActionButtons
                gifUrl={gifUrl}
                taskId={result?.task_id || null}
                onClear={handleClear}
                onClearAll={handleClearAll}
                disabled={status === 'converting'}
              />
              <p className="text-xs text-gray-400 mt-3 text-center">
                Use "Clear All" to remove all uploaded data for privacy
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Disclaimers Section */}
      <section className="max-w-6xl mx-auto px-4 py-8">
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-amber-800 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Important Disclaimers
          </h3>

          <div className="space-y-4 text-sm text-amber-900">
            {/* Privacy Notice */}
            <div>
              <h4 className="font-semibold mb-1">Privacy Notice</h4>
              <ul className="list-disc list-inside space-y-1 text-amber-800">
                <li>This tool processes medical imaging data which may contain Protected Health Information (PHI)</li>
                <li>Files are processed locally on the server and temporarily stored during conversion</li>
                <li>Use the "Clear All" button to remove all uploaded data after use</li>
                <li>Do not use this tool on public networks with sensitive patient data</li>
                <li>You are responsible for ensuring compliance with HIPAA, GDPR, or other applicable regulations</li>
              </ul>
            </div>

            {/* Medical Disclaimer */}
            <div>
              <h4 className="font-semibold mb-1">Medical Disclaimer</h4>
              <ul className="list-disc list-inside space-y-1 text-amber-800">
                <li>This tool is for visualization and educational purposes only</li>
                <li>Output GIFs are not suitable for clinical diagnosis or medical decision-making</li>
                <li>Image processing may alter appearance - always refer to original DICOM/NIfTI for clinical use</li>
              </ul>
            </div>

            {/* Usage Terms */}
            <div>
              <h4 className="font-semibold mb-1">Terms of Use</h4>
              <ul className="list-disc list-inside space-y-1 text-amber-800">
                <li>This software is provided "as is" without warranty of any kind</li>
                <li>The authors are not liable for any damages arising from the use of this tool</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Footer with Credits */}
      <footer className="bg-slate-800 text-white mt-8">
        <div className="max-w-6xl mx-auto px-4 py-8">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Credits */}
            <div>
              <h4 className="font-semibold mb-3">Credits & Acknowledgments</h4>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>Developed by <span className="text-white">Jinhee Jang MD, PhD</span>, Seoul St. Mary's Hospital</li>
                <li>Built with FastAPI, React, and TypeScript</li>
                <li>NIfTI processing: <a href="https://nipy.org/nibabel/" className="text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">NiBabel</a></li>
                <li>DICOM processing: <a href="https://pydicom.github.io/" className="text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">pydicom</a></li>
                <li>GIF generation: <a href="https://imageio.readthedocs.io/" className="text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">imageio</a></li>
              </ul>
            </div>

            {/* Supported Formats */}
            <div>
              <h4 className="font-semibold mb-3">Supported Formats</h4>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>NIfTI: .nii, .nii.gz (3D and 4D volumes)</li>
                <li>DICOM: .dcm, .dicom (single files and series)</li>
              </ul>
            </div>
          </div>

          <div className="border-t border-slate-700 mt-6 pt-6 text-center text-sm text-slate-400">
            <p>Medical Image to GIF Converter</p>
            <p className="mt-1">For research and educational purposes only</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
