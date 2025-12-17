export type Orientation = 'axial' | 'coronal' | 'sagittal';
export type Colormap = 'gray' | 'viridis' | 'plasma' | 'hot' | 'bone' | 'jet';
export type Mode = 'volume' | 'series';
export type WindowMode = 'auto' | 'manual';

// CT Window presets (Hounsfield Units: Width / Level)
export const CT_PRESETS = {
  brain: { name: 'Brain', width: 80, level: 40 },
  abdomen: { name: 'Abdomen', width: 340, level: 40 },
  lung: { name: 'Lung', width: 1500, level: -600 },
  bone: { name: 'Bone', width: 2000, level: 300 },
} as const;

export interface ConversionSettings {
  mode: Mode;
  orientation: Orientation;
  fps: number;
  colormap: Colormap;
  sliceStart: number;
  sliceEnd: number;
  windowMode: WindowMode;
  windowLevel: number;
  windowWidth: number;
  // Image transform controls
  flipHorizontal: boolean;
  flipVertical: boolean;
  rotate90: number;  // 0, 1, 2, or 3 (number of 90-degree CW rotations)
  reverseSlices: boolean;
  // GIF options
  maxGifSize: number;
  maxFrames: number;
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

  const updateWindowLevel = (level: number) => {
    onSettingsChange({ ...settings, windowLevel: level });
  };

  const updateWindowWidth = (width: number) => {
    width = Math.max(1, width);
    onSettingsChange({ ...settings, windowWidth: width });
  };

  const applyPreset = (preset: keyof typeof CT_PRESETS) => {
    const p = CT_PRESETS[preset];
    onSettingsChange({
      ...settings,
      windowMode: 'manual',
      windowLevel: p.level,
      windowWidth: p.width,
    });
  };

  const rotateClockwise = () => {
    const newRotation = ((settings.rotate90 + 1) % 4) as 0 | 1 | 2 | 3;
    updateSetting('rotate90', newRotation);
  };

  return (
    <div className="space-y-2">
      {/* Row 1: Mode + Orientation */}
      <div className="grid grid-cols-2 gap-2">
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
              3D Vol
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
              2D Seq
            </button>
          </div>
        </div>

        {/* Orientation */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">View</label>
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
      </div>

      {/* Row 2: Image Transform Controls */}
      <div className="bg-purple-50 rounded-lg p-2">
        <label className="block text-xs font-medium text-gray-600 mb-1">Image Adjust</label>
        <div className="flex gap-1">
          {/* Flip Horizontal */}
          <button
            onClick={() => updateSetting('flipHorizontal', !settings.flipHorizontal)}
            className={`flex-1 px-1 py-1.5 rounded text-xs font-medium transition-all ${
              settings.flipHorizontal
                ? 'bg-purple-500 text-white'
                : 'bg-white hover:bg-gray-100 text-gray-600 border border-gray-200'
            }`}
            disabled={disabled}
            title="Flip Left/Right"
          >
            <span className="flex items-center justify-center gap-0.5">
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M7 16l-4-4 4-4M17 16l4-4-4-4M12 3v18" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              L/R
            </span>
          </button>

          {/* Flip Vertical */}
          <button
            onClick={() => updateSetting('flipVertical', !settings.flipVertical)}
            className={`flex-1 px-1 py-1.5 rounded text-xs font-medium transition-all ${
              settings.flipVertical
                ? 'bg-purple-500 text-white'
                : 'bg-white hover:bg-gray-100 text-gray-600 border border-gray-200'
            }`}
            disabled={disabled}
            title="Flip Up/Down"
          >
            <span className="flex items-center justify-center gap-0.5">
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M16 7l-4-4-4 4M16 17l-4 4-4-4M3 12h18" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              U/D
            </span>
          </button>

          {/* Rotate 90 CW */}
          <button
            onClick={rotateClockwise}
            className={`flex-1 px-1 py-1.5 rounded text-xs font-medium transition-all ${
              settings.rotate90 > 0
                ? 'bg-purple-500 text-white'
                : 'bg-white hover:bg-gray-100 text-gray-600 border border-gray-200'
            }`}
            disabled={disabled}
            title="Rotate 90° clockwise"
          >
            <span className="flex items-center justify-center gap-0.5">
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12a9 9 0 11-3-6.7M21 3v6h-6" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {settings.rotate90 > 0 ? `${settings.rotate90 * 90}°` : 'Rot'}
            </span>
          </button>

          {/* Reverse Slices */}
          <button
            onClick={() => updateSetting('reverseSlices', !settings.reverseSlices)}
            className={`flex-1 px-1 py-1.5 rounded text-xs font-medium transition-all ${
              settings.reverseSlices
                ? 'bg-purple-500 text-white'
                : 'bg-white hover:bg-gray-100 text-gray-600 border border-gray-200'
            }`}
            disabled={disabled}
            title="Reverse slice order"
          >
            <span className="flex items-center justify-center gap-0.5">
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M7 4v16M17 4v16M4 12h16M4 7l3 5-3 5M20 7l-3 5 3 5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Rev
            </span>
          </button>
        </div>
      </div>

      {/* Row 3: FPS + Colormap */}
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

      {/* Row 4: Slice Range */}
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

      {/* Row 5: Window/Level with CT Presets */}
      <div className="bg-gray-50 rounded-lg p-2">
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium text-gray-600">
            {settings.windowMode === 'auto'
              ? `W/L: ${settings.windowWidth}% / ${settings.windowLevel}%`
              : `W/L: ${settings.windowWidth} / ${settings.windowLevel} HU`
            }
          </label>
        </div>

        {/* Window Presets: Auto + CT presets */}
        <div className="flex gap-1 mb-2">
          <button
            onClick={() => onSettingsChange({ ...settings, windowMode: 'auto', windowLevel: 50, windowWidth: 98 })}
            className={`flex-1 px-1 py-1 rounded text-xs transition-all ${
              settings.windowMode === 'auto'
                ? 'bg-green-500 text-white'
                : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
            }`}
            disabled={disabled}
            title="Auto (percentile-based)"
          >
            Auto
          </button>
          {Object.entries(CT_PRESETS).map(([key, preset]) => (
            <button
              key={key}
              onClick={() => applyPreset(key as keyof typeof CT_PRESETS)}
              className={`flex-1 px-1 py-1 rounded text-xs transition-all ${
                settings.windowMode === 'manual' &&
                settings.windowLevel === preset.level &&
                settings.windowWidth === preset.width
                  ? 'bg-orange-500 text-white'
                  : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
              }`}
              disabled={disabled}
              title={`${preset.name} (W:${preset.width} L:${preset.level})`}
            >
              {preset.name.slice(0, 4)}
            </button>
          ))}
        </div>

        {/* Width and Level sliders */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-xs text-gray-400">
              Width {settings.windowMode === 'auto' ? '(%)' : '(HU)'}
            </span>
            <input
              type="range"
              min={settings.windowMode === 'auto' ? 2 : 1}
              max={settings.windowMode === 'auto' ? 100 : 4000}
              value={settings.windowWidth}
              onChange={(e) => {
                updateWindowWidth(parseInt(e.target.value));
              }}
              className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
              disabled={disabled}
            />
          </div>
          <div>
            <span className="text-xs text-gray-400">
              Level {settings.windowMode === 'auto' ? '(%)' : '(HU)'}
            </span>
            <input
              type="range"
              min={settings.windowMode === 'auto' ? 1 : -1000}
              max={settings.windowMode === 'auto' ? 99 : 3000}
              value={settings.windowLevel}
              onChange={(e) => {
                updateWindowLevel(parseInt(e.target.value));
              }}
              className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
              disabled={disabled}
            />
          </div>
        </div>
      </div>

      {/* Row 6: GIF Size Options */}
      <div className="bg-gray-50 rounded-lg p-2">
        <label className="text-xs font-medium text-gray-600 mb-1 block">
          GIF: {settings.maxGifSize}px {settings.maxFrames > 0 ? `/ max ${settings.maxFrames}f` : ''}
        </label>
        <div className="grid grid-cols-2 gap-2">
          <select
            value={settings.maxGifSize}
            onChange={(e) => updateSetting('maxGifSize', parseInt(e.target.value))}
            className="w-full px-2 py-1 text-xs border border-gray-200 rounded bg-white"
            disabled={disabled}
          >
            <option value={256}>256px</option>
            <option value={384}>384px</option>
            <option value={512}>512px</option>
            <option value={640}>640px</option>
            <option value={768}>768px</option>
          </select>
          <select
            value={settings.maxFrames}
            onChange={(e) => updateSetting('maxFrames', parseInt(e.target.value))}
            className="w-full px-2 py-1 text-xs border border-gray-200 rounded bg-white"
            disabled={disabled}
          >
            <option value={0}>All frames</option>
            <option value={50}>50 frames</option>
            <option value={100}>100 frames</option>
            <option value={150}>150 frames</option>
            <option value={200}>200 frames</option>
          </select>
        </div>
      </div>
    </div>
  );
}
