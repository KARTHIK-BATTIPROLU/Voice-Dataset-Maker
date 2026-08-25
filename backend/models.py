"""
Data Models and Schemas

Core data classes for the ASTA Voice Dataset Collector.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
import json


class RecordingState(Enum):
    """Recording session states"""
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class TranscriptionResult:
    """Result from transcription engine"""
    text: str
    confidence: float
    is_unclear: bool
    processing_time: float


@dataclass
class SampleMetadata:
    """Metadata for a single audio sample"""
    sample_id: str
    file_path: str  # Relative path from project root
    transcript: str
    duration_sec: float
    sample_rate: int
    session_id: str
    timestamp: str  # ISO 8601 format
    whisper_confidence: float
    speaker_id: str = "ASTA_primary"
    device_name: str = ""
    room_tag: str = ""
    is_holdout: bool = False
    rms_db: float = 0.0
    peak_amplitude: float = 0.0
    
    def to_csv_row(self) -> List[str]:
        """Convert to CSV row values"""
        return [
            self.sample_id,
            self.file_path,
            self.transcript,
            str(self.duration_sec),
            str(self.sample_rate),
            self.session_id,
            self.timestamp,
            str(self.whisper_confidence),
            self.speaker_id,
            self.device_name,
            self.room_tag,
            str(self.is_holdout),
            f"{self.rms_db:.2f}",
            f"{self.peak_amplitude:.4f}"
        ]


@dataclass
class SessionState:
    """Persistent session state"""
    current_session_id: str
    sample_counter: int
    recording_state: str  # RecordingState enum value
    total_samples: int
    session_start_time: str  # ISO 8601
    last_sample_id: str = "0000"
    device_name: str = ""
    room_tag: str = ""
    is_finalized: bool = False
    valid_sample_count: int = 0
    current_phrase_index: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "current_session_id": self.current_session_id,
            "sample_counter": self.sample_counter,
            "recording_state": self.recording_state,
            "total_samples": self.total_samples,
            "session_start_time": self.session_start_time,
            "last_sample_id": self.last_sample_id,
            "device_name": self.device_name,
            "room_tag": self.room_tag,
            "is_finalized": self.is_finalized,
            "valid_sample_count": self.valid_sample_count,
            "current_phrase_index": self.current_phrase_index
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SessionState':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class SessionStats:
    """Statistics for a recording session"""
    session_id: str
    total_samples: int
    session_samples: int
    session_duration: float
    start_time: str
    end_time: Optional[str] = None


@dataclass
class ValidationReport:
    """Manifest validation report"""
    is_valid: bool
    missing_files: List[str] = field(default_factory=list)
    duplicate_ids: List[str] = field(default_factory=list)
    format_errors: List[str] = field(default_factory=list)
    total_samples: int = 0
    valid_samples: int = 0
    unclear_samples: int = 0
    unique_transcripts: int = 0
    ready_for_training: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response"""
        return {
            "is_valid": self.is_valid,
            "missing_files": self.missing_files,
            "duplicate_ids": self.duplicate_ids,
            "format_errors": self.format_errors,
            "total_samples": self.total_samples,
            "valid_samples": self.valid_samples,
            "unclear_samples": self.unclear_samples,
            "unique_transcripts": self.unique_transcripts,
            "ready_for_training": self.ready_for_training
        }


@dataclass
class WSMessage:
    """WebSocket message"""
    event_type: str
    payload: dict
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps({
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp
        })


# Helper functions for ID generation
def generate_sample_id(counter: int) -> str:
    """Generate zero-padded 4-digit sample ID"""
    if counter < 0 or counter > 9999:
        raise ValueError(f"Counter must be between 0 and 9999, got {counter}")
    return f"{counter:04d}"


def generate_session_id(dt: datetime) -> str:
    """Generate session ID from datetime"""
    return f"session_{dt.strftime('%Y%m%d_%H%M%S')}"


def format_iso8601(dt: datetime) -> str:
    """Format datetime as ISO 8601 with Z suffix"""
    return dt.isoformat() + "Z"
