overview.

Build an app, easy-to-use dicom or nifti to animiated gifs.
There are some solutions, but it is not very useuful.

Animated gif can be two major ways.
- 3D volume to 2D slices to gif, axial coronal or sagittal, 3D nifti or a set of 2D dicom
- series of 2D slices to gif, and in this case, might use dicom instread of nifti

Need option for speed of animation

Eaay and clean modern UI for upload and download images.

Clean button, for privary issue.


Check this repo.
https://github.com/miykael/gif_your_nifti


use this conda env for default
/opt/homebrew/Caskroom/miniforge/base/envs/wmh


## Standalone App Plan

Build a cross-platform standalone desktop application from this web app.

### Recommended Approach: Tauri + React

**Why Tauri:**
- Reuses existing React frontend code
- Lightweight (~10-30MB vs Electron's 150MB+)
- Cross-platform (Mac/Windows/Linux)
- Uses system webview (no bundled Chromium)
- Rust backend for performance

**Architecture:**
```
nifti_gif_standalone/
├── src-tauri/           # Rust/Tauri backend
│   ├── src/
│   │   └── main.rs      # Tauri app entry
│   └── tauri.conf.json  # Tauri config
├── src/                 # React frontend (copy from webapp)
├── python-sidecar/      # Bundled Python backend
│   ├── main.py          # FastAPI app (simplified)
│   └── requirements.txt
└── package.json
```

**Implementation Steps:**
1. Create new project with `npm create tauri-app`
2. Copy React frontend from `nifti_gif_app/frontend/src`
3. Bundle Python backend with PyInstaller as sidecar process
4. Tauri spawns Python sidecar on app start
5. Frontend communicates with local Python API
6. Package with `tauri build` for each platform

**Alternative Approaches:**
- **Electron**: Heavier but more mature ecosystem
- **PyWebView**: Python-native, simpler but less polished
- **Native Swift/SwiftUI**: Mac-only, best performance


