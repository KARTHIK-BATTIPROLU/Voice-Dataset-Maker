"""
Session Manager Component

Tracks recording sessions, manages state persistence, and coordinates lifecycle.
"""

from pathlib import Path
from datetime import datetime
import json
import logging
from .models import SessionState, RecordingState, SessionStats, generate_sample_id, generate_session_id, format_iso8601


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
    
    def start_session(self) -> str:
        """
        Create new recording session with timestamp-based ID.
        
        Returns:
            session_id: Format session_YYYYMMDD_HHMMSS
        """
        now = datetime.utcnow()
        session_id = generate_session_id(now)
        
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
            last_sample_id=self.state.last_sample_id if self.state else "0000"
        )
        
        self.save_state()
        logger.info(f"Started session: {session_id}")
        return session_id
    
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
        session_samples = self.state.total_samples - (
            self.state.total_samples - 
            (int(self.state.last_sample_id) if self.state.last_sample_id.isdigit() else 0)
        )
        
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
