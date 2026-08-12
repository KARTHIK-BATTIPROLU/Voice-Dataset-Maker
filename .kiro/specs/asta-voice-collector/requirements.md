# Requirements Document

## Introduction

The ASTA Voice Dataset Collector is a local, zero-cost platform for collecting and preparing voice datasets for custom speaker verification model training. The system automatically records audio samples, transcribes them using local speech recognition, labels the samples, and generates a structured manifest file compatible with SpeechBrain ECAPA-TDNN fine-tuning workflows. The platform eliminates manual file management and ensures dataset quality through automated validation and quality safeguards.

## Glossary

- **Recording_Backend**: The FastAPI service that handles audio recording, transcription, and data management
- **Frontend_UI**: The React web application that provides user controls and real-time feedback
- **Audio_Recorder**: The SoundDevice-based component that captures audio in 5-second chunks
- **Transcription_Engine**: The Faster Whisper component that converts audio to text locally
- **Session_Manager**: The component that tracks recording sessions and manages state persistence
- **Manifest_Generator**: The component that creates and updates the SpeechBrain-compatible CSV manifest
- **WebSocket_Server**: The component that provides real-time updates to the frontend
- **Sample**: A single 5-second audio recording with associated metadata
- **Recording_Session**: A continuous recording period with a unique session identifier
- **Manifest_File**: The CSV file containing all sample metadata in SpeechBrain format
- **Confidence_Score**: A numeric value (0-1) indicating transcription reliability
- **Sample_ID**: A zero-padded 4-digit unique identifier for each audio sample

## Requirements

### Requirement 1: Audio Recording

**User Story:** As a dataset creator, I want the system to automatically record 5-second audio chunks, so that I can collect standardized voice samples without manual recording management.

#### Acceptance Criteria

1. WHEN a recording session is started, THE Audio_Recorder SHALL record audio at 16kHz sample rate in mono format
2. THE Audio_Recorder SHALL capture exactly 5 seconds of audio per sample
3. THE Audio_Recorder SHALL save each sample as a WAV file with 16-bit PCM encoding
4. WHEN a sample is recorded, THE Audio_Recorder SHALL generate a unique Sample_ID using zero-padded 4-digit format
5. THE Audio_Recorder SHALL continue Sample_ID numbering across sessions without reset
6. WHEN recording is paused, THE Audio_Recorder SHALL stop capturing audio immediately
7. WHEN recording is resumed, THE Audio_Recorder SHALL continue with the next sequential Sample_ID
8. THE Audio_Recorder SHALL store WAV files in a structured directory organized by session

### Requirement 2: Local Transcription

**User Story:** As a dataset creator, I want audio samples automatically transcribed using local speech recognition, so that each sample is labeled without cloud costs or privacy concerns.

#### Acceptance Criteria

1. WHEN a sample is recorded, THE Transcription_Engine SHALL transcribe the audio using Faster Whisper base model
2. THE Transcription_Engine SHALL execute transcription entirely on the local machine
3. THE Transcription_Engine SHALL produce a transcript string for each sample
4. THE Transcription_Engine SHALL calculate a Confidence_Score for each transcription
5. WHEN the Confidence_Score is below 0.4, THE Transcription_Engine SHALL label the transcript as "__unclear__"
6. THE Transcription_Engine SHALL process transcriptions within 2 seconds of sample completion
7. THE Transcription_Engine SHALL handle audio without speech by returning "__unclear__" label

### Requirement 3: Session Management

**User Story:** As a dataset creator, I want to start, pause, resume, and stop recording sessions, so that I can control data collection flexibly.

#### Acceptance Criteria

1. WHEN the user initiates recording, THE Session_Manager SHALL create a new Recording_Session with a unique session identifier
2. THE Session_Manager SHALL persist session state to disk
3. WHEN the user pauses recording, THE Session_Manager SHALL preserve the current Sample_ID counter
4. WHEN the user resumes recording, THE Session_Manager SHALL restore the Sample_ID counter from the previous state
5. WHEN the user stops recording, THE Session_Manager SHALL finalize the session and update the Manifest_File
6. THE Session_Manager SHALL track session metadata including start time, end time, and total samples collected
7. WHEN the application restarts, THE Session_Manager SHALL load the previous session state

### Requirement 4: Manifest Generation

**User Story:** As a machine learning engineer, I want a SpeechBrain-compatible manifest file automatically generated, so that I can immediately use the dataset for model fine-tuning.

#### Acceptance Criteria

1. THE Manifest_Generator SHALL create a CSV file named "manifest.csv" in the project root directory
2. THE Manifest_Generator SHALL include columns: sample_id, file_path, transcript, duration_sec, sample_rate, session_id, timestamp, whisper_confidence
3. WHEN a new sample is transcribed, THE Manifest_Generator SHALL append a row to the manifest file
4. THE Manifest_Generator SHALL use relative file paths for portability
5. THE Manifest_Generator SHALL format timestamps in ISO 8601 format
6. THE Manifest_Generator SHALL preserve the manifest file across sessions
7. THE Manifest_Generator SHALL update the manifest atomically to prevent corruption

### Requirement 5: Recording Loop Automation

**User Story:** As a dataset creator, I want an automated recording loop with audio cues, so that I can produce continuous samples without manual intervention.

#### Acceptance Criteria

1. WHEN a recording session is active, THE Recording_Backend SHALL execute the sequence: beep → record → save → transcribe → label → update manifest
2. THE Recording_Backend SHALL play an audio beep before each 5-second recording
3. THE Recording_Backend SHALL wait 1 second between the beep and recording start
4. THE Recording_Backend SHALL automatically start the next recording cycle after completing the current cycle
5. WHEN recording is paused, THE Recording_Backend SHALL complete the current cycle before pausing
6. THE Recording_Backend SHALL continue the loop until the user pauses or stops the session

### Requirement 6: Real-time Frontend Updates

**User Story:** As a dataset creator, I want to see live updates on recording progress and transcripts, so that I can monitor data collection quality in real-time.

#### Acceptance Criteria

1. THE WebSocket_Server SHALL establish a WebSocket connection with the Frontend_UI
2. WHEN a sample is recorded, THE WebSocket_Server SHALL send the Sample_ID to the Frontend_UI
3. WHEN a sample is transcribed, THE WebSocket_Server SHALL send the transcript and Confidence_Score to the Frontend_UI
4. THE WebSocket_Server SHALL send session statistics including total samples and session samples
5. THE WebSocket_Server SHALL broadcast recording state changes (started, paused, resumed, stopped)
6. THE WebSocket_Server SHALL maintain connection state and reconnect on disconnection
7. THE WebSocket_Server SHALL send updates within 500 milliseconds of event occurrence

### Requirement 7: Frontend Recording Controls

**User Story:** As a dataset creator, I want intuitive controls to manage recording sessions, so that I can easily start, pause, resume, and stop data collection.

#### Acceptance Criteria

1. THE Frontend_UI SHALL display a start button to initiate recording
2. THE Frontend_UI SHALL display a pause button to temporarily halt recording
3. THE Frontend_UI SHALL display a resume button to continue paused recording
4. THE Frontend_UI SHALL display a stop button to terminate the recording session
5. WHEN recording is active, THE Frontend_UI SHALL disable the start button
6. WHEN recording is paused, THE Frontend_UI SHALL disable the pause button and enable the resume button
7. THE Frontend_UI SHALL use a dark theme with electric blue (#4F8EF7) accent color
8. THE Frontend_UI SHALL provide visual feedback on button hover and click

### Requirement 8: Visual Recording Indicators

**User Story:** As a dataset creator, I want visual feedback during recording, so that I know when to speak and when the system is processing.

#### Acceptance Criteria

1. THE Frontend_UI SHALL display a glowing orb indicator
2. WHEN the beep plays, THE Frontend_UI SHALL pulse the orb with electric blue glow
3. WHILE recording is in progress, THE Frontend_UI SHALL display a countdown from 5 to 0
4. THE Frontend_UI SHALL display the countdown centered within the orb
5. WHEN recording completes, THE Frontend_UI SHALL reset the orb to idle state
6. THE Frontend_UI SHALL animate the orb transitions smoothly

### Requirement 9: Live Sample Counter

**User Story:** As a dataset creator, I want to see how many samples I've collected, so that I can track progress toward my dataset goal.

#### Acceptance Criteria

1. THE Frontend_UI SHALL display the total number of samples collected across all sessions
2. THE Frontend_UI SHALL display the number of samples in the current session
3. WHEN a new sample is recorded, THE Frontend_UI SHALL increment both counters
4. THE Frontend_UI SHALL update counters in real-time via WebSocket
5. THE Frontend_UI SHALL display counters prominently in the interface

### Requirement 10: Live Transcript Feed

**User Story:** As a dataset creator, I want to see recent transcripts with confidence scores, so that I can verify transcription quality during collection.

#### Acceptance Criteria

1. THE Frontend_UI SHALL display the last 10 transcripts in chronological order
2. THE Frontend_UI SHALL show the Sample_ID for each transcript entry
3. THE Frontend_UI SHALL show the transcript text for each entry
4. THE Frontend_UI SHALL show the Confidence_Score as a percentage for each entry
5. WHEN the Confidence_Score is below 40%, THE Frontend_UI SHALL highlight the entry with a warning color
6. THE Frontend_UI SHALL auto-scroll to show the most recent transcript
7. THE Frontend_UI SHALL update the feed in real-time as new samples are transcribed

### Requirement 11: Quality Safeguards

**User Story:** As a dataset creator, I want automatic quality checks during collection, so that I can identify and address low-quality samples.

#### Acceptance Criteria

1. WHEN the Confidence_Score is below 0.4, THE Recording_Backend SHALL flag the sample as low confidence
2. WHEN the same transcript appears 5 consecutive times, THE Recording_Backend SHALL send a duplicate detection warning
3. THE Recording_Backend SHALL log low confidence samples to a separate warnings file
4. THE Recording_Backend SHALL continue recording after detecting quality issues
5. THE Frontend_UI SHALL display a warning notification when low confidence samples occur
6. THE Frontend_UI SHALL display a warning notification when duplicate detection occurs

### Requirement 12: Backend API Endpoints

**User Story:** As a frontend developer, I want RESTful API endpoints to control recording, so that the UI can communicate with the backend.

#### Acceptance Criteria

1. THE Recording_Backend SHALL provide a POST /api/session/start endpoint to start recording
2. THE Recording_Backend SHALL provide a POST /api/session/pause endpoint to pause recording
3. THE Recording_Backend SHALL provide a POST /api/session/resume endpoint to resume recording
4. THE Recording_Backend SHALL provide a POST /api/session/stop endpoint to stop recording
5. THE Recording_Backend SHALL provide a GET /api/session/status endpoint to query current session state
6. THE Recording_Backend SHALL provide a GET /api/manifest/validate endpoint to validate manifest integrity
7. THE Recording_Backend SHALL provide a GET /api/stats endpoint to retrieve collection statistics
8. THE Recording_Backend SHALL return JSON responses with appropriate HTTP status codes
9. THE Recording_Backend SHALL handle errors gracefully and return descriptive error messages

### Requirement 13: Manifest Validation

**User Story:** As a dataset creator, I want to validate the manifest file, so that I can ensure data integrity before using the dataset for training.

#### Acceptance Criteria

1. THE Recording_Backend SHALL verify that all file paths in the manifest point to existing files
2. THE Recording_Backend SHALL verify that all Sample_IDs are unique
3. THE Recording_Backend SHALL verify that all required columns are present
4. THE Recording_Backend SHALL verify that duration values match actual audio file durations
5. THE Recording_Backend SHALL verify that sample rate values are consistent
6. THE Recording_Backend SHALL return a validation report with any detected issues
7. THE Recording_Backend SHALL flag missing files, duplicate IDs, and format errors

### Requirement 14: File Organization

**User Story:** As a dataset creator, I want audio files organized systematically, so that I can navigate and manage the dataset easily.

#### Acceptance Criteria

1. THE Recording_Backend SHALL create a "data" directory in the project root
2. THE Recording_Backend SHALL create a subdirectory for each session using the pattern "session_YYYYMMDD_HHMMSS"
3. THE Recording_Backend SHALL save audio files with the naming pattern "sample_{Sample_ID}.wav"
4. THE Recording_Backend SHALL save the manifest file in the project root directory
5. THE Recording_Backend SHALL create a "logs" directory for quality warnings and system logs

### Requirement 15: Configuration Management

**User Story:** As a system administrator, I want configurable parameters for the recording system, so that I can adjust settings without modifying code.

#### Acceptance Criteria

1. THE Recording_Backend SHALL load configuration from a "config.yaml" file
2. THE Recording_Backend SHALL support configuration of sample duration (default: 5 seconds)
3. THE Recording_Backend SHALL support configuration of sample rate (default: 16000 Hz)
4. THE Recording_Backend SHALL support configuration of confidence threshold (default: 0.4)
5. THE Recording_Backend SHALL support configuration of Faster Whisper model size (default: base)
6. THE Recording_Backend SHALL support configuration of beep duration (default: 0.5 seconds)
7. THE Recording_Backend SHALL use default values when configuration file is missing

### Requirement 16: State Persistence

**User Story:** As a dataset creator, I want session state saved automatically, so that I can resume collection after application restart.

#### Acceptance Criteria

1. THE Session_Manager SHALL save session state to a "session_state.json" file
2. THE Session_Manager SHALL update the state file after each sample is recorded
3. WHEN the application starts, THE Session_Manager SHALL load the previous session state if it exists
4. THE Session_Manager SHALL persist the current Sample_ID counter
5. THE Session_Manager SHALL persist the active session identifier
6. THE Session_Manager SHALL persist the recording state (active, paused, stopped)

### Requirement 17: Error Handling

**User Story:** As a dataset creator, I want robust error handling, so that recording continues despite transient failures.

#### Acceptance Criteria

1. WHEN audio recording fails, THE Recording_Backend SHALL log the error and retry the sample
2. WHEN transcription fails, THE Recording_Backend SHALL label the sample as "__unclear__" and continue
3. WHEN manifest update fails, THE Recording_Backend SHALL queue the update and retry
4. WHEN WebSocket connection fails, THE WebSocket_Server SHALL attempt reconnection
5. THE Recording_Backend SHALL continue the recording loop after recoverable errors
6. THE Recording_Backend SHALL notify the Frontend_UI of critical errors
7. THE Frontend_UI SHALL display error notifications to the user

### Requirement 18: Performance Requirements

**User Story:** As a dataset creator, I want efficient processing, so that I can collect samples continuously without delays.

#### Acceptance Criteria

1. THE Transcription_Engine SHALL complete transcription within 2 seconds per sample
2. THE Manifest_Generator SHALL update the manifest within 100 milliseconds
3. THE WebSocket_Server SHALL deliver updates with latency under 500 milliseconds
4. THE Audio_Recorder SHALL buffer audio without dropped frames
5. THE Recording_Backend SHALL support continuous recording for sessions exceeding 4 hours
6. THE Frontend_UI SHALL render updates without blocking the UI thread

### Requirement 19: Cross-Platform Compatibility

**User Story:** As a dataset creator, I want the platform to work on multiple operating systems, so that I can use my preferred development environment.

#### Acceptance Criteria

1. THE Recording_Backend SHALL run on Windows, Linux, and macOS
2. THE Audio_Recorder SHALL detect and use the default system microphone
3. THE Recording_Backend SHALL use platform-independent file paths
4. THE Frontend_UI SHALL render correctly in Chrome, Firefox, and Edge browsers
5. THE Recording_Backend SHALL handle file system differences across operating systems

### Requirement 20: Zero-Cost Operation

**User Story:** As a dataset creator, I want all processing to occur locally, so that I incur no cloud service costs.

#### Acceptance Criteria

1. THE Transcription_Engine SHALL use the locally-installed Faster Whisper model
2. THE Recording_Backend SHALL not make any external API calls
3. THE Recording_Backend SHALL not require internet connectivity during recording
4. THE Recording_Backend SHALL store all data on the local file system
5. THE Frontend_UI SHALL communicate only with the local Recording_Backend
