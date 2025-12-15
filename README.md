# NIfTI/DICOM to GIF Converter

A web application for converting medical imaging files (NIfTI and DICOM) to animated GIFs. Built with FastAPI backend and React frontend.

## Features

- **File Format Support**
  - NIfTI: `.nii`, `.nii.gz` (3D and 4D volumes)
  - DICOM: `.dcm`, `.dicom` (single files and series)
  - Folder upload for DICOM series

- **Conversion Modes**
  - **3D Volume**: Animate through slices (axial, coronal, sagittal)
  - **2D Series**: Animate 4D time series or DICOM sequences

- **Customization Options**
  - Slice range selection (exclude first/last slices)
  - Dynamic range / Window-Level controls (auto percentile or manual)
  - Animation speed (1-30 FPS)
  - Color maps (gray, viridis, plasma, hot, bone, jet)

- **Privacy Features**
  - Local server-side processing
  - Clear All button to remove uploaded data
  - No data sent to external servers

## Requirements

- Python 3.10+ with conda
- Node.js 18+
- OpenSSL (for generating certificates)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/znee/NiftiDicom2gif.git
cd NiftiDicom2gif
```

### 2. Set up Python environment

```bash
# Create conda environment
conda create -n nifti2gif python=3.10
conda activate nifti2gif

# Install Python dependencies
cd backend
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
```

### 4. Generate SSL certificates

```bash
mkdir -p certs
cd certs
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

## Running the Application

### Option 1: Use the startup script

```bash
chmod +x run.sh
./run.sh
```

### Option 2: Manual startup

**Terminal 1 - Backend:**
```bash
conda activate nifti2gif
cd backend
uvicorn main:app --host 0.0.0.0 --port 8802 \
  --ssl-keyfile="../certs/key.pem" \
  --ssl-certfile="../certs/cert.pem"
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Access the application

- **Frontend**: https://localhost:8801
- **API Docs**: https://localhost:8802/docs

> Note: Accept the self-signed certificate warning in your browser on first visit.

## Project Structure

```
nifti_gif_app/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── requirements.txt     # Python dependencies
│   ├── routers/
│   │   └── convert.py       # API routes
│   ├── services/
│   │   ├── nifti_processor.py   # NIfTI processing
│   │   └── dicom_processor.py   # DICOM processing
│   └── utils/
│       └── gif_generator.py     # GIF generation
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React component
│   │   ├── api.ts           # API client
│   │   └── components/      # UI components
│   ├── package.json
│   └── vite.config.ts
├── certs/                   # SSL certificates (not in repo)
└── run.sh                   # Startup script
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/convert` | Convert files to GIF |
| GET | `/api/download/{task_id}` | Download generated GIF |
| DELETE | `/api/clear` | Clear all temporary files |
| DELETE | `/api/clear/{task_id}` | Clear specific task |

## Tech Stack

- **Backend**: FastAPI, uvicorn, nibabel, pydicom, imageio
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Communication**: HTTPS with Vite proxy

## Disclaimers

### Privacy Notice
- This tool processes medical imaging data which may contain PHI
- Files are processed locally and temporarily stored during conversion
- You are responsible for HIPAA/GDPR compliance

### Medical Disclaimer
- For visualization and educational purposes only
- Not suitable for clinical diagnosis
- Image processing may alter appearance

## License

MIT License

## Acknowledgments

- [NiBabel](https://nipy.org/nibabel/) - NIfTI file processing
- [pydicom](https://pydicom.github.io/) - DICOM file processing
- [imageio](https://imageio.readthedocs.io/) - GIF generation
