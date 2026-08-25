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


import numpy as np

ENROLLMENT_PHRASES = [
    "Asta, what's on my schedule today.",
    "Hey Asta, set a timer for ten minutes.",
    "Asta, three seven two nine one.",
    "This is just me talking normally for a few seconds.",
    "Asta, can you check the weather.",
    "One two three four five six seven.",
    "Asta, remind me to call back later.",
    "I'm recording this in one sitting on one device.",
    "Asta, play some music.",
    "Testing testing, this is sample number ten.",
    "Asta, what time is it right now.",
    "A quick brown fox jumps over something or other.",
    "Asta, stop.",
    "Nine eight seven six five four three.",
    "Asta, open my notes app.",
    "Just another casual sentence for variety.",
    "Asta, how's the traffic looking.",
    "Twelve, twenty, two hundred, two thousand.",
    "Asta, good morning.",
    "Last one, wrapping up the enrollment set.",
    "Asta, are you listening.",
    "This is a held-out test clip, not enrollment."
]


class RecordingLoopController:
    """
    Orchestrates the automated recording loop.
    
    Executes: beep → wait → record → save → quality gate → transcribe → update manifest
    """
    
    def __init__(
        self,
        audio_recorder: AudioRecorder,
        transcription_engine: TranscriptionEngine,
        session_manager: SessionManager,
        manifest_generator: ManifestGenerator,
        websocket_manager: WebSocketManager,
        quality_safeguards: QualitySafeguards,
        loop_delay: float = 1.0,
        enrollment_config: dict = None
    ):
        """Initialize recording loop with all dependencies"""
        self.audio_recorder = audio_recorder
        self.transcription_engine = transcription_engine
        self.session_manager = session_manager
        self.manifest_generator = manifest_generator
        self.websocket_manager = websocket_manager
        self.quality_safeguards = quality_safeguards
        self.loop_delay = loop_delay
        
        cfg = enrollment_config or {}
        self.target_samples = cfg.get('target_samples', 20)
        self.holdout_samples = cfg.get('holdout_samples', 2)
        self.total_target = self.target_samples + self.holdout_samples
        self.min_rms_db = cfg.get('min_rms_db', -35.0)
        self.max_clip_peak = cfg.get('max_clip_peak', 0.98)
        self.speaker_id = cfg.get('speaker_id', 'ASTA_primary')
        
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

                # Check if total target reached
                if state.valid_sample_count >= self.total_target:
                    logger.info(f"Target count reached ({state.valid_sample_count}/{self.total_target})")
                    self.stop_loop()
                    break
                
                # Execute one recording cycle
                await self.execute_cycle()
                
            except Exception as e:
                logger.error(f"Error in recording loop: {e}", exc_info=True)
                await self.websocket_manager.send_error(
                    f"Recording loop error: {str(e)}",
                    severity="warning"
                )
                await asyncio.sleep(2)
        
        self.is_running = False
        logger.info("Recording loop stopped")
    
    async def execute_cycle(self) -> None:
        """
        Execute single recording cycle.
        """
        try:
            state = self.session_manager.get_state()
            phrase_idx = state.current_phrase_index
            phrase = ENROLLMENT_PHRASES[phrase_idx % len(ENROLLMENT_PHRASES)]
            is_holdout = phrase_idx >= self.target_samples

            # Step 1: Broadcast prompt phrase & Play beep
            logger.info(f"Prompting Phrase #{phrase_idx + 1} ({'HOLDOUT' if is_holdout else 'ENROLLMENT'}): '{phrase}'")
            await self.websocket_manager.broadcast(WSMessage(
                event_type="PROMPT_PHRASE",
                payload={
                    "phrase": phrase,
                    "phrase_index": phrase_idx + 1,
                    "total_phrases": self.total_target,
                    "is_holdout": is_holdout
                }
            ))

            await self.websocket_manager.broadcast(WSMessage(
                event_type="BEEP",
                payload={}
            ))
            
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
            
            # Step 4: Compute quality metrics
            peak_amplitude = float(np.max(np.abs(audio_data))) if len(audio_data) > 0 else 0.0
            rms_val = float(np.sqrt(np.mean(audio_data**2))) if len(audio_data) > 0 else 0.0
            rms_db = 20.0 * np.log10(rms_val) if rms_val > 1e-9 else -100.0

            sample_id = self.session_manager.get_next_sample_id()
            timestamp = datetime.utcnow()
            session_dir = self.session_manager.get_current_session_dir()
            
            filename = f"sample_{sample_id}.wav"
            file_path = session_dir / filename
            
            await loop.run_in_executor(None, self.audio_recorder.save_wav, audio_data, file_path)
            rel_path = self.manifest_generator.to_relative_path(file_path)

            # Step 5: Quality Gate Check BEFORE Whisper
            is_rejected = False
            reject_reason = ""
            if rms_db < self.min_rms_db:
                is_rejected = True
                reject_reason = f"RMS too low ({rms_db:.1f} dB < {self.min_rms_db} dB)"
            elif peak_amplitude > self.max_clip_peak:
                is_rejected = True
                reject_reason = f"Peak amplitude too high ({peak_amplitude:.2f} > {self.max_clip_peak})"

            if is_rejected:
                logger.warning(f"Sample {sample_id} REJECTED_QUALITY: {reject_reason}")
                
                # Emit WebSocket quality warning
                await self.websocket_manager.send_quality_warning(
                    "rejected_quality",
                    sample_id=sample_id,
                    rms_db=round(rms_db, 2),
                    peak_amplitude=round(peak_amplitude, 3),
                    reason=reject_reason,
                    phrase=phrase
                )

                # Record REJECTED_QUALITY in manifest
                sample_metadata = SampleMetadata(
                    sample_id=sample_id,
                    file_path=rel_path,
                    transcript="REJECTED_QUALITY",
                    duration_sec=self.audio_recorder.duration,
                    sample_rate=self.audio_recorder.sample_rate,
                    session_id=state.current_session_id,
                    timestamp=format_iso8601(timestamp),
                    whisper_confidence=0.0,
                    speaker_id=self.speaker_id,
                    device_name=state.device_name,
                    room_tag=state.room_tag,
                    is_holdout=is_holdout,
                    rms_db=rms_db,
                    peak_amplitude=peak_amplitude
                )
                await loop.run_in_executor(None, self.manifest_generator.append_sample, sample_metadata)
                
                # Do NOT advance current_phrase_index (repeat phrase)
                return

            # Step 6: Transcribe audio with Faster Whisper (Valid Clip)
            await self.websocket_manager.send_sample_recorded(sample_id, rel_path)
            logger.info(f"Transcribing sample {sample_id}...")
            
            try:
                transcription_result = await asyncio.wait_for(
                    loop.run_in_executor(None, self.transcription_engine.transcribe, file_path),
                    timeout=3.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Transcription timeout for sample {sample_id}")
                transcription_result = None
            
            if transcription_result is None:
                transcript = "__unclear__"
                confidence = 0.0
                is_unclear = True
            else:
                transcript = transcription_result.text
                confidence = transcription_result.confidence
                is_unclear = transcription_result.is_unclear
            
            # Step 7: Update manifest with valid metadata
            sample_metadata = SampleMetadata(
                sample_id=sample_id,
                file_path=rel_path,
                transcript=transcript,
                duration_sec=self.audio_recorder.duration,
                sample_rate=self.audio_recorder.sample_rate,
                session_id=state.current_session_id,
                timestamp=format_iso8601(timestamp),
                whisper_confidence=confidence,
                speaker_id=self.speaker_id,
                device_name=state.device_name,
                room_tag=state.room_tag,
                is_holdout=is_holdout,
                rms_db=rms_db,
                peak_amplitude=peak_amplitude
            )
            
            await loop.run_in_executor(None, self.manifest_generator.append_sample, sample_metadata)
            
            # Step 8: Update state & advance phrase index
            state.valid_sample_count += 1
            state.current_phrase_index += 1
            self.session_manager.save_state()

            # Broadcast completion
            await self.websocket_manager.send_transcription_complete(
                sample_id, transcript, confidence, is_unclear
            )
            
            # Update stats
            await self.websocket_manager.send_stats_update(
                state.total_samples,
                state.valid_sample_count
            )
            
            logger.info(f"Cycle complete for valid sample {sample_id} ({state.valid_sample_count}/{self.total_target})")
            
            
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
