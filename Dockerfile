# Stage 1: Build React Frontend
FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci || npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend Runtime
FROM python:3.10-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=10000

# Install required system dependencies for soundfile and ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code, config, and models
COPY backend/ ./backend/
COPY config.yaml ./config.yaml

# Copy built frontend static files from Stage 1 into frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose server port
EXPOSE 10000

# Run FastAPI backend with Uvicorn
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]
