"""
Transcription Engine Component

Converts audio samples to text using Faster Whisper with confidence scoring.
"""

from pathlib import Path
from faster_whisper import WhisperModel
import logging
import time
from models import TranscriptionResult


logger = logging.getLogger(__name__)


class TranscriptionEngine:
    """
    Local speech-to-text transcription using Faster Whisper.
    
    Loads the model once on initialization and reuses it for all transcriptions.
    """
    
    def __init__(self, model_size: str = "base", confidence_threshold: float = 0.4, device: str = "cpu"):
        """
        Load Faster Whisper model for local transcription.
        
        Args:
            model_size: Model size (tiny, base, small, medium, large)
            confidence_threshold: Minimum confidence for valid transcripts
            device: Device to use (cpu or cuda)
        """
        self.model_size = model_size
        self.confidence_threshold = confidence_threshold
        self.device = device
        
        logger.info(f"Loading Faster Whisper model ({model_size}) on {device}...")
        try:
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type="int8" if device == "cpu" else "float16"
            )
            logger.info("Faster Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Faster Whisper model: {e}")
            raise RuntimeError(f"Failed to load transcription model: {e}")
    
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """
        Transcribe audio file to text with confidence scoring.
        
        Args:
            audio_path: Path to WAV file
            
        Returns:
            TranscriptionResult with text and confidence score
        """
        start_time = time.time()
        
        try:
            # Transcribe audio
            segments, info = self.model.transcribe(
                str(audio_path),
                language="en",
                beam_size=1,  # Fast inference
                vad_filter=True  # Voice activity detection
            )
            
            # Collect segments and calculate average confidence
            texts = []
            confidences = []
            
            for segment in segments:
                texts.append(segment.text.strip())
                # avg_logprob is typically negative, convert to 0-1 scale
                # Higher (less negative) is better, typical range is -1.0 to 0.0
                conf = max(0.0, min(1.0, (segment.avg_logprob + 1.0)))
                confidences.append(conf)
            
            # Combine results
            if not texts:
                # No speech detected
                transcript = "__unclear__"
                confidence = 0.0
            else:
                transcript = " ".join(texts)
                confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Check if unclear
            is_unclear = confidence < self.confidence_threshold
            if is_unclear:
                transcript = "__unclear__"
            
            processing_time = time.time() - start_time
            
            logger.info(f"Transcription complete: '{transcript}' (confidence: {confidence:.2f}, time: {processing_time:.2f}s)")
            
            return TranscriptionResult(
                text=transcript,
                confidence=confidence,
                is_unclear=is_unclear,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Transcription failed for {audio_path}: {e}")
            # Return unclear result on failure
            processing_time = time.time() - start_time
            return TranscriptionResult(
                text="__unclear__",
                confidence=0.0,
                is_unclear=True,
                processing_time=processing_time
            )
    
    def should_flag_unclear(self, confidence: float) -> bool:
        """Check if confidence is below threshold"""
        return confidence < self.confidence_threshold
