export type Orientation = 'axial' | 'coronal' | 'sagittal';
export type Colormap = 'gray' | 'viridis' | 'plasma' | 'hot' | 'bone' | 'jet';
export type Mode = 'volume' | 'series';
export type WindowMode = 'auto' | 'manual';

export interface ConversionSettings {
  mode: Mode;
  orientation: Orientation;
  fps: number;
  colormap: Colormap;
  // Slice range (percentage 0-100)
  sliceStart: number;
  sliceEnd: number;
  // Dynamic range / Window-Level
  windowMode: WindowMode;
  windowMin: number;  // percentile for auto, absolute for manual
  windowMax: number;
}

interface ConversionOptionsProps {
  settings: ConversionSettings;
  onSettingsChange: (settings: ConversionSettings) => void;
  onConvert: () => void;
  disabled?: boolean;
  isConverting?: boolean;
  hasFiles: boolean;
}

export function ConversionOptions({
  settings,
  onSettingsChange,
  onConvert,
  disabled,
  isConverting,
  hasFiles,
}: ConversionOptionsProps) {
  const updateSetting = <K extends keyof ConversionSettings>(
    key: K,
    value: ConversionSettings[K]
  ) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  const updateSliceRange = (start: number, end: number) => {
    // Ensure start < end with at least 5% range
    if (start >= end - 5) {
      if (start === settings.sliceStart) {
        // User is dragging end slider
        end = Math.min(100, start + 5);
      } else {
        // User is dragging start slider
        start = Math.max(0, end - 5);
      }
    }
    onSettingsChange({ ...settings, sliceStart: start, sliceEnd: end });
  };

  const updateWindowRange = (min: number, max: number) => {
    // Ensure min < max
    if (min >= max - 1) {
      if (min === settings.windowMin) {
        max = Math.min(100, min + 1);
      } else {
        min = Math.max(0, max - 1);
      }
    }
    onSettingsChange({ ...settings, windowMin: min, windowMax: max });
  };

  return (
    <div className="space-y-6">
      {/* Mode Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Conversion Mode
        </label>
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => updateSetting('mode', 'volume')}
            className={`
              px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all
              ${settings.mode === 'volume'
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 hover:border-gray-300 text-gray-600'
              }
            `}
            disabled={disabled}
          >
            <div className="font-semibold">3D Volume</div>
            <div className="text-xs opacity-75 mt-1">Slices through volume</div>
          </button>
          <button
            onClick={() => updateSetting('mode', 'series')}
            className={`
              px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all
              ${settings.mode === 'series'
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 hover:border-gray-300 text-gray-600'
              }
            `}
            disabled={disabled}
          >
            <div className="font-semibold">2D Series</div>
            <div className="text-xs opacity-75 mt-1">Sequential frames</div>
          </button>
        </div>
      </div>

      {/* Orientation (only for volume mode) */}
      {settings.mode === 'volume' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Orientation
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(['axial', 'coronal', 'sagittal'] as Orientation[]).map((orientation) => (
              <button
                key={orientation}
                onClick={() => updateSetting('orientation', orientation)}
                className={`
                  px-3 py-2 rounded-lg border text-sm font-medium capitalize transition-all
                  ${settings.orientation === orientation
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-600'
                  }
                `}
                disabled={disabled}
              >
                {orientation}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Slice Range Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Slice Range: {settings.sliceStart}% - {settings.sliceEnd}%
        </label>
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Start: {settings.sliceStart}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="95"
              value={settings.sliceStart}
              onChange={(e) => updateSliceRange(parseInt(e.target.value), settings.sliceEnd)}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              disabled={disabled}
            />
          </div>
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>End: {settings.sliceEnd}%</span>
            </div>
            <input
              type="range"
              min="5"
              max="100"
              value={settings.sliceEnd}
              onChange={(e) => updateSliceRange(settings.sliceStart, parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              disabled={disabled}
            />
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Exclude slices from start/end (e.g., remove empty slices)
        </p>
      </div>

      {/* Dynamic Range / Window-Level */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Intensity Range (Window/Level)
        </label>
        <div className="grid grid-cols-2 gap-2 mb-3">
          <button
            onClick={() => updateSetting('windowMode', 'auto')}
            className={`
              px-3 py-2 rounded-lg border text-sm font-medium transition-all
              ${settings.windowMode === 'auto'
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 hover:border-gray-300 text-gray-600'
              }
            `}
            disabled={disabled}
          >
            Auto (Percentile)
          </button>
          <button
            onClick={() => updateSetting('windowMode', 'manual')}
            className={`
              px-3 py-2 rounded-lg border text-sm font-medium transition-all
              ${settings.windowMode === 'manual'
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 hover:border-gray-300 text-gray-600'
              }
            `}
            disabled={disabled}
          >
            Manual
          </button>
        </div>

        {settings.windowMode === 'auto' ? (
          <div className="space-y-3 bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600">
              Auto mode clips intensities at percentiles to handle outliers
            </p>
            <div>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Lower percentile: {settings.windowMin}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="49"
                value={settings.windowMin}
                onChange={(e) => updateWindowRange(parseInt(e.target.value), settings.windowMax)}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-500"
                disabled={disabled}
              />
            </div>
            <div>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Upper percentile: {settings.windowMax}%</span>
              </div>
              <input
                type="range"
                min="51"
                max="100"
                value={settings.windowMax}
                onChange={(e) => updateWindowRange(settings.windowMin, parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-500"
                disabled={disabled}
              />
            </div>
            <p className="text-xs text-gray-400">
              Default: 1% - 99% (recommended for most images)
            </p>
          </div>
        ) : (
          <div className="space-y-3 bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-600">
              Manual mode: set exact intensity range (0-100% of data range)
            </p>
            <div>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Min intensity: {settings.windowMin}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="99"
                value={settings.windowMin}
                onChange={(e) => updateWindowRange(parseInt(e.target.value), settings.windowMax)}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
                disabled={disabled}
              />
            </div>
            <div>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Max intensity: {settings.windowMax}%</span>
              </div>
              <input
                type="range"
                min="1"
                max="100"
                value={settings.windowMax}
                onChange={(e) => updateWindowRange(settings.windowMin, parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
                disabled={disabled}
              />
            </div>
            <p className="text-xs text-gray-400">
              Useful for specific tissue windows (e.g., brain, bone, lung)
            </p>
          </div>
        )}
      </div>

      {/* Animation Speed */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Animation Speed: {settings.fps} FPS
        </label>
        <input
          type="range"
          min="1"
          max="30"
          value={settings.fps}
          onChange={(e) => updateSetting('fps', parseInt(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
          disabled={disabled}
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>Slow</span>
          <span>Fast</span>
        </div>
      </div>

      {/* Colormap */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Color Map
        </label>
        <div className="grid grid-cols-3 gap-2">
          {(['gray', 'viridis', 'plasma', 'hot', 'bone', 'jet'] as Colormap[]).map((cmap) => (
            <button
              key={cmap}
              onClick={() => updateSetting('colormap', cmap)}
              className={`
                px-3 py-2 rounded-lg border text-sm font-medium capitalize transition-all
                ${settings.colormap === cmap
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-gray-300 text-gray-600'
                }
              `}
              disabled={disabled}
            >
              {cmap}
            </button>
          ))}
        </div>
      </div>

      {/* Convert Button */}
      <button
        onClick={onConvert}
        disabled={disabled || !hasFiles || isConverting}
        className={`
          w-full py-3 px-4 rounded-xl font-semibold text-white transition-all
          ${disabled || !hasFiles || isConverting
            ? 'bg-gray-300 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800 shadow-lg hover:shadow-xl'
          }
        `}
      >
        {isConverting ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
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
            Converting...
          </span>
        ) : (
          'Convert to GIF'
        )}
      </button>
    </div>
  );
}
