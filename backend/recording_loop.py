"""
Recording Loop Controller

Orchestrates the automated recording cycle with proper error handling.
"""

import asyncio
from pathlib import Path
from datetime import datetime
import logging
from audio_recorder import AudioRecorder, AudioRecordingError
from transcription_engine import TranscriptionEngine
from session_manager import SessionManager
from manifest_generator import ManifestGenerator
from websocket_manager import WebSocketManager
from quality_safeguards import QualitySafeguards
from models import SampleMetadata, RecordingState, format_iso8601, WSMessage


logger = logging.getLogger(__name__)


class RecordingLoopController:
    """
    Orchestrates the automated recording loop.
    
    Executes: beep → wait → record → save → transcribe → update manifest
    """
    
    def __init__(
        self,
        audio_recorder: AudioRecorder,
        transcription_engine: TranscriptionEngine,
        session_manager: SessionManager,
        manifest_generator: ManifestGenerator,
        websocket_manager: WebSocketManager,
        quality_safeguards: QualitySafeguards,
        loop_delay: float = 1.0
    ):
        """Initialize recording loop with all dependencies"""
        self.audio_recorder = audio_recorder
        self.transcription_engine = transcription_engine
        self.session_manager = session_manager
        self.manifest_generator = manifest_generator
        self.websocket_manager = websocket_manager
        self.quality_safeguards = quality_safeguards
        self.loop_delay = loop_delay
        
        self.is_running = False
        self.should_stop = False
    
    async def start_loop(self) -> None:
        """
        Start automated recording loop.
        
        Continues until pause/stop signal.
        """
        self.is_running = True
        self.should_stop = False
        
        logger.info("Starting recording loop...")
        
        while self.is_running and not self.should_stop:
            try:
                # Check if we should pause
                state = self.session_manager.get_state()
                if state.recording_state == RecordingState.PAUSED.value:
                    logger.info("Recording loop paused, waiting...")
                    await asyncio.sleep(1)
                    continue
                
                if state.recording_state != RecordingState.ACTIVE.value:
                    logger.info("Recording loop stopped (not active)")
                    break
                
                # Execute one recording cycle
                await self.execute_cycle()
                
            except Exception as e:
                logger.error(f"Error in recording loop: {e}", exc_info=True)
                await self.websocket_manager.send_error(
                    f"Recording loop error: {str(e)}",
                    severity="warning"
                )
                # Continue loop despite error
                await asyncio.sleep(2)
        
        self.is_running = False
        logger.info("Recording loop stopped")
    
    async def execute_cycle(self) -> None:
        """
        Execute single recording cycle.
        
        Steps:
        1. Play beep (0.5s)
        2. Wait (1s)
        3. Record audio (5s)
        4. Save WAV file
        5. Transcribe audio (1-2s)
        6. Update manifest
        7. Broadcast events via WebSocket
        """
        try:
            # Step 1: Play beep
            logger.info("Playing beep...")
            await self.websocket_manager.broadcast(WSMessage(
                event_type="BEEP",
                payload={}
            ))
            
            # Play beep in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.audio_recorder.play_beep)
            
            # Step 2: Wait before recording
            await asyncio.sleep(self.loop_delay)
            
            # Step 3: Record audio
            logger.info("Recording audio...")
            await self.websocket_manager.broadcast(WSMessage(
                event_type="RECORDING_START",
                payload={}
            ))
            
            audio_data = await loop.run_in_executor(None, self.audio_recorder.record_sample)
            
            # Step 4: Save WAV file
            sample_id = self.session_manager.get_next_sample_id()
            timestamp = datetime.utcnow()
            session_dir = self.session_manager.get_current_session_dir()
            
            filename = f"sample_{sample_id}.wav"
            file_path = session_dir / filename
            
            await loop.run_in_executor(None, self.audio_recorder.save_wav, audio_data, file_path)
            
            # Notify frontend
            rel_path = self.manifest_generator.to_relative_path(file_path)
            await self.websocket_manager.send_sample_recorded(sample_id, rel_path)
            
            # Step 5: Transcribe audio
            logger.info(f"Transcribing sample {sample_id}...")
            
            # Run transcription with timeout
            try:
                transcription_result = await asyncio.wait_for(
                    loop.run_in_executor(None, self.transcription_engine.transcribe, file_path),
                    timeout=3.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Transcription timeout for sample {sample_id}")
                transcription_result = None
            
            # Handle transcription result
            if transcription_result is None:
                transcript = "__unclear__"
                confidence = 0.0
                is_unclear = True
            else:
                transcript = transcription_result.text
                confidence = transcription_result.confidence
                is_unclear = transcription_result.is_unclear
            
            # Step 6: Quality checks
            is_low_conf = self.quality_safeguards.check_low_confidence(sample_id, confidence)
            is_duplicate = self.quality_safeguards.check_duplicate_transcripts(transcript)
            
            if is_low_conf:
                await self.websocket_manager.send_quality_warning(
                    "low_confidence",
                    sample_id=sample_id,
                    confidence=confidence
                )
            
            if is_duplicate:
                await self.websocket_manager.send_quality_warning(
                    "duplicate_detection",
                    transcript=transcript,
                    occurrence_count=self.quality_safeguards.duplicate_threshold
                )
                self.quality_safeguards.reset_duplicate_tracking()
            
            # Step 7: Update manifest
            sample_metadata = SampleMetadata(
                sample_id=sample_id,
                file_path=rel_path,
                transcript=transcript,
                duration_sec=self.audio_recorder.duration,
                sample_rate=self.audio_recorder.sample_rate,
                session_id=self.session_manager.get_state().current_session_id,
                timestamp=format_iso8601(timestamp),
                whisper_confidence=confidence
            )
            
            await loop.run_in_executor(None, self.manifest_generator.append_sample, sample_metadata)
            
            # Step 8: Broadcast completion
            await self.websocket_manager.send_transcription_complete(
                sample_id, transcript, confidence, is_unclear
            )
            
            # Update stats
            state = self.session_manager.get_state()
            session_samples = int(sample_id) - (state.total_samples - int(sample_id))
            await self.websocket_manager.send_stats_update(
                state.total_samples,
                session_samples
            )
            
            logger.info(f"Cycle complete for sample {sample_id}")
            
        except AudioRecordingError as e:
            logger.error(f"Audio recording error: {e}")
            await self.websocket_manager.send_error(
                f"Audio recording failed: {str(e)}",
                severity="critical"
            )
            # Pause on audio error
            self.session_manager.pause_session()
        
        except Exception as e:
            logger.error(f"Cycle execution error: {e}", exc_info=True)
            await self.websocket_manager.send_error(
                f"Cycle error: {str(e)}",
                severity="warning"
            )
    
    def pause_loop(self) -> None:
        """Signal loop to pause after current cycle"""
        logger.info("Pause signal received")
        # Pause is handled by session manager state
    
    def stop_loop(self) -> None:
        """Signal loop to stop after current cycle"""
        logger.info("Stop signal received")
        self.should_stop = True
        self.is_running = False
