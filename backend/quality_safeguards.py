"""
Quality Safeguards Module

Implements quality detection for low confidence samples and duplicate transcripts.
"""

from pathlib import Path
from typing import List, Deque
from collections import deque
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


class QualitySafeguards:
    """
    Monitors and detects quality issues during recording.
    
    Tracks:
    - Low confidence transcriptions
    - Duplicate transcript patterns
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.4,
        duplicate_threshold: int = 5,
        warnings_file: Path = Path("logs/quality_warnings.log")
    ):
        """
        Initialize quality safeguards.
        
        Args:
            confidence_threshold: Minimum confidence for valid transcripts
            duplicate_threshold: Number of consecutive duplicates to flag
            warnings_file: Path to quality warnings log file
        """
        self.confidence_threshold = confidence_threshold
        self.duplicate_threshold = duplicate_threshold
        self.warnings_file = warnings_file
        
        # Track recent transcripts for duplicate detection
        self.recent_transcripts: Deque[str] = deque(maxlen=duplicate_threshold)
        
        # Ensure warnings directory exists
        self.warnings_file.parent.mkdir(parents=True, exist_ok=True)
    
    def check_low_confidence(self, sample_id: str, confidence: float) -> bool:
        """
        Check if confidence is below threshold.
        
        Args:
            sample_id: Sample identifier
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            True if low confidence detected
        """
        is_low = confidence < self.confidence_threshold
        
        if is_low:
            self.log_warning(
                f"Low confidence detected: sample {sample_id}, confidence: {confidence:.2f}"
            )
            logger.warning(f"Sample {sample_id} has low confidence: {confidence:.2f}")
        
        return is_low
    
    def check_duplicate_transcripts(self, transcript: str) -> bool:
        """
        Check for duplicate transcript patterns.
        
        Detects when the same transcript appears multiple consecutive times.
        
        Args:
            transcript: Current transcript text
            
        Returns:
            True if duplicate pattern detected (threshold consecutive matches)
        """
        # Add to recent transcripts
        self.recent_transcripts.append(transcript)
        
        # Check if we have enough samples
        if len(self.recent_transcripts) < self.duplicate_threshold:
            return False
        
        # Check if all recent transcripts are identical
        if len(set(self.recent_transcripts)) == 1 and transcript != "__unclear__":
            self.log_warning(
                f"Duplicate pattern detected: '{transcript}' repeated {self.duplicate_threshold} times"
            )
            logger.warning(f"Duplicate transcript detected: '{transcript}'")
            return True
        
        return False
    
    def log_warning(self, message: str) -> None:
        """
        Log warning to quality warnings file.
        
        Args:
            message: Warning message
        """
        try:
            timestamp = datetime.utcnow().isoformat() + "Z"
            with open(self.warnings_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            logger.error(f"Failed to write quality warning: {e}")
    
    def reset_duplicate_tracking(self) -> None:
        """Reset duplicate tracking (e.g., after warning issued)"""
        self.recent_transcripts.clear()
