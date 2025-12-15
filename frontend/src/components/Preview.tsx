interface Metadata {
  shape?: number[];
  num_slices?: number;
  file_type?: string;
  orientation?: string;
  modality?: string;
}

interface PreviewProps {
  gifUrl: string | null;
  previewFrames: string[];
  metadata: Metadata | null;
  isLoading?: boolean;
}

export function Preview({ gifUrl, previewFrames, metadata, isLoading }: PreviewProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 bg-gray-50 rounded-xl">
        <svg className="animate-spin h-10 w-10 text-blue-500 mb-4" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <p className="text-gray-500">Processing your image...</p>
      </div>
    );
  }

  if (!gifUrl && previewFrames.length === 0) {
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
          Upload files and convert<br />to see preview
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* GIF Preview */}
      {gifUrl && (
        <div className="bg-black rounded-xl overflow-hidden flex items-center justify-center">
          <img
            src={gifUrl}
            alt="Converted GIF"
            className="max-w-full max-h-96 object-contain"
          />
        </div>
      )}

      {/* Metadata */}
      {metadata && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Image Info</h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {metadata.file_type && (
              <div>
                <span className="text-gray-500">Type:</span>{' '}
                <span className="text-gray-700 font-medium">{metadata.file_type.toUpperCase()}</span>
              </div>
            )}
            {metadata.num_slices && (
              <div>
                <span className="text-gray-500">Frames:</span>{' '}
                <span className="text-gray-700 font-medium">{metadata.num_slices}</span>
              </div>
            )}
            {metadata.shape && (
              <div className="col-span-2">
                <span className="text-gray-500">Dimensions:</span>{' '}
                <span className="text-gray-700 font-medium">
                  {Array.isArray(metadata.shape) ? metadata.shape.join(' x ') : String(metadata.shape)}
                </span>
              </div>
            )}
            {metadata.orientation && (
              <div>
                <span className="text-gray-500">Orientation:</span>{' '}
                <span className="text-gray-700 font-medium capitalize">{metadata.orientation}</span>
              </div>
            )}
            {metadata.modality && (
              <div>
                <span className="text-gray-500">Modality:</span>{' '}
                <span className="text-gray-700 font-medium">{metadata.modality}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Preview frames (before GIF loads) */}
      {!gifUrl && previewFrames.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Preview Frames</h4>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {previewFrames.map((frame, index) => (
              <img
                key={index}
                src={frame}
                alt={`Frame ${index + 1}`}
                className="h-24 rounded border border-gray-200 flex-shrink-0"
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
