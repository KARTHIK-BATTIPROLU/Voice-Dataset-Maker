# Design Document

## Overview

The ASTA Voice Dataset Collector is a full-stack application designed for efficient, zero-cost collection of voice datasets for speaker verification model training. The system consists of a FastAPI backend service that manages audio recording, local transcription, and data persistence, paired with a React frontend that provides real-time user controls and visual feedback.

### Key Design Principles

1. **Local-First Architecture**: All processing occurs on the local machine with no external dependencies
2. **Real-Time Feedback**: WebSocket-based communication ensures immediate UI updates
3. **Automated Workflow**: Continuous recording loop minimizes manual intervention
4. **Data Integrity**: Atomic operations and validation ensure dataset reliability
5. **SpeechBrain Compatibility**: Generated manifest follows SpeechBrain ECAPA-TDNN format specifications

### Technology Stack

**Backend:**
- FastAPI: Async web framework for RESTful API and WebSocket server
- SoundDevice: Low-level audio recording with 16kHz mono capture
- Faster Whisper: Local speech-to-text transcription (base model)
- Python 3.10+: Core runtime environment
- PyYAML: Configuration management
- asyncio: Asynchronous task orchestration

**Frontend:**
- React 18: Component-based UI framework
- WebSocket API: Real-time backend communication
- CSS3: Custom styling with electric blue (#4F8EF7) theme
- Modern JavaScript (ES6+): Event handling and state management

**Data Storage:**
- File System: WAV files, CSV manifest, JSON state
- No database required for MVP

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │  Controls  │  │ Visual Orb   │  │  Transcript Feed    │ │
│  │  Component │  │  Indicator   │  │  Component          │ │
│  └────────────┘  └──────────────┘  └─────────────────────┘ │
│         │                │                    │              │
│         └────────────────┴────────────────────┘              │
│                          │                                   │
│                    WebSocket + REST API                      │
└──────────────────────────┼───────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────┐
│                  FastAPI Backend                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              WebSocket Server                           │ │
│  │         (Real-time event broadcasting)                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐  │
│  │   REST API    │  │    Session    │  │   Recording    │  │
│  │   Endpoints   │  │    Manager    │  │     Loop       │  │
│  └───────────────┘  └───────────────┘  └────────────────┘  │
│                          │                      │            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Core Processing Pipeline                   │ │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────────┐   │ │
│  │  │  Audio   │→ │  Faster  │→ │     Manifest      │   │ │
│  │  │ Recorder │  │ Whisper  │  │    Generator      │   │ │
│  │  └──────────┘  └──────────┘  └───────────────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           ▼
                 ┌──────────────────┐
                 │   File System    │
                 │ ├─ data/         │
                 │ ├─ manifest.csv  │
                 │ ├─ session.json  │
                 │ └─ logs/         │
                 └──────────────────┘
```

### Recording Loop State Machine

```
                    ┌─────────┐
                    │  IDLE   │
                    └────┬────┘
                         │ start
                         ▼
                    ┌─────────┐
         ┌─────────►│ ACTIVE  │◄────────┐
         │          └────┬────┘         │
         │               │              │
         │ resume        │ pause        │
         │          ┌────▼────┐         │
         │          │ PAUSED  │         │
         │          └────┬────┘         │
         │               │              │
         │               └──────────────┘
         │               
         │          ┌─────────┐
         └──────────│ STOPPED │
                    └─────────┘
```

### Recording Cycle Flow

```
┌──────────────────────────────────────────────────────────┐
│            Single Recording Cycle (6-7 seconds)           │
└──────────────────────────────────────────────────────────┘
        │
        ▼
   ┌─────────┐
   │ Play    │  0.5 sec beep
   │ Beep    │
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ Wait    │  1 sec delay
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ Record  │  5 sec capture
   │ Audio   │  → sample_XXXX.wav
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ Save    │  Write to disk
   │ WAV     │  data/session_*/sample_XXXX.wav
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ Faster  │  ~1-2 sec processing
   │ Whisper │  → transcript + confidence
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ Update  │  Append to manifest.csv
   │Manifest │  Broadcast via WebSocket
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ Check   │  if ACTIVE → next cycle
   │ State   │  if PAUSED/STOPPED → exit
   └─────────┘
```

## Components and Interfaces

### 1. Audio Recorder Component

**Responsibility**: Capture 5-second audio chunks at 16kHz mono using the system microphone.

**Technology**: SoundDevice library with blocking I/O for simplicity

**Interface**:
```python
class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, duration: float = 5.0):
        """Initialize recorder with configurable parameters"""
        
    def record_sample(self) -> np.ndarray:
        """
        Record a single 5-second audio sample
        Returns: numpy array of audio data (shape: [sample_rate * duration])
        Raises: AudioRecordingError on capture failure
        """
        
    def save_wav(self, audio_data: np.ndarray, file_path: Path) -> None:
        """
        Save audio data as 16-bit PCM WAV file
        Args:
            audio_data: Audio samples as numpy array
            file_path: Output path for WAV file
        """
        
    def play_beep(self, duration: float = 0.5, frequency: int = 800) -> None:
        """Play audio beep cue before recording"""
```

**Configuration**:
- Sample rate: 16000 Hz (required for most speech models)
- Channels: 1 (mono)
- Duration: 5.0 seconds
- Bit depth: 16-bit PCM
- Device: System default microphone

### 2. Transcription Engine Component

**Responsibility**: Convert audio samples to text using Faster Whisper with confidence scoring.

**Technology**: Faster Whisper (base model) - optimized local inference

**Interface**:
```python
class TranscriptionEngine:
    def __init__(self, model_size: str = "base", confidence_threshold: float = 0.4):
        """Load Faster Whisper model for local transcription"""
        
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """
        Transcribe audio file to text with confidence scoring
        Args:
            audio_path: Path to WAV file
        Returns: TranscriptionResult with text and confidence score
        Processing time: ~1-2 seconds for 5-second audio
        """
        
    def should_flag_unclear(self, confidence: float) -> bool:
        """Check if confidence is below threshold"""

@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    is_unclear: bool
    processing_time: float
```

**Confidence Score Handling**:
- Scores < 0.4: Label as `__unclear__`
- Scores ≥ 0.4: Use actual transcript
- Empty audio: Return `__unclear__`

### 3. Session Manager Component

**Responsibility**: Track recording sessions, manage state persistence, and coordinate lifecycle.

**Technology**: Python dataclasses with JSON serialization

**Interface**:
```python
class SessionManager:
    def __init__(self, state_file: Path = "session_state.json"):
        """Initialize session manager with state persistence"""
        
    def start_session(self) -> str:
        """
        Create new recording session with timestamp-based ID
        Returns: session_id (format: session_YYYYMMDD_HHMMSS)
        Creates: data/session_YYYYMMDD_HHMMSS/ directory
        """
        
    def pause_session(self) -> None:
        """Pause current session, preserve sample counter"""
        
    def resume_session(self) -> None:
        """Resume paused session with preserved state"""
        
    def stop_session(self) -> SessionStats:
        """Finalize session and return statistics"""
        
    def get_next_sample_id(self) -> str:
        """
        Generate next sequential sample ID
        Format: Zero-padded 4-digit (0001, 0002, ..., 9999)
        Persists across sessions
        """
        
    def get_current_session_dir(self) -> Path:
        """Get current session's data directory"""
        
    def save_state(self) -> None:
        """Persist state to session_state.json"""
        
    def load_state(self) -> None:
        """Restore state from session_state.json"""

@dataclass
class SessionState:
    current_session_id: str
    sample_counter: int
    recording_state: RecordingState
    total_samples: int
    session_start_time: datetime

class RecordingState(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
```

### 4. Manifest Generator Component

**Responsibility**: Create and update SpeechBrain-compatible CSV manifest with atomic operations.

**Technology**: Python CSV writer with file locking

**Interface**:
```python
class ManifestGenerator:
    def __init__(self, manifest_path: Path = "manifest.csv"):
        """Initialize manifest generator with CSV file path"""
        
    def initialize_manifest(self) -> None:
        """
        Create manifest.csv with headers if not exists
        Headers: sample_id, file_path, transcript, duration_sec, 
                 sample_rate, session_id, timestamp, whisper_confidence
        """
        
    def append_sample(self, sample_data: SampleMetadata) -> None:
        """
        Atomically append sample row to manifest
        Args:
            sample_data: Complete sample metadata
        Ensures: Atomic write with file locking
        Performance: <100ms per operation
        """
        
    def validate_manifest(self) -> ValidationReport:
        """
        Validate manifest integrity
        Checks:
        - All file paths exist
        - Sample IDs are unique
        - Required columns present
        - Duration matches actual file duration
        Returns: ValidationReport with issues list
        """

@dataclass
class SampleMetadata:
    sample_id: str
    file_path: str  # Relative path from project root
    transcript: str
    duration_sec: float
    sample_rate: int
    session_id: str
    timestamp: str  # ISO 8601 format
    whisper_confidence: float

@dataclass
class ValidationReport:
    is_valid: bool
    missing_files: List[str]
    duplicate_ids: List[str]
    format_errors: List[str]
    total_samples: int
```

### 5. WebSocket Server Component

**Responsibility**: Broadcast real-time events to connected frontend clients.

**Technology**: FastAPI WebSocket with asyncio event broadcasting

**Interface**:
```python
class WebSocketManager:
    def __init__(self):
        """Initialize WebSocket connection manager"""
        
    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register new WebSocket connection"""
        
    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove WebSocket connection"""
        
    async def broadcast(self, message: WSMessage) -> None:
        """
        Send message to all connected clients
        Latency target: <500ms
        """

@dataclass
class WSMessage:
    event_type: str  # "sample_recorded", "transcription_complete", "state_change"
    payload: dict
    timestamp: str

# Message Types:
# 1. sample_recorded: {"sample_id": "0001"}
# 2. transcription_complete: {"sample_id": "0001", "transcript": "hello", "confidence": 0.85}
# 3. state_change: {"state": "active", "session_id": "session_20240115_143022"}
# 4. stats_update: {"total_samples": 42, "session_samples": 15}
# 5. quality_warning: {"warning_type": "low_confidence", "sample_id": "0001"}
# 6. error: {"error_message": "Transcription failed", "severity": "warning"}
```

### 6. Recording Loop Controller

**Responsibility**: Orchestrate the automated recording cycle with proper error handling.

**Technology**: asyncio task management with exception handling

**Interface**:
```python
class RecordingLoopController:
    def __init__(
        self,
        audio_recorder: AudioRecorder,
        transcription_engine: TranscriptionEngine,
        session_manager: SessionManager,
        manifest_generator: ManifestGenerator,
        websocket_manager: WebSocketManager
    ):
        """Initialize recording loop with all dependencies"""
        
    async def start_loop(self) -> None:
        """
        Start automated recording loop
        Executes: beep → wait → record → save → transcribe → update
        Continues until pause/stop signal
        """
        
    async def execute_cycle(self) -> None:
        """
        Execute single recording cycle
        Steps:
        1. Play beep (0.5s)
        2. Wait (1s)
        3. Record audio (5s)
        4. Save WAV file
        5. Transcribe audio (1-2s)
        6. Update manifest
        7. Broadcast events via WebSocket
        Total cycle time: ~7-8 seconds
        """
        
    def pause_loop(self) -> None:
        """Signal loop to pause after current cycle"""
        
    def stop_loop(self) -> None:
        """Signal loop to stop after current cycle"""
```

### 7. REST API Endpoints

**Responsibility**: Provide HTTP endpoints for session control and status queries.

**Technology**: FastAPI route handlers with JSON responses

**Endpoints**:

```python
# Session Control
POST /api/session/start
Response: {"session_id": str, "status": "started"}

POST /api/session/pause
Response: {"status": "paused", "sample_id": str}

POST /api/session/resume
Response: {"status": "resumed", "session_id": str}

POST /api/session/stop
Response: {"status": "stopped", "total_samples": int, "session_duration": float}

# Status Queries
GET /api/session/status
Response: {
    "state": str,  # "idle", "active", "paused", "stopped"
    "current_session_id": str,
    "sample_counter": int,
    "total_samples": int
}

GET /api/stats
Response: {
    "total_samples": int,
    "total_sessions": int,
    "total_duration_minutes": float,
    "last_session_id": str
}

GET /api/manifest/validate
Response: {
    "is_valid": bool,
    "missing_files": List[str],
    "duplicate_ids": List[str],
    "format_errors": List[str]
}
```

### 8. Frontend Components

**Responsibility**: Provide user interface for recording control and real-time feedback.

**Technology**: React functional components with WebSocket hooks

**Component Structure**:

```
App (Root Component)
├── WebSocketProvider (Context for WebSocket connection)
├── ControlPanel
│   ├── StartButton
│   ├── PauseButton
│   ├── ResumeButton
│   └── StopButton
├── VisualOrb
│   ├── GlowAnimation (CSS keyframes)
│   └── CountdownDisplay (5, 4, 3, 2, 1)
├── StatsDisplay
│   ├── TotalSamplesCounter
│   └── SessionSamplesCounter
└── TranscriptFeed
    └── TranscriptEntry[] (last 10 samples)
        ├── SampleID
        ├── TranscriptText
        └── ConfidenceScore (with warning highlight)
```

**React Component Interfaces**:

```typescript
// WebSocket Context
interface WebSocketContextValue {
    socket: WebSocket | null;
    isConnected: boolean;
    sendMessage: (msg: WSMessage) => void;
}

// Control Panel
interface ControlPanelProps {
    recordingState: RecordingState;
    onStart: () => void;
    onPause: () => void;
    onResume: () => void;
    onStop: () => void;
}

// Visual Orb
interface VisualOrbProps {
    isRecording: boolean;
    countdown: number | null;  // null when not counting
    isBeeping: boolean;
}

// Transcript Feed
interface TranscriptEntry {
    sampleId: string;
    transcript: string;
    confidence: number;
    timestamp: string;
}

interface TranscriptFeedProps {
    entries: TranscriptEntry[];
    maxEntries: number;  // 10
}
```

## Data Models

### 1. Manifest CSV Schema

**File**: `manifest.csv` (project root)

**Format**: CSV with header row

**Columns**:
```csv
sample_id,file_path,transcript,duration_sec,sample_rate,session_id,timestamp,whisper_confidence
0001,data/session_20240115_143022/sample_0001.wav,hello world,5.0,16000,session_20240115_143022,2024-01-15T14:30:27Z,0.89
0002,data/session_20240115_143022/sample_0002.wav,__unclear__,5.0,16000,session_20240115_143022,2024-01-15T14:30:35Z,0.23
```

**Field Specifications**:
- `sample_id`: Zero-padded 4-digit string (0001-9999)
- `file_path`: Relative path from project root (forward slashes for portability)
- `transcript`: UTF-8 text or `__unclear__` for low confidence
- `duration_sec`: Float, typically 5.0
- `sample_rate`: Integer, typically 16000
- `session_id`: Session identifier (session_YYYYMMDD_HHMMSS)
- `timestamp`: ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
- `whisper_confidence`: Float 0.0-1.0

### 2. Session State JSON Schema

**File**: `session_state.json` (project root)

**Format**: JSON

**Schema**:
```json
{
  "current_session_id": "session_20240115_143022",
  "sample_counter": 42,
  "recording_state": "paused",
  "total_samples": 156,
  "session_start_time": "2024-01-15T14:30:22Z",
  "last_sample_id": "0156"
}
```

**Field Specifications**:
- `current_session_id`: String, current or last session identifier
- `sample_counter`: Integer, next sample ID to assign (global counter)
- `recording_state`: Enum string ("idle", "active", "paused", "stopped")
- `total_samples`: Integer, cumulative samples across all sessions
- `session_start_time`: ISO 8601 timestamp
- `last_sample_id`: String, most recent sample ID

### 3. WebSocket Message Schema

**Format**: JSON over WebSocket

**Message Types**:

```typescript
// 1. Sample Recorded Event
{
  "event_type": "sample_recorded",
  "payload": {
    "sample_id": "0001",
    "file_path": "data/session_20240115_143022/sample_0001.wav"
  },
  "timestamp": "2024-01-15T14:30:27Z"
}

// 2. Transcription Complete Event
{
  "event_type": "transcription_complete",
  "payload": {
    "sample_id": "0001",
    "transcript": "hello world",
    "confidence": 0.89,
    "is_unclear": false
  },
  "timestamp": "2024-01-15T14:30:29Z"
}

// 3. State Change Event
{
  "event_type": "state_change",
  "payload": {
    "state": "active",
    "session_id": "session_20240115_143022"
  },
  "timestamp": "2024-01-15T14:30:22Z"
}

// 4. Stats Update Event
{
  "event_type": "stats_update",
  "payload": {
    "total_samples": 156,
    "session_samples": 15
  },
  "timestamp": "2024-01-15T14:30:29Z"
}

// 5. Quality Warning Event
{
  "event_type": "quality_warning",
  "payload": {
    "warning_type": "low_confidence",
    "sample_id": "0002",
    "confidence": 0.23
  },
  "timestamp": "2024-01-15T14:30:35Z"
}

// 6. Duplicate Detection Warning
{
  "event_type": "quality_warning",
  "payload": {
    "warning_type": "duplicate_detection",
    "transcript": "test test test",
    "occurrence_count": 5
  },
  "timestamp": "2024-01-15T14:31:05Z"
}

// 7. Error Event
{
  "event_type": "error",
  "payload": {
    "error_message": "Microphone not accessible",
    "severity": "critical",
    "retry_possible": false
  },
  "timestamp": "2024-01-15T14:30:30Z"
}
```

### 4. Configuration YAML Schema

**File**: `config.yaml` (project root)

**Format**: YAML

**Schema**:
```yaml
audio:
  sample_rate: 16000
  duration: 5.0
  channels: 1
  beep_duration: 0.5
  beep_frequency: 800

transcription:
  model_size: "base"  # Options: tiny, base, small, medium, large
  confidence_threshold: 0.4
  device: "cpu"  # Options: cpu, cuda

recording:
  loop_delay: 1.0  # Seconds between beep and recording
  auto_start_next_cycle: true

paths:
  data_dir: "data"
  manifest_file: "manifest.csv"
  state_file: "session_state.json"
  logs_dir: "logs"

quality:
  duplicate_detection_threshold: 5
  enable_quality_warnings: true
  log_low_confidence_samples: true
```

### 5. Directory Structure

```
project_root/
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── audio_recorder.py       # AudioRecorder component
│   ├── transcription_engine.py # TranscriptionEngine component
│   ├── session_manager.py      # SessionManager component
│   ├── manifest_generator.py   # ManifestGenerator component
│   ├── websocket_manager.py    # WebSocketManager component
│   ├── recording_loop.py       # RecordingLoopController component
│   └── models.py               # Data classes and schemas
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ControlPanel.jsx
│   │   │   ├── VisualOrb.jsx
│   │   │   ├── StatsDisplay.jsx
│   │   │   └── TranscriptFeed.jsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.js
│   │   └── styles/
│   │       └── App.css
│   └── package.json
├── data/                       # Generated during recording
│   ├── session_20240115_143022/
│   │   ├── sample_0001.wav
│   │   ├── sample_0002.wav
│   │   └── ...
│   └── session_20240115_154530/
│       └── ...
├── logs/
│   ├── quality_warnings.log
│   └── system.log
├── manifest.csv                # SpeechBrain manifest
├── session_state.json          # Persistent session state
├── config.yaml                 # Configuration file
└── README.md
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

This section defines universal properties that should hold across all valid inputs for the ASTA Voice Dataset Collector. These properties focus on the pure logic components that can be verified through property-based testing, while UI rendering, hardware I/O, and external library integrations are covered by integration and example-based tests.

### Property Reflection Analysis

After reviewing all acceptance criteria, we identified the following categories of testable properties:

**Core Logic Properties** (Pure functions, suitable for PBT):
- Sample ID generation and formatting
- Session ID generation and formatting
- State persistence round-trips
- Confidence score thresholding
- Timestamp formatting
- Path conversion (absolute to relative)
- Validation logic (uniqueness, presence, consistency)
- Duplicate detection
- Counter management and increment logic
- Transcript list management (last N entries)

**Integration/Example Tests** (Side effects, hardware, external libraries):
- Audio recording (SoundDevice integration)
- Transcription (Faster Whisper integration)
- File I/O operations
- WebSocket communication
- UI rendering and animations
- Error recovery scenarios

**Redundancy Elimination**:
- Properties 1.4, 1.5, 1.7 (Sample ID generation) can be combined into a single comprehensive property
- Properties 2.5 and 11.1 (confidence thresholding) are identical—consolidate to one
- Properties 3.3, 3.4, 3.7 (state persistence) can be combined as a round-trip property
- Properties 10.2, 10.3 (transcript entry data) can be combined into one property
- Properties 13.1, 13.2, 13.3, 13.5, 13.7 (validation checks) can be consolidated into fewer comprehensive properties

### Property 1: Sample ID Sequential Formatting

*For any* non-negative integer counter value from 0 to 9999, the generated Sample_ID SHALL be a zero-padded 4-digit string, and incrementing the counter SHALL produce sequential IDs that preserve order.

**Validates: Requirements 1.4, 1.5, 1.7**

**Test Strategy**: Generate random counter values (0-9999), verify format is always "XXXX" with leading zeros, and verify that counter + 1 produces the next sequential ID.

### Property 2: Session ID Timestamp Formatting

*For any* valid datetime, the generated session identifier SHALL follow the format "session_YYYYMMDD_HHMMSS" where each component is correctly zero-padded.

**Validates: Requirements 3.1**

**Test Strategy**: Generate random datetimes, verify session ID format matches pattern and components are correctly extracted.

### Property 3: Confidence Threshold Classification

*For any* confidence score in the range [0.0, 1.0], transcripts with scores below 0.4 SHALL be labeled as "__unclear__" and scores at or above 0.4 SHALL use the actual transcript text.

**Validates: Requirements 2.5, 11.1**

**Test Strategy**: Generate random confidence scores across the full range, verify classification boundary at 0.4 is correct.

### Property 4: State Persistence Round-Trip

*For any* valid session state (including session ID, counter value, recording state, and metadata), saving the state to disk and then loading it SHALL restore an equivalent state where all fields match the original.

**Validates: Requirements 3.2, 3.3, 3.4, 3.7**

**Test Strategy**: Generate random session states with various counter values and states, serialize to JSON, deserialize, and verify equivalence.

### Property 5: Relative Path Conversion

*For any* absolute file path within the project directory, converting to a relative path SHALL produce a portable path that uses forward slashes and is relative to the project root.

**Validates: Requirements 4.4**

**Test Strategy**: Generate various absolute paths (with different OS separators), verify relative path conversion is correct and portable.

### Property 6: ISO 8601 Timestamp Formatting

*For any* valid datetime object, formatting as ISO 8601 SHALL produce a string matching the pattern "YYYY-MM-DDTHH:MM:SSZ" with correct zero-padding and UTC timezone indicator.

**Validates: Requirements 4.5**

**Test Strategy**: Generate random datetimes, verify ISO 8601 format is correct and parseable.

### Property 7: Manifest CSV Schema Validation

*For any* manifest CSV file, the header row SHALL contain exactly the required columns (sample_id, file_path, transcript, duration_sec, sample_rate, session_id, timestamp, whisper_confidence) in the correct order.

**Validates: Requirements 4.2, 13.3**

**Test Strategy**: Generate manifests with various header combinations, verify required columns are detected and order is validated.

### Property 8: Sample ID Uniqueness Validation

*For any* list of sample IDs in a manifest, the validation SHALL correctly identify all duplicate IDs and report them, and for lists with all unique IDs, validation SHALL pass with no duplicates reported.

**Validates: Requirements 13.2**

**Test Strategy**: Generate lists with known duplicates and unique lists, verify duplicate detection is accurate.

### Property 9: Sample Rate Consistency Validation

*For any* list of sample rate values in a manifest, the validation SHALL detect inconsistencies when multiple different values are present, and SHALL pass when all values are identical.

**Validates: Requirements 13.5**

**Test Strategy**: Generate lists with uniform and mixed sample rates, verify consistency checking.

### Property 10: Duplicate Transcript Detection

*For any* sequence of transcripts, when the same transcript text appears 5 or more consecutive times, the system SHALL detect and flag this as a duplicate pattern, and sequences with fewer than 5 consecutive duplicates SHALL not trigger the warning.

**Validates: Requirements 11.2**

**Test Strategy**: Generate transcript sequences with various repetition patterns, verify detection threshold at 5 consecutive duplicates.

### Property 11: Counter Increment Invariant

*For any* pair of counter values (total_samples, session_samples), recording a new sample SHALL increment both counters by exactly 1, and the relationship (total_samples ≥ session_samples) SHALL always hold.

**Validates: Requirements 9.3**

**Test Strategy**: Generate random counter pairs, verify increment behavior and invariant preservation.

### Property 12: Transcript Feed Window Management

*For any* list of transcript entries, maintaining the last 10 entries SHALL preserve chronological order and discard older entries, such that adding N new entries to a feed with M entries results in min(N + M, 10) entries with the most recent 10 preserved in order.

**Validates: Requirements 10.1**

**Test Strategy**: Generate transcript lists of various sizes, add new entries, verify only last 10 are kept in chronological order.

### Property 13: Transcript Entry Completeness

*For any* transcript entry displayed in the feed, it SHALL contain all required fields (sample_id, transcript text, confidence score) with no null or missing values.

**Validates: Requirements 10.2, 10.3, 10.4**

**Test Strategy**: Generate random transcript entries, verify all required fields are present and non-null.

### Property 14: Confidence Score Percentage Conversion

*For any* confidence score in the range [0.0, 1.0], converting to a percentage SHALL produce a value in the range [0, 100] where percentage = confidence × 100, with appropriate rounding.

**Validates: Requirements 10.4**

**Test Strategy**: Generate random confidence scores, verify percentage conversion is mathematically correct.

### Property 15: Low Confidence Highlighting Threshold

*For any* transcript entry with a confidence score, entries with percentage < 40% SHALL be flagged for warning highlighting, and entries with percentage ≥ 40% SHALL not be flagged.

**Validates: Requirements 10.5**

**Test Strategy**: Generate entries with various confidence percentages, verify highlighting threshold at 40%.

### Property 16: Button State Consistency

*For any* recording state (IDLE, ACTIVE, PAUSED, STOPPED), the UI button states SHALL follow the rules: start button enabled only in IDLE/STOPPED, pause button enabled only in ACTIVE, resume button enabled only in PAUSED, and stop button enabled in ACTIVE/PAUSED.

**Validates: Requirements 7.5, 7.6**

**Test Strategy**: Test all recording states, verify button enabled/disabled states follow the state machine rules.

### Property 17: Session Directory Structure

*For any* session ID in the format "session_YYYYMMDD_HHMMSS", the corresponding directory path SHALL be "data/session_YYYYMMDD_HHMMSS" and sample files SHALL be stored as "sample_XXXX.wav" within that directory.

**Validates: Requirements 1.8, 14.2, 14.3**

**Test Strategy**: Generate random session IDs, verify directory structure and file naming follow the pattern.

### Property 18: Validation Report Completeness

*For any* validation operation that detects issues (missing files, duplicate IDs, format errors, consistency errors), the validation report SHALL include ALL detected issues with no omissions, and for valid manifests with no issues, the report SHALL correctly indicate no errors.

**Validates: Requirements 13.6, 13.7**

**Test Strategy**: Generate manifests with known issues and valid manifests, verify report completeness and accuracy.

### Property 19: Countdown Display Mapping

*For any* recording progress time remaining t in seconds where 0 ≤ t ≤ 5, the countdown display SHALL show ceiling(t), resulting in the sequence 5, 4, 3, 2, 1, 0 as time progresses from 5.0 to 0.0 seconds.

**Validates: Requirements 8.3**

**Test Strategy**: Generate random time values in the range [0, 5], verify countdown display is correct.

## Error Handling

### Backend Error Handling Strategy

**1. Audio Recording Errors**
- **Scenario**: Microphone not accessible, buffer overflow
- **Handling**: Log error, notify frontend via WebSocket, retry current sample once
- **Recovery**: If retry fails, pause recording and await user intervention

**2. Transcription Errors**
- **Scenario**: Faster Whisper model failure, OOM error
- **Handling**: Label sample as `__unclear__`, log error, continue recording
- **Recovery**: Non-blocking, next sample proceeds normally

**3. Manifest Update Errors**
- **Scenario**: Disk full, file lock timeout, permission denied
- **Handling**: Queue update in memory, retry with exponential backoff
- **Recovery**: Attempt flush on next successful write or session stop

**4. WebSocket Connection Errors**
- **Scenario**: Client disconnect, network timeout
- **Handling**: Remove connection from active list, log disconnect
- **Recovery**: Client automatically reconnects, state sync on reconnection

**5. File System Errors**
- **Scenario**: Directory creation failure, WAV write error
- **Handling**: Pause recording, log critical error, notify frontend
- **Recovery**: Require user to resolve disk space or permissions

### Frontend Error Handling Strategy

**1. WebSocket Connection Loss**
- **Handling**: Display "Reconnecting..." indicator, attempt reconnect every 2 seconds
- **Recovery**: Resume normal operation once reconnected

**2. API Request Failures**
- **Handling**: Display error notification, enable retry button
- **Recovery**: User-initiated retry or automatic retry for transient errors

**3. Invalid Server Responses**
- **Handling**: Log error to console, display generic error message
- **Recovery**: Refresh application state with GET /api/session/status

### Error Logging

**Structure**:
```python
logger.error(
    "Audio recording failed",
    extra={
        "sample_id": sample_id,
        "error_type": "MicrophoneAccessError",
        "retry_count": 1,
        "timestamp": datetime.utcnow().isoformat()
    }
)
```

**Log Files**:
- `logs/system.log`: All application logs (INFO, WARNING, ERROR)
- `logs/quality_warnings.log`: Quality-specific warnings (low confidence, duplicates)

## Testing Strategy

### Testing Approach Overview

The ASTA Voice Dataset Collector employs a **dual testing strategy** combining property-based testing for pure logic components with example-based and integration tests for I/O, hardware integration, and UI components.

**Property-Based Testing Scope**:
- Pure logic functions (ID generation, formatting, validation)
- State management and persistence
- Counter and collection management
- Threshold and classification logic

**Example-Based + Integration Testing Scope**:
- Hardware I/O (audio recording via SoundDevice)
- External libraries (Faster Whisper transcription)
- File system operations
- WebSocket communication
- UI rendering and animations

### Property-Based Testing Configuration

**Framework**: Hypothesis (Python backend), fast-check (TypeScript/JavaScript frontend)

**Configuration**:
- Minimum 100 iterations per property test (due to randomization)
- Each property test MUST reference its design document property
- Tag format: `# Feature: asta-voice-collector, Property {number}: {property_text}`

**Example Property Test Structure** (Python with Hypothesis):
```python
from hypothesis import given, strategies as st

@given(counter=st.integers(min_value=0, max_value=9999))
def test_property_1_sample_id_sequential_formatting(counter):
    """
    Feature: asta-voice-collector, Property 1: Sample ID Sequential Formatting
    For any non-negative integer counter value from 0 to 9999,
    the generated Sample_ID SHALL be a zero-padded 4-digit string.
    """
    sample_id = generate_sample_id(counter)
    
    # Property assertions
    assert len(sample_id) == 4
    assert sample_id.isdigit()
    assert int(sample_id) == counter
    
    # Sequential property
    next_id = generate_sample_id(counter + 1)
    assert int(next_id) == counter + 1
```

### Unit Testing

**Backend Components**:

1. **SessionManager** (Property Tests):
   - Property 1: Sample ID formatting and sequencing
   - Property 2: Session ID timestamp formatting
   - Property 4: State persistence round-trip
   - Property 11: Counter increment invariant
   - Property 17: Session directory structure

2. **TranscriptionEngine** (Property + Example Tests):
   - Property 3: Confidence threshold classification
   - Example: Silent audio returns "__unclear__"
   - Integration: Faster Whisper model loading and transcription

3. **ManifestGenerator** (Property Tests):
   - Property 5: Relative path conversion
   - Property 6: ISO 8601 timestamp formatting
   - Property 7: CSV schema validation
   - Property 18: Validation report completeness
   - Example: Manifest creation and append operations

4. **Quality Module** (Property Tests):
   - Property 8: Sample ID uniqueness validation
   - Property 9: Sample rate consistency validation
   - Property 10: Duplicate transcript detection

5. **AudioRecorder** (Integration Tests):
   - Mock SoundDevice for unit tests
   - Integration tests with real microphone
   - WAV file format verification

6. **WebSocketManager** (Integration Tests):
   - Mock WebSocket connections
   - Message broadcast logic
   - Connection state management

**Frontend Components**:

1. **Counter Components** (Property Tests):
   - Property 11: Counter increment behavior
   - Property 14: Confidence percentage conversion

2. **TranscriptFeed** (Property Tests):
   - Property 12: Last 10 entries window management
   - Property 13: Entry completeness
   - Property 15: Low confidence highlighting threshold

3. **ControlPanel** (Property Tests):
   - Property 16: Button state consistency across recording states

4. **VisualOrb** (Property + Example Tests):
   - Property 19: Countdown display mapping
   - Example: Animation state transitions

5. **useWebSocket Hook** (Integration Tests):
   - Mock WebSocket for reconnection logic
   - Message handling and state updates

**Test Frameworks**: 
- Backend: pytest + Hypothesis
- Frontend: Jest + React Testing Library + fast-check

**Coverage Target**: 80% line coverage for core business logic, 100% property coverage

### Integration Testing

**Recording Loop**:
- Test complete cycle: start → beep → record → transcribe → manifest update
- Verify WebSocket events broadcast correctly
- Test pause/resume/stop during active recording

**API Endpoints**:
- Test session lifecycle via REST API
- Verify state persistence across restart
- Test manifest validation endpoint

**Frontend-Backend Integration**:
- Test WebSocket message handling end-to-end
- Verify UI updates on state changes
- Test error notification flow

### Manual Testing Checklist

1. **Cross-Platform**:
   - Test on Windows, Linux, macOS
   - Verify microphone detection on each platform
   - Check file path handling

2. **Long-Running Sessions**:
   - Record 100+ samples continuously
   - Verify no memory leaks
   - Check manifest integrity

3. **Error Scenarios**:
   - Disconnect microphone during recording
   - Fill disk during recording
   - Kill and restart application mid-session

4. **Quality Checks**:
   - Test with clear speech
   - Test with background noise
   - Test with silence
   - Verify low confidence detection

## Performance Considerations

### Backend Performance

**1. Transcription Latency**
- **Target**: <2 seconds per 5-second sample
- **Optimization**: Use Faster Whisper (optimized for inference speed)
- **Consideration**: Base model provides best speed/accuracy tradeoff

**2. Manifest Update Latency**
- **Target**: <100ms per append operation
- **Optimization**: Use append mode, avoid reading entire file
- **Consideration**: File locking may add 10-20ms overhead

**3. WebSocket Broadcast Latency**
- **Target**: <500ms from event to UI update
- **Optimization**: asyncio ensures non-blocking broadcast
- **Consideration**: Multiple clients may increase latency slightly

**4. Memory Usage**
- **Audio Buffer**: 16kHz * 5s * 2 bytes = 160KB per sample
- **Faster Whisper Model**: ~140MB (base model)
- **Total Backend**: ~300MB steady state
- **Optimization**: Clear audio buffers immediately after save

### Frontend Performance

**1. Rendering Performance**
- **Target**: 60 FPS during animations
- **Optimization**: CSS animations (GPU-accelerated)
- **Consideration**: Limit transcript feed to 10 entries

**2. WebSocket Message Handling**
- **Target**: Process messages without blocking UI thread
- **Optimization**: Use React state batching
- **Consideration**: Throttle stats updates to 1 per second max

### Scalability Considerations

**Current Scope** (MVP):
- Single user, local machine
- Sessions up to 4 hours
- Sample IDs limited to 9999 (4 digits)

**Future Scalability**:
- Expand sample ID to 6 digits (999,999 samples)
- Add database backend for large datasets
- Support multiple concurrent users (requires session isolation)

## Deployment

### Development Setup

**Backend**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn sounddevice faster-whisper pyyaml numpy scipy
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd frontend
npm install
npm start  # Development server on port 3000
```

### Production Deployment

**Backend**:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

**Frontend**:
```bash
npm run build
# Serve build/ directory with any static file server
```

**Configuration**:
- Copy `config.yaml.example` to `config.yaml`
- Adjust paths and model settings as needed
- Ensure microphone permissions granted

### System Requirements

**Minimum**:
- CPU: Quad-core (Intel i5 or equivalent)
- RAM: 4GB available
- Storage: 10GB free (for ~1000 samples)
- OS: Windows 10+, Ubuntu 20.04+, macOS 11+
- Python: 3.10+
- Node.js: 16+

**Recommended**:
- CPU: Hexa-core (Intel i7 or equivalent)
- RAM: 8GB available
- Storage: 50GB free
- GPU: Optional (Faster Whisper supports CUDA)

## Security Considerations

**1. Local-Only Operation**
- No external API calls
- No cloud dependencies
- All data remains on local file system

**2. File System Access**
- Application requires read/write permissions in project directory
- Microphone access required for recording

**3. WebSocket Security**
- Local connections only (no external exposure)
- No authentication required (single-user local application)

**4. Data Privacy**
- Audio files stored unencrypted locally
- No telemetry or analytics
- User responsible for data backup and security

## Future Enhancements

### Phase 2 Enhancements
1. **Advanced Quality Filters**:
   - SNR (Signal-to-Noise Ratio) calculation
   - Automatic silence trimming
   - Volume normalization

2. **Dataset Management**:
   - Export to ZIP for sharing
   - Import existing datasets
   - Merge multiple manifests

3. **Enhanced UI**:
   - Waveform visualization during recording
   - Playback of recorded samples
   - Manual transcript editing

4. **Multi-Speaker Support**:
   - Speaker profile management
   - Speaker identification in manifest
   - Multi-speaker fine-tuning support

5. **Advanced Transcription**:
   - Multiple Whisper model sizes
   - Language selection
   - Custom vocabulary support

### Technical Debt Considerations
- Add comprehensive type hints (Python 3.10+)
- Implement dependency injection for better testability
- Add OpenAPI documentation for REST API
- Create Docker containerization for easier deployment
- Add database backend for large-scale datasets (>10k samples)

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-15  
**Status**: Draft for Review
