# NIfTI/DICOM to GIF Converter

A web application for converting medical imaging files (NIfTI and DICOM) to animated GIFs. Built with FastAPI backend and React frontend.

**Author**: Jinhee Jang MD, PhD, Seoul St. Mary's Hospital

## Features

- **File Format Support**
  - NIfTI: `.nii`, `.nii.gz` (3D and 4D volumes)
  - DICOM: `.dcm`, `.dicom` (single files and series)
  - Folder upload for DICOM series
  - Multi-frame DICOM (cine loops, DSA, angiography)

- **Conversion Modes**
  - **3D Volume**: Animate through slices (axial, coronal, sagittal)
  - **2D Series**: Animate 4D time series, rotating MIP, or DICOM sequences

- **Interactive Preview**
  - Real-time preview with instant feedback
  - Client-side colormap and slice range adjustments
  - Play/pause animation with frame navigation
  - All transforms applied live before final conversion

- **Image Controls**
  - **Orientation**: Flip horizontal/vertical, rotate 90°, reverse slice order
  - **Slice Range**: Select percentage range of slices to include
  - **Window/Level**: Auto (percentile-based) or manual (HU values for CT)
  - **CT Presets**: Brain, Subdural, Stroke, Bone, Lung, Soft Tissue

- **Customization Options**
  - Animation speed (1-30 FPS)
  - Color maps (gray, viridis, plasma, hot, bone, jet)
  - Maximum GIF size (64-2048 pixels)
  - Maximum frame limit

- **Privacy Features**
  - Local server-side processing
  - Clear All button to remove uploaded data
  - No data sent to external servers

## Requirements

- Python 3.10+
- Node.js 18+

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/znee/NiftiDicom2gif.git
cd NiftiDicom2gif
```

### 2. Set up Python environment

```bash
# Create conda environment (recommended)
conda create -n nifti2gif python=3.10
conda activate nifti2gif

# Or use venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
cd backend
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
```

### 4. Run the application

**Terminal 1 - Backend:**
```bash
conda activate nifti2gif
cd backend
python main.py
# Or: uvicorn main:app --host 0.0.0.0 --port 8802 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 5. Access the application

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8802/docs

## Environment Configuration

The backend supports environment variables for configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host address |
| `PORT` | `8802` | Server port |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated for multiple) |

Example:
```bash
CORS_ORIGINS="https://example.com,https://app.example.com" PORT=8000 python main.py
```

## HTTPS Setup (Optional)

For HTTPS access (eliminates "Not Secure" browser warning):

```bash
# Generate self-signed certificate
mkdir -p certs
cd certs
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

Run with SSL:
```bash
uvicorn main:app --host 0.0.0.0 --port 8802 \
  --ssl-keyfile="../certs/key.pem" \
  --ssl-certfile="../certs/cert.pem"
```

## Project Structure

```
nifti_gif_app/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── requirements.txt         # Python dependencies
│   ├── routers/
│   │   └── convert.py           # API routes (/convert, /preview, /download)
│   ├── services/
│   │   ├── nifti_processor.py   # NIfTI loading and slicing
│   │   └── dicom_processor.py   # DICOM loading, sorting, windowing
│   └── utils/
│       ├── gif_generator.py     # GIF creation and preview frames
│       └── image_ops.py         # Shared image operations
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main React component
│   │   ├── api.ts               # API client functions
│   │   └── components/
│   │       ├── FileUploader.tsx       # Drag-drop file upload
│   │       ├── ConversionOptions.tsx  # Settings panel
│   │       ├── InteractivePreview.tsx # Canvas-based preview with transforms
│   │       ├── Preview.tsx            # Final GIF display
│   │       └── ActionButtons.tsx      # Download/clear buttons
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/convert` | Convert files to GIF with all settings |
| POST | `/api/preview` | Get grayscale frames for interactive preview |
| GET | `/api/download/{task_id}` | Download generated GIF |
| DELETE | `/api/clear` | Clear all temporary files |
| DELETE | `/api/clear/{task_id}` | Clear specific task |

### Convert Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `files` | File[] | required | NIfTI or DICOM files |
| `mode` | string | `volume` | `volume` or `series` |
| `orientation` | string | `axial` | `axial`, `coronal`, or `sagittal` |
| `fps` | int | `10` | Animation speed (1-30) |
| `colormap` | string | `gray` | Color scheme |
| `slice_start` | int | `0` | Start slice percentage (0-100) |
| `slice_end` | int | `100` | End slice percentage (0-100) |
| `window_mode` | string | `auto` | `auto` or `manual` |
| `window_width` | int | `98` | Window width |
| `window_level` | int | `50` | Window level |
| `flip_horizontal` | bool | `false` | Flip left-right |
| `flip_vertical` | bool | `false` | Flip up-down |
| `rotate90` | int | `0` | 90° rotations (0-3) |
| `reverse_slices` | bool | `false` | Reverse slice order |
| `max_gif_size` | int | `512` | Max dimension in pixels |
| `max_frames` | int | `0` | Max frames (0=unlimited) |

## Tech Stack

- **Backend**: FastAPI, uvicorn, nibabel, pydicom, imageio, Pillow, matplotlib
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, axios
- **Communication**: REST API with Vite proxy

## Disclaimers

### Privacy Notice
- This tool processes medical imaging data which may contain PHI
- Files are processed locally and temporarily stored during conversion
- Use "Clear All" to remove all uploaded data after use
- You are responsible for HIPAA/GDPR compliance

### Medical Disclaimer
- For visualization and educational purposes only
- Not suitable for clinical diagnosis or medical decision-making
- Image processing may alter appearance - always refer to original files for clinical use

## License

MIT License

## Acknowledgments

- [NiBabel](https://nipy.org/nibabel/) - NIfTI file processing
- [pydicom](https://pydicom.github.io/) - DICOM file processing
- [imageio](https://imageio.readthedocs.io/) - GIF generation
- [Pillow](https://pillow.readthedocs.io/) - Image processing
