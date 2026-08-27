"""
ASTA Voice Dataset Collector - FastAPI Application

Main entry point for the backend API server.
"""

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
import asyncio
import yaml

import io
import soundfile as sf
import numpy as np
from datetime import datetime

# Import components
from audio_recorder import AudioRecorder
from transcription_engine import TranscriptionEngine
from session_manager import SessionManager
from manifest_generator import ManifestGenerator
from websocket_manager import WebSocketManager
from quality_safeguards import QualitySafeguards
from recording_loop import RecordingLoopController
from models import RecordingState, WSMessage, SampleMetadata, format_iso8601

# Configure logging
Path('logs').mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ASTA Voice Dataset Collector API",
    description="Backend API for voice dataset collection with local transcription",
    version="1.0.0"
)

# Add CORS middleware
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
audio_recorder: AudioRecorder = None
transcription_engine: TranscriptionEngine = None
session_manager: SessionManager = None
manifest_generator: ManifestGenerator = None
websocket_manager: WebSocketManager = None
quality_safeguards: QualitySafeguards = None
recording_loop: RecordingLoopController = None
recording_task: asyncio.Task = None


def load_config():
    """Load configuration from config.yaml with env overrides"""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            cfg = yaml.safe_load(f)
    else:
        # Return default configuration
        cfg = {
            'audio': {
                'sample_rate': 16000,
                'duration': 5.0,
                'beep_duration': 0.5,
                'beep_frequency': 800
            },
            'transcription': {
                'model_size': 'tiny',
                'confidence_threshold': 0.4,
                'device': 'cpu'
            },
            'recording': {
                'loop_delay': 1.0
            },
            'paths': {
                'data_dir': 'data',
                'manifest_file': 'manifest.csv',
                'state_file': 'session_state.json',
                'logs_dir': 'logs'
            },
            'quality': {
                'duplicate_detection_threshold': 5
            }
        }

    # Environment variable override for cloud/low-memory environments
    if 'WHISPER_MODEL_SIZE' in os.environ:
        if 'transcription' not in cfg:
            cfg['transcription'] = {}
        cfg['transcription']['model_size'] = os.environ['WHISPER_MODEL_SIZE']

    return cfg


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global audio_recorder, transcription_engine, session_manager, manifest_generator
    global websocket_manager, quality_safeguards, recording_loop
    
    logger.info("Starting ASTA Voice Dataset Collector backend...")
    
    # Load configuration
    config = load_config()
    
    # Create directories
    Path(config['paths']['logs_dir']).mkdir(parents=True, exist_ok=True)
    Path(config['paths']['data_dir']).mkdir(parents=True, exist_ok=True)
    
    # Initialize components
    try:
        audio_recorder = AudioRecorder(
            sample_rate=config['audio']['sample_rate'],
            duration=config['audio']['duration']
        )
        logger.info("Audio recorder initialized")
        
        transcription_engine = TranscriptionEngine(
            model_size=config['transcription']['model_size'],
            confidence_threshold=config['transcription']['confidence_threshold'],
            device=config['transcription']['device']
        )
        logger.info("Transcription engine initialized")
        
        session_manager = SessionManager(
            state_file=Path(config['paths']['state_file']),
            data_dir=Path(config['paths']['data_dir'])
        )
        logger.info("Session manager initialized")
        
        manifest_generator = ManifestGenerator(
            manifest_path=Path(config['paths']['manifest_file'])
        )
        logger.info("Manifest generator initialized")
        
        websocket_manager = WebSocketManager()
        logger.info("WebSocket manager initialized")
        
        quality_safeguards = QualitySafeguards(
            confidence_threshold=config['transcription']['confidence_threshold'],
            duplicate_threshold=config['quality']['duplicate_detection_threshold']
        )
        logger.info("Quality safeguards initialized")
        
        recording_loop = RecordingLoopController(
            audio_recorder=audio_recorder,
            transcription_engine=transcription_engine,
            session_manager=session_manager,
            manifest_generator=manifest_generator,
            websocket_manager=websocket_manager,
            quality_safeguards=quality_safeguards,
            loop_delay=config['recording']['loop_delay'],
            enrollment_config=config.get('enrollment', {})
        )
        logger.info("Recording loop controller initialized")
        
        logger.info("Backend initialization complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize backend: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global recording_task
    
    logger.info("Shutting down backend...")
    
    if recording_task and not recording_task.done():
        recording_loop.stop_loop()
        recording_task.cancel()
    
    logger.info("Backend shutdown complete")


# REST API Endpoints

class StartSessionRequest(BaseModel if 'BaseModel' in globals() else object):
    pass

@app.post("/api/session/start")
async def start_session(room_tag: str = "default-room"):
    """Start a new recording session"""
    global recording_task
    
    try:
        config = load_config()
        enroll_cfg = config.get('enrollment', {})
        single_lock = enroll_cfg.get('single_session_lock', True)
        
        # Check if already recording
        state = session_manager.get_state()
        if state.recording_state == RecordingState.ACTIVE.value:
            raise HTTPException(status_code=400, detail="Session already active")
        
        # Start new session
        session_id = session_manager.start_session(
            room_tag=room_tag,
            single_session_lock=single_lock
        )
        
        # Start recording loop
        if recording_task is None or recording_task.done():
            recording_task = asyncio.create_task(recording_loop.start_loop())
        
        # Broadcast state change
        await websocket_manager.send_state_change(RecordingState.ACTIVE.value, session_id)
        
        logger.info(f"Session started: {session_id} (room_tag: {room_tag})")
        
        return JSONResponse({
            "session_id": session_id,
            "status": "started",
            "device_name": session_manager.get_state().device_name,
            "room_tag": room_tag
        })
        
    except ValueError as ve:
        logger.warning(f"Session start blocked: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sample/upload")
async def upload_sample(file: UploadFile = File(...)):
    """Receive audio file uploaded from client browser microphone"""
    try:
        audio_bytes = await file.read()
        
        # Read uploaded audio into numpy array
        try:
            audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype='float32')
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)
        except Exception:
            temp_path = Path("temp_upload.webm")
            with open(temp_path, "wb") as f:
                f.write(audio_bytes)
            wav_temp = Path("temp_upload.wav")
            import subprocess
            subprocess.run([
                "ffmpeg", "-y", "-i", str(temp_path),
                "-ar", "16000", "-ac", "1", str(wav_temp)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            audio_data, sample_rate = sf.read(wav_temp, dtype='float32')
            temp_path.unlink(missing_ok=True)
            wav_temp.unlink(missing_ok=True)

        state = session_manager.get_state()
        session_dir = session_manager.get_current_session_dir()
        sample_id = session_manager.get_next_sample_id()
        filename = f"sample_{sample_id}.wav"
        file_path = session_dir / filename
        
        # Save as 16kHz mono 16-bit PCM WAV
        audio_recorder.save_wav(audio_data, file_path)
        rel_path = manifest_generator.to_relative_path(file_path)
        
        # Quality check
        config = load_config()
        enroll_cfg = config.get('enrollment', {})
        min_rms = enroll_cfg.get('min_rms_db', -35.0)
        max_peak = enroll_cfg.get('max_clip_peak', 0.98)

        rms_val = float(np.sqrt(np.mean(audio_data ** 2))) if len(audio_data) > 0 else 0.0
        rms_db = 20.0 * np.log10(rms_val) if rms_val > 1e-9 else -100.0
        peak_val = float(np.max(np.abs(audio_data))) if len(audio_data) > 0 else 0.0

        if rms_db < min_rms or peak_val > max_peak:
            reason = f"RMS too low ({rms_db:.1f} dB < {min_rms} dB)" if rms_db < min_rms else f"Peak amplitude too high ({peak_val:.2f} > {max_peak})"
            logger.warning(f"Uploaded sample {sample_id} REJECTED_QUALITY: {reason}")
            await websocket_manager.send_quality_warning(
                "rejected_quality",
                sample_id=sample_id,
                rms_db=round(rms_db, 2),
                peak_amplitude=round(peak_val, 3),
                reason=reason
            )
            return JSONResponse({"status": "rejected", "reason": reason}, status_code=400)

        # Transcribe using Faster Whisper
        result = transcription_engine.transcribe(file_path)
        
        metadata = SampleMetadata(
            sample_id=sample_id,
            file_path=rel_path,
            transcript=result.text,
            duration_sec=round(len(audio_data) / 16000.0, 2),
            sample_rate=16000,
            session_id=state.current_session_id,
            timestamp=format_iso8601(datetime.utcnow()),
            whisper_confidence=round(result.confidence, 4)
        )
        manifest_generator.add_sample(metadata)
        session_manager.state.valid_sample_count += 1
        session_manager.state.current_phrase_index += 1
        session_manager.save_state()
        
        await websocket_manager.send_transcription_complete(
            sample_id=sample_id,
            transcript=result.text,
            confidence=result.confidence,
            is_unclear=result.is_unclear
        )
        
        updated_state = session_manager.get_state()
        await websocket_manager.send_stats_update(updated_state.total_samples, updated_state.valid_sample_count)

        return JSONResponse({
            "status": "success",
            "sample_id": sample_id,
            "transcript": result.text,
            "confidence": result.confidence
        })
    except Exception as e:
        logger.error(f"Failed to upload sample: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/reset")
async def reset_session():
    """Reset session state to unlock single-session lock"""
    global recording_task
    try:
        recording_loop.stop_loop()
        if recording_task and not recording_task.done():
            recording_task.cancel()
        session_manager.reset_session()
        await websocket_manager.send_state_change(RecordingState.IDLE.value, "")
        logger.info("Session reset via API")
        return JSONResponse({"status": "reset", "message": "Session reset successfully."})
    except Exception as e:
        logger.error(f"Failed to reset session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/pause")
async def pause_session():
    """Pause the current recording session"""
    try:
        session_manager.pause_session()
        recording_loop.pause_loop()
        
        state = session_manager.get_state()
        await websocket_manager.send_state_change(RecordingState.PAUSED.value, state.current_session_id)
        
        logger.info("Session paused")
        
        return JSONResponse({
            "status": "paused",
            "sample_id": state.last_sample_id
        })
        
    except Exception as e:
        logger.error(f"Failed to pause session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/resume")
async def resume_session():
    """Resume a paused recording session"""
    global recording_task
    
    try:
        session_manager.resume_session()
        
        # Restart recording loop if needed
        if recording_task is None or recording_task.done():
            recording_task = asyncio.create_task(recording_loop.start_loop())
        
        state = session_manager.get_state()
        await websocket_manager.send_state_change(RecordingState.ACTIVE.value, state.current_session_id)
        
        logger.info("Session resumed")
        
        return JSONResponse({
            "status": "resumed",
            "session_id": state.current_session_id
        })
        
    except Exception as e:
        logger.error(f"Failed to resume session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/stop")
async def stop_session():
    """Stop the current recording session and run post-session enrollment verification"""
    global recording_task
    
    try:
        config = load_config()
        stats = session_manager.stop_session()
        recording_loop.stop_loop()
        
        if recording_task and not recording_task.done():
            recording_task.cancel()
        
        await websocket_manager.send_state_change(RecordingState.STOPPED.value, stats.session_id)
        
        # Run ECAPA-TDNN speaker enrollment script
        import enroll
        loop = asyncio.get_event_loop()
        enrollment_result = await loop.run_in_executor(
            None,
            enroll.run,
            stats.session_id,
            config['paths']['manifest_file']
        )

        session_manager.finalize_session()

        # Surface holdout pass/fail scores through WebSocket immediately
        await websocket_manager.broadcast(WSMessage(
            event_type="ENROLLMENT_COMPLETE",
            payload=enrollment_result
        ))
        
        logger.info(f"Session stopped and enrolled: {stats.session_id}")
        
        return JSONResponse({
            "status": "stopped",
            "total_samples": stats.total_samples,
            "session_duration": stats.session_duration,
            "enrollment_result": enrollment_result
        })
        
    except Exception as e:
        logger.error(f"Failed to stop session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/status")
async def get_session_status():
    """Get current session status"""
    try:
        state = session_manager.get_state()
        
        return JSONResponse({
            "state": state.recording_state,
            "current_session_id": state.current_session_id,
            "sample_counter": state.sample_counter,
            "total_samples": state.total_samples
        })
        
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get collection statistics"""
    try:
        state = session_manager.get_state()
        validation = manifest_generator.validate_manifest()
        
        return JSONResponse({
            "total_samples": state.total_samples,
            "valid_samples": validation.valid_samples,
            "unclear_samples": validation.unclear_samples,
            "unique_transcripts": validation.unique_transcripts,
            "ready_for_training": validation.ready_for_training
        })
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/manifest/validate")
async def validate_manifest():
    """Validate manifest integrity"""
    try:
        validation = manifest_generator.validate_manifest()
        return JSONResponse(validation.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to validate manifest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket)
    
    try:
        # Send initial status
        state = session_manager.get_state()
        await websocket_manager.send_state_change(state.recording_state, state.current_session_id)
        await websocket_manager.send_stats_update(state.total_samples, 0)
        
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            # Client messages can be handled here if needed
            logger.debug(f"Received from client: {data}")
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket_manager.disconnect(websocket)


# Health check endpoint

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ASTA Voice Dataset Collector"}


# Static file serving for React frontend (if built in dist/)
dist_dir = Path(__file__).parent.parent / "frontend" / "dist"
if not dist_dir.exists():
    dist_dir = Path("frontend/dist")

if dist_dir.exists():
    logger.info(f"Serving static frontend assets from {dist_dir}")
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api") or full_path.startswith("ws") or full_path == "health":
            raise HTTPException(status_code=404, detail="Endpoint not found")
        target_file = dist_dir / full_path
        if target_file.exists() and target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(dist_dir / "index.html")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")

