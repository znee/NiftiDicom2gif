export type Orientation = 'axial' | 'coronal' | 'sagittal';
export type Colormap = 'gray' | 'viridis' | 'plasma' | 'hot' | 'bone' | 'jet';
export type Mode = 'volume' | 'series';
export type WindowMode = 'auto' | 'manual';

// CT Window presets
export const CT_PRESETS = {
  brain: { name: 'Brain', windowMin: 25, windowMax: 35 },
  abdomen: { name: 'Abdomen', windowMin: 20, windowMax: 40 },
  lung: { name: 'Lung', windowMin: 0, windowMax: 60 },
  bone: { name: 'Bone', windowMin: 30, windowMax: 80 },
  soft: { name: 'Soft', windowMin: 22, windowMax: 38 },
} as const;

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
  flipHorizontal: boolean;
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

  const applyPreset = (preset: keyof typeof CT_PRESETS) => {
    const p = CT_PRESETS[preset];
    onSettingsChange({
      ...settings,
      windowMode: 'manual',
      windowMin: p.windowMin,
      windowMax: p.windowMax,
    });
  };

  return (
    <div className="space-y-3">
      {/* Row 1: Mode + Orientation + Flip */}
      <div className="grid grid-cols-3 gap-2">
        {/* Mode Selection */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Mode</label>
          <div className="flex gap-1">
            <button
              onClick={() => updateSetting('mode', 'volume')}
              className={`flex-1 px-1 py-1.5 rounded text-xs font-medium transition-all ${
                settings.mode === 'volume'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
              }`}
              disabled={disabled}
            >
              3D
            </button>
            <button
              onClick={() => updateSetting('mode', 'series')}
              className={`flex-1 px-1 py-1.5 rounded text-xs font-medium transition-all ${
                settings.mode === 'series'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
              }`}
              disabled={disabled}
            >
              2D
            </button>
          </div>
        </div>

        {/* Orientation */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Orient</label>
          <div className="flex gap-1">
            {(['axial', 'coronal', 'sagittal'] as Orientation[]).map((o) => (
              <button
                key={o}
                onClick={() => updateSetting('orientation', o)}
                className={`flex-1 px-0.5 py-1.5 rounded text-xs font-medium transition-all ${
                  settings.orientation === o
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
                }`}
                disabled={disabled || settings.mode === 'series'}
                title={o}
              >
                {o[0].toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Flip */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Flip L/R</label>
          <button
            onClick={() => updateSetting('flipHorizontal', !settings.flipHorizontal)}
            className={`w-full px-2 py-1.5 rounded text-xs font-medium transition-all ${
              settings.flipHorizontal
                ? 'bg-purple-500 text-white'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
            }`}
            disabled={disabled}
          >
            {settings.flipHorizontal ? 'Flipped' : 'Normal'}
          </button>
        </div>
      </div>

      {/* Row 2: FPS + Colormap */}
      <div className="grid grid-cols-2 gap-2">
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
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Colormap</label>
          <select
            value={settings.colormap}
            onChange={(e) => updateSetting('colormap', e.target.value as Colormap)}
            className="w-full px-2 py-1 text-xs border border-gray-200 rounded bg-white"
            disabled={disabled}
          >
            {(['gray', 'viridis', 'plasma', 'hot', 'bone', 'jet'] as Colormap[]).map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Row 3: Slice Range */}
      <div className="bg-gray-50 rounded-lg p-2">
        <label className="text-xs font-medium text-gray-600">
          Slice: {settings.sliceStart}% - {settings.sliceEnd}%
        </label>
        <div className="grid grid-cols-2 gap-2 mt-1">
          <input
            type="range"
            min="0"
            max="95"
            value={settings.sliceStart}
            onChange={(e) => updateSliceRange(parseInt(e.target.value), settings.sliceEnd)}
            className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
            disabled={disabled}
          />
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

      {/* Row 4: Window/Level with CT Presets */}
      <div className="bg-gray-50 rounded-lg p-2">
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium text-gray-600">
            Window: {settings.windowMin}% - {settings.windowMax}%
          </label>
          <button
            onClick={() => onSettingsChange({ ...settings, windowMode: 'auto', windowMin: 1, windowMax: 99 })}
            className={`px-1.5 py-0.5 rounded text-xs transition-all ${
              settings.windowMode === 'auto'
                ? 'bg-green-500 text-white'
                : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
            }`}
            disabled={disabled}
          >
            Auto
          </button>
        </div>

        {/* CT Presets */}
        <div className="flex gap-1 mb-2">
          {Object.entries(CT_PRESETS).map(([key, preset]) => (
            <button
              key={key}
              onClick={() => applyPreset(key as keyof typeof CT_PRESETS)}
              className={`flex-1 px-1 py-1 rounded text-xs transition-all ${
                settings.windowMode === 'manual' &&
                settings.windowMin === preset.windowMin &&
                settings.windowMax === preset.windowMax
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
              }`}
              disabled={disabled}
              title={preset.name}
            >
              {preset.name.slice(0, 3)}
            </button>
          ))}
        </div>

        {/* Manual sliders */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-xs text-gray-400">Min</span>
            <input
              type="range"
              min="0"
              max="99"
              value={settings.windowMin}
              onChange={(e) => {
                updateSetting('windowMode', 'manual');
                updateWindowRange(parseInt(e.target.value), settings.windowMax);
              }}
              className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
              disabled={disabled}
            />
          </div>
          <div>
            <span className="text-xs text-gray-400">Max</span>
            <input
              type="range"
              min="1"
              max="100"
              value={settings.windowMax}
              onChange={(e) => {
                updateSetting('windowMode', 'manual');
                updateWindowRange(settings.windowMin, parseInt(e.target.value));
              }}
              className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
              disabled={disabled}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
