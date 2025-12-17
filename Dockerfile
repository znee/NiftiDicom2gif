# Multi-stage build for NIfTI/DICOM to GIF Converter
# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend with frontend static files
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
# Note: PORT is set by cloud platforms (Render, Railway, etc.)
# Default 10000 is Render's default port
ENV PORT=10000

WORKDIR /app

# Install system dependencies (curl for health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Create temp directory
RUN mkdir -p temp

# Expose the port (Render uses PORT env var)
EXPOSE $PORT

# Health check - use PORT env var
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

# Run the application
CMD ["python", "main.py"]
