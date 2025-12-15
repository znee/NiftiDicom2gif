export type Orientation = 'axial' | 'coronal' | 'sagittal';
export type Colormap = 'gray' | 'viridis' | 'plasma' | 'hot' | 'bone' | 'jet';
export type Mode = 'volume' | 'series';
export type WindowMode = 'auto' | 'manual';

export interface ConversionSettings {
  mode: Mode;
  orientation: Orientation;
  fps: number;
  colormap: Colormap;
  sliceStart: number;
  sliceEnd: number;
  windowMode: WindowMode;
  windowMin: number;
  windowMax: number;
}

interface ConversionOptionsProps {
  settings: ConversionSettings;
  onSettingsChange: (settings: ConversionSettings) => void;
  disabled?: boolean;
}

export function ConversionOptions({
  settings,
  onSettingsChange,
  disabled,
}: ConversionOptionsProps) {
  const updateSetting = <K extends keyof ConversionSettings>(
    key: K,
    value: ConversionSettings[K]
  ) => {
    onSettingsChange({ ...settings, [key]: value });
  };

  const updateSliceRange = (start: number, end: number) => {
    if (start >= end - 5) {
      if (start === settings.sliceStart) {
        end = Math.min(100, start + 5);
      } else {
        start = Math.max(0, end - 5);
      }
    }
    onSettingsChange({ ...settings, sliceStart: start, sliceEnd: end });
  };

  const updateWindowRange = (min: number, max: number) => {
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
    <div className="space-y-4">
      {/* Row 1: Mode + Orientation */}
      <div className="grid grid-cols-2 gap-3">
        {/* Mode Selection */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Mode</label>
          <div className="flex gap-1">
            <button
              onClick={() => updateSetting('mode', 'volume')}
              className={`flex-1 px-2 py-1.5 rounded text-xs font-medium transition-all ${
                settings.mode === 'volume'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
              }`}
              disabled={disabled}
            >
              3D Vol
            </button>
            <button
              onClick={() => updateSetting('mode', 'series')}
              className={`flex-1 px-2 py-1.5 rounded text-xs font-medium transition-all ${
                settings.mode === 'series'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
              }`}
              disabled={disabled}
            >
              2D Seq
            </button>
          </div>
        </div>

        {/* Orientation */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Orientation</label>
          <div className="flex gap-1">
            {(['axial', 'coronal', 'sagittal'] as Orientation[]).map((o) => (
              <button
                key={o}
                onClick={() => updateSetting('orientation', o)}
                className={`flex-1 px-1 py-1.5 rounded text-xs font-medium capitalize transition-all ${
                  settings.orientation === o
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
                }`}
                disabled={disabled || settings.mode === 'series'}
              >
                {o.slice(0, 3)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Row 2: FPS + Colormap */}
      <div className="grid grid-cols-2 gap-3">
        {/* FPS */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Speed: {settings.fps} FPS
          </label>
          <input
            type="range"
            min="1"
            max="30"
            value={settings.fps}
            onChange={(e) => updateSetting('fps', parseInt(e.target.value))}
            className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
            disabled={disabled}
          />
        </div>

        {/* Colormap */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Colormap</label>
          <select
            value={settings.colormap}
            onChange={(e) => updateSetting('colormap', e.target.value as Colormap)}
            className="w-full px-2 py-1.5 text-xs border border-gray-200 rounded bg-white"
            disabled={disabled}
          >
            {(['gray', 'viridis', 'plasma', 'hot', 'bone', 'jet'] as Colormap[]).map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Row 3: Slice Range */}
      <div className="bg-gray-50 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-medium text-gray-600">
            Slice Range: {settings.sliceStart}% - {settings.sliceEnd}%
          </label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="text-xs text-gray-400">Start</span>
            <input
              type="range"
              min="0"
              max="95"
              value={settings.sliceStart}
              onChange={(e) => updateSliceRange(parseInt(e.target.value), settings.sliceEnd)}
              className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              disabled={disabled}
            />
          </div>
          <div>
            <span className="text-xs text-gray-400">End</span>
            <input
              type="range"
              min="5"
              max="100"
              value={settings.sliceEnd}
              onChange={(e) => updateSliceRange(settings.sliceStart, parseInt(e.target.value))}
              className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              disabled={disabled}
            />
          </div>
        </div>
      </div>

      {/* Row 4: Window/Level */}
      <div className="bg-gray-50 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-medium text-gray-600">
            Intensity: {settings.windowMin}% - {settings.windowMax}%
          </label>
          <div className="flex gap-1">
            <button
              onClick={() => updateSetting('windowMode', 'auto')}
              className={`px-2 py-0.5 rounded text-xs transition-all ${
                settings.windowMode === 'auto'
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}
              disabled={disabled}
            >
              Auto
            </button>
            <button
              onClick={() => updateSetting('windowMode', 'manual')}
              className={`px-2 py-0.5 rounded text-xs transition-all ${
                settings.windowMode === 'manual'
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-200 text-gray-600'
              }`}
              disabled={disabled}
            >
              Manual
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="text-xs text-gray-400">
              {settings.windowMode === 'auto' ? 'Low %ile' : 'Min'}
            </span>
            <input
              type="range"
              min="0"
              max={settings.windowMode === 'auto' ? '49' : '99'}
              value={settings.windowMin}
              onChange={(e) => updateWindowRange(parseInt(e.target.value), settings.windowMax)}
              className={`w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer ${
                settings.windowMode === 'auto' ? 'accent-green-500' : 'accent-orange-500'
              }`}
              disabled={disabled}
            />
          </div>
          <div>
            <span className="text-xs text-gray-400">
              {settings.windowMode === 'auto' ? 'High %ile' : 'Max'}
            </span>
            <input
              type="range"
              min={settings.windowMode === 'auto' ? '51' : '1'}
              max="100"
              value={settings.windowMax}
              onChange={(e) => updateWindowRange(settings.windowMin, parseInt(e.target.value))}
              className={`w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer ${
                settings.windowMode === 'auto' ? 'accent-green-500' : 'accent-orange-500'
              }`}
              disabled={disabled}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
