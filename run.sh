#!/bin/bash

# NIfTI/DICOM to GIF Converter - Run Script
# This script starts both the backend and frontend servers

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== NIfTI/DICOM to GIF Converter ===${NC}"
echo ""

# Check if conda environment exists
CONDA_ENV="/opt/homebrew/Caskroom/miniforge/base/envs/wmh"
if [ -d "$CONDA_ENV" ]; then
    echo -e "${YELLOW}Activating conda environment: wmh${NC}"
    source /opt/homebrew/Caskroom/miniforge/base/etc/profile.d/conda.sh
    conda activate wmh
else
    echo -e "${YELLOW}Conda environment 'wmh' not found, using current environment${NC}"
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install backend dependencies if needed
echo -e "${YELLOW}Checking backend dependencies...${NC}"
pip install -q -r "$SCRIPT_DIR/backend/requirements.txt"

# Install frontend dependencies if needed
echo -e "${YELLOW}Checking frontend dependencies...${NC}"
cd "$SCRIPT_DIR/frontend"
npm install --silent

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Kill any existing processes on our ports
echo -e "${YELLOW}Killing any existing processes on ports 8801 and 8802...${NC}"
lsof -ti:8801 | xargs kill -9 2>/dev/null || true
lsof -ti:8802 | xargs kill -9 2>/dev/null || true
sleep 1

# Start backend server with HTTPS
echo ""
echo -e "${GREEN}Starting backend server on https://localhost:8802${NC}"
cd "$SCRIPT_DIR/backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8802 --reload --ssl-keyfile="$SCRIPT_DIR/certs/key.pem" --ssl-certfile="$SCRIPT_DIR/certs/cert.pem" &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend server with HTTPS on port 8801
echo -e "${GREEN}Starting frontend server on https://localhost:8801${NC}"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Get local IP for network access
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "N/A")

echo ""
echo -e "${GREEN}=== Servers are running ===${NC}"
echo -e "Frontend UI (local):   ${YELLOW}https://localhost:8801${NC}"
echo -e "Frontend UI (network): ${YELLOW}https://${LOCAL_IP}:8801${NC}"
echo -e "Backend API:           ${YELLOW}https://localhost:8802${NC}"
echo -e "API Docs:              ${YELLOW}https://localhost:8802/docs${NC}"
echo ""
echo -e "${YELLOW}Note: Accept the self-signed certificate warning in your browser${NC}"
echo -e "Press ${RED}Ctrl+C${NC} to stop both servers"
echo ""

# Wait for both processes
wait
