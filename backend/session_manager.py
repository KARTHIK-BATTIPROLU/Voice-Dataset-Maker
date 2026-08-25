"""
Session Manager Component

Tracks recording sessions, manages state persistence, and coordinates lifecycle.
"""

from pathlib import Path
from datetime import datetime
import json
import logging
from models import SessionState, RecordingState, SessionStats, generate_sample_id, generate_session_id, format_iso8601


logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages recording sessions and persistent state.
    
    Handles session lifecycle (start, pause, resume, stop) and maintains
    sample ID continuity across application restarts.
    """
    
    def __init__(self, state_file: Path = Path("session_state.json"), data_dir: Path = Path("data")):
        """
        Initialize session manager with state persistence.
        
        Args:
            state_file: Path to session state JSON file
            data_dir: Base directory for audio samples
        """
        self.state_file = state_file
        self.data_dir = data_dir
        self.state: SessionState = None
        
        # Load existing state or initialize new
        self.load_state()
    
    def get_input_device_name(self) -> str:
        """Query system audio input device name"""
        try:
            import sounddevice as sd
            input_device = sd.query_devices(kind='input')
            return input_device.get('name', 'Default Microphone')
        except Exception as e:
            logger.warning(f"Failed to query sounddevice input device: {e}")
            return "Default Microphone"

    def start_session(self, room_tag: str = "", single_session_lock: bool = True) -> str:
        """
        Create new recording session with timestamp-based ID.
        
        Args:
            room_tag: User-entered room/setup description
            single_session_lock: Block starting second session if unfinalized session exists
            
        Returns:
            session_id: Format session_YYYYMMDD_HHMMSS
        """
        if single_session_lock and self.state and self.state.current_session_id and not self.state.is_finalized:
            raise ValueError(f"Enrollment session '{self.state.current_session_id}' already exists and is locked. Finalize or reset before starting a new session.")

        now = datetime.utcnow()
        session_id = generate_session_id(now)
        device_name = self.get_input_device_name()
        
        # Create session directory
        session_dir = self.data_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Update state
        self.state = SessionState(
            current_session_id=session_id,
            sample_counter=self.state.sample_counter if self.state else 1,
            recording_state=RecordingState.ACTIVE.value,
            total_samples=self.state.total_samples if self.state else 0,
            session_start_time=format_iso8601(now),
            last_sample_id=self.state.last_sample_id if self.state else "0000",
            device_name=device_name,
            room_tag=room_tag,
            is_finalized=False,
            valid_sample_count=0,
            current_phrase_index=0
        )
        
        self.save_state()
        logger.info(f"Started session: {session_id} [Device: {device_name}, Room: {room_tag}]")
        return session_id
    
    def reset_session(self) -> None:
        """Reset the session state so a new session can be started"""
        self.state = SessionState(
            current_session_id="",
            sample_counter=self.state.sample_counter if self.state else 1,
            recording_state=RecordingState.IDLE.value,
            total_samples=self.state.total_samples if self.state else 0,
            session_start_time=format_iso8601(datetime.utcnow()),
            last_sample_id=self.state.last_sample_id if self.state else "0000",
            device_name="",
            room_tag="",
            is_finalized=False,
            valid_sample_count=0,
            current_phrase_index=0
        )
        self.save_state()
        logger.info("Session state reset")

    def finalize_session(self) -> None:
        """Mark current session as finalized"""
        if self.state:
            self.state.is_finalized = True
            self.save_state()
            logger.info(f"Session {self.state.current_session_id} marked as finalized")

    def pause_session(self) -> None:
        """Pause current session, preserve sample counter"""
        if self.state:
            self.state.recording_state = RecordingState.PAUSED.value
            self.save_state()
            logger.info(f"Paused session: {self.state.current_session_id}")
    
    def resume_session(self) -> None:
        """Resume paused session with preserved state"""
        if self.state:
            self.state.recording_state = RecordingState.ACTIVE.value
            self.save_state()
            logger.info(f"Resumed session: {self.state.current_session_id}")
    
    def stop_session(self) -> SessionStats:
        """
        Finalize session and return statistics.
        
        Returns:
            SessionStats with session summary
        """
        if not self.state:
            logger.warning("stop_session called with no active state")
            return SessionStats(
                session_id="unknown",
                total_samples=0,
                session_samples=0,
                session_duration=0.0,
                start_time=""
            )
        
        # Calculate session samples
        session_samples = self.state.valid_sample_count
        
        # Calculate duration
        start_time = datetime.fromisoformat(self.state.session_start_time.rstrip('Z'))
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        stats = SessionStats(
            session_id=self.state.current_session_id,
            total_samples=self.state.total_samples,
            session_samples=session_samples,
            session_duration=duration,
            start_time=self.state.session_start_time,
            end_time=format_iso8601(end_time)
        )
        
        # Update state
        self.state.recording_state = RecordingState.STOPPED.value
        self.save_state()
        
        logger.info(f"Stopped session: {self.state.current_session_id} ({session_samples} samples)")
        return stats
    
    def get_next_sample_id(self) -> str:
        """
        Generate next sequential sample ID.
        
        Returns:
            Zero-padded 4-digit string (0001, 0002, ..., 9999)
        """
        if not self.state:
            self.state = SessionState(
                current_session_id="",
                sample_counter=1,
                recording_state=RecordingState.IDLE.value,
                total_samples=0,
                session_start_time=format_iso8601(datetime.utcnow())
            )
        
        sample_id = generate_sample_id(self.state.sample_counter)
        
        # Increment counters
        self.state.sample_counter += 1
        self.state.total_samples += 1
        self.state.last_sample_id = sample_id
        
        self.save_state()
        return sample_id
    
    def get_current_session_dir(self) -> Path:
        """Get current session's data directory"""
        if not self.state or not self.state.current_session_id:
            raise ValueError("No active session")
        
        return self.data_dir / self.state.current_session_id
    
    def get_state(self) -> SessionState:
        """Get current session state"""
        if not self.state:
            # Return default idle state
            return SessionState(
                current_session_id="",
                sample_counter=1,
                recording_state=RecordingState.IDLE.value,
                total_samples=0,
                session_start_time=format_iso8601(datetime.utcnow())
            )
        return self.state
    
    def save_state(self) -> None:
        """Persist state to session_state.json"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=2)
            logger.debug(f"Session state saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
    
    def load_state(self) -> None:
        """Restore state from session_state.json"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                self.state = SessionState.from_dict(data)
                logger.info(f"Loaded session state: {self.state.current_session_id}")
            except Exception as e:
                logger.error(f"Failed to load session state: {e}")
                self.state = None
        else:
            logger.info("No existing session state found")
            self.state = None
