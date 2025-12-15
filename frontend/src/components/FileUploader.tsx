import { useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';

interface FileUploaderProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  disabled?: boolean;
}

export function FileUploader({ files, onFilesChange, disabled }: FileUploaderProps) {
  const folderInputRef = useRef<HTMLInputElement>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Filter to only accepted file types
    const validFiles = acceptedFiles.filter(file => {
      const name = file.name.toLowerCase();
      return name.endsWith('.nii') ||
             name.endsWith('.nii.gz') ||
             name.endsWith('.dcm') ||
             name.endsWith('.dicom') ||
             !name.includes('.'); // DICOM files often have no extension
    });
    onFilesChange([...files, ...validFiles]);
  }, [files, onFilesChange]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled,
    noClick: false,
    noKeyboard: false,
    // Accept all files, we filter in onDrop
    accept: undefined,
  });

  const handleFolderSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList) return;

    const validFiles: File[] = [];
    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const name = file.name.toLowerCase();
      if (name.endsWith('.nii') ||
          name.endsWith('.nii.gz') ||
          name.endsWith('.dcm') ||
          name.endsWith('.dicom') ||
          !name.includes('.')) {
        validFiles.push(file);
      }
    }

    if (validFiles.length > 0) {
      onFilesChange([...files, ...validFiles]);
    }

    // Reset input so same folder can be selected again
    e.target.value = '';
  }, [files, onFilesChange]);

  const openFolderDialog = () => {
    folderInputRef.current?.click();
  };

  const removeFile = (index: number) => {
    const newFiles = files.filter((_, i) => i !== index);
    onFilesChange(newFiles);
  };

  const clearAllFiles = () => {
    onFilesChange([]);
  };

  const detectFileType = (filename: string): string => {
    const lower = filename.toLowerCase();
    if (lower.endsWith('.nii') || lower.endsWith('.nii.gz')) {
      return 'NIfTI';
    }
    return 'DICOM';
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full">
      {/* Hidden folder input for selecting directories */}
      <input
        ref={folderInputRef}
        type="file"
        // @ts-expect-error webkitdirectory is a non-standard attribute for folder selection
        webkitdirectory="true"
        multiple
        onChange={handleFolderSelect}
        className="hidden"
        disabled={disabled}
      />

      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
          transition-all duration-200 ease-in-out
          ${isDragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3">
          <svg
            className={`w-12 h-12 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          {isDragActive ? (
            <p className="text-blue-600 font-medium">Drop files or folder here...</p>
          ) : (
            <>
              <p className="text-gray-600 font-medium">
                Drag & drop files or folder here, or click to select files
              </p>
              <p className="text-sm text-gray-400">
                Supports NIfTI (.nii, .nii.gz) and DICOM (.dcm) files
              </p>
            </>
          )}
        </div>
      </div>

      {/* Folder select button */}
      <div className="mt-3 flex justify-center">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            openFolderDialog();
          }}
          disabled={disabled}
          className={`
            px-4 py-2 text-sm font-medium rounded-lg border
            transition-colors flex items-center gap-2
            ${disabled
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed border-gray-200'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 hover:border-gray-400'
            }
          `}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
            />
          </svg>
          Select DICOM Folder
        </button>
      </div>

      {files.length > 0 && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-gray-700">
              Selected files ({files.length})
            </h4>
            <button
              onClick={clearAllFiles}
              disabled={disabled}
              className="text-xs text-red-500 hover:text-red-700 transition-colors"
            >
              Clear all
            </button>
          </div>
          <ul className="space-y-2 max-h-48 overflow-y-auto">
            {files.map((file, index) => (
              <li
                key={`${file.name}-${index}`}
                className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-2"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className={`
                    text-xs font-medium px-2 py-1 rounded
                    ${detectFileType(file.name) === 'NIfTI'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-green-100 text-green-700'
                    }
                  `}>
                    {detectFileType(file.name)}
                  </span>
                  <span className="text-sm text-gray-700 truncate">
                    {file.name}
                  </span>
                  <span className="text-xs text-gray-400">
                    {formatFileSize(file.size)}
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(index);
                  }}
                  className="text-gray-400 hover:text-red-500 transition-colors p-1"
                  disabled={disabled}
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
