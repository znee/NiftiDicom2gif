interface ActionButtonsProps {
  gifUrl: string | null;
  taskId: string | null;
  onClear: () => void;
  onClearAll: () => void;
  disabled?: boolean;
}

export function ActionButtons({
  gifUrl,
  taskId,
  onClear,
  onClearAll,
  disabled,
}: ActionButtonsProps) {
  const handleDownload = () => {
    if (!gifUrl) return;

    // Create download link
    const link = document.createElement('a');
    link.href = gifUrl;
    link.download = `medical_image_${taskId || 'converted'}.gif`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex gap-3">
      {/* Download Button */}
      <button
        onClick={handleDownload}
        disabled={!gifUrl || disabled}
        className={`
          flex-1 py-3 px-4 rounded-xl font-semibold transition-all flex items-center justify-center gap-2
          ${!gifUrl || disabled
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-green-600 hover:bg-green-700 text-white shadow-lg hover:shadow-xl'
          }
        `}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        Download GIF
      </button>

      {/* Clear Button (Privacy) */}
      <button
        onClick={onClear}
        disabled={!gifUrl || disabled}
        className={`
          py-3 px-4 rounded-xl font-semibold transition-all flex items-center justify-center gap-2
          ${!gifUrl || disabled
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
          }
        `}
        title="Clear current result"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
          />
        </svg>
      </button>

      {/* Clear All Button */}
      <button
        onClick={onClearAll}
        disabled={disabled}
        className={`
          py-3 px-4 rounded-xl font-semibold transition-all flex items-center justify-center gap-2
          ${disabled
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-red-100 hover:bg-red-200 text-red-700'
          }
        `}
        title="Clear all data (privacy)"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        Clear All
      </button>
    </div>
  );
}
