import { useState } from 'react';
import { FileUploader } from './components/FileUploader';
import { ConversionOptions, type ConversionSettings } from './components/ConversionOptions';
import { Preview } from './components/Preview';
import { ActionButtons } from './components/ActionButtons';
import { convertToGif, getGifUrl, clearTask, clearAll, type ConversionResponse } from './api';

type Status = 'idle' | 'converting' | 'done' | 'error';

// Check if running on GitHub Pages (no backend available)
const isGitHubPages = window.location.hostname.includes('github.io');

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
    windowMin: 1,
    windowMax: 99,
  });
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ConversionResponse | null>(null);
  const [gifUrl, setGifUrl] = useState<string | null>(null);

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
    setStatus('idle');
    setError(null);
  };

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
          <div className="space-y-6">
            {/* File Upload Card */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">
                Upload Files
              </h2>
              <FileUploader
                files={files}
                onFilesChange={setFiles}
                disabled={status === 'converting'}
              />
            </div>

            {/* Conversion Options Card */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">
                Conversion Options
              </h2>
              <ConversionOptions
                settings={settings}
                onSettingsChange={setSettings}
                onConvert={handleConvert}
                disabled={status === 'converting'}
                isConverting={status === 'converting'}
                hasFiles={files.length > 0}
              />
            </div>
          </div>

          {/* Right Column - Preview & Actions */}
          <div className="space-y-6">
            {/* Preview Card */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">
                Preview
              </h2>
              <Preview
                gifUrl={gifUrl}
                previewFrames={result?.preview_frames || []}
                metadata={result?.metadata || null}
                isLoading={status === 'converting'}
              />
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
