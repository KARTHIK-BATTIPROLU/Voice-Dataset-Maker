# Deploying ASTA Voice Dataset Collector to Render

This repository is pre-configured for 1-click deployment on [Render](https://render.com).

---

## 🚀 Quick Start Deployment (Render Blueprint - Recommended)

1. **Push your code to GitHub**:
   Ensure all local changes (including `Dockerfile`, `render.yaml`, `backend/main.py`, `frontend/src/App.jsx`) are pushed to your GitHub repository:
   ```bash
   git add .
   git commit -m "Configure app for Render deployment"
   git push origin main
   ```

2. **Log into Render**:
   - Go to [dashboard.render.com](https://dashboard.render.com/)
   - Sign in with your GitHub account.

3. **Deploy with Blueprint**:
   - Click **New +** -> **Blueprints**
   - Connect your GitHub repository (`KARTHIK-BATTIPROLU/Voice-Dataset-Maker`)
   - Render will automatically detect `render.yaml`.
   - Click **Apply**. Render will build and deploy the Docker container automatically!

---

## 🛠️ Alternative Manual Web Service Deployment

If you prefer to configure the Web Service manually via Render UI:

1. Click **New +** -> **Web Service**
2. Select your repository: `KARTHIK-BATTIPROLU/Voice-Dataset-Maker`
3. Configure the service settings:
   - **Name**: `voice-dataset-maker`
   - **Environment**: **Docker**
   - **Dockerfile Path**: `./Dockerfile`
   - **Health Check Path**: `/health`
4. Click **Create Web Service**.

---

## 🌐 Features Included for Render Deployment

- **Single Service Architecture**: FastAPI serves both backend REST/WebSocket endpoints and the React frontend static assets (`frontend/dist`).
- **Dynamic WebSocket (`wss://`) Protocol**: Frontend automatically selects `wss://` over HTTPS and connects to your Render domain without port mismatches.
- **Headless Server Protection**: `AudioRecorder` detects cloud environment and avoids crashing if physical microphone hardware is absent.
- **Health Check Endpoint**: Available at `/health` for Render's zero-downtime health monitors.
