# Implementation Plan: ASTA Voice Dataset Collector

## Overview

This implementation plan breaks down the ASTA Voice Dataset Collector into three main stages: Backend Core (recording, transcription, manifest management), Frontend UI (React components with real-time feedback), and Integration & Testing (end-to-end validation, property tests, and startup automation). The system uses Python/FastAPI for the backend and React for the frontend, with WebSocket-based real-time communication.

## Tasks

### Stage 1: Backend Core

- [ ] 1. Set up backend project structure and core data models
  - Create backend/ directory with Python package structure
  - Implement data classes in models.py (SessionState, SampleMetadata, TranscriptionResult, ValidationReport, WSMessage, RecordingState enum)
  - Set up configuration management with config.yaml and default values
  - Create directory structure helper functions (data/, logs/, session directories)
  - _Requirements: 14.1, 14.2, 14.3, 14.5, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

- [ ]* 1.1 Write property tests for data model formatting functions
  - **Property 1: Sample ID Sequential Formatting** - Validates: Requirements 1.4, 1.5, 1.7
  - **Property 2: Session ID Timestamp Formatting** - Validates: Requirements 3.1
  - **Property 6: ISO 8601 Timestamp Formatting** - Validates: Requirements 4.5
  - **Property 17: Session Directory Structure** - Validates: Requirements 1.8, 14.2, 14.3

- [ ] 2. Implement Audio Recorder component
  - [-] 2.1 Create AudioRecorder class in audio_recorder.py
    - Implement initialization with configurable sample rate and duration
    - Implement record_sample() method using SoundDevice library (16kHz, mono, 5 seconds)
    - Implement save_wav() method with 16-bit PCM encoding
    - Implement play_beep() method for audio cues (800Hz, 0.5s duration)
    - Add error handling for microphone access failures
    - _Requirements: 1.1, 1.2, 1.3, 15.2, 15.3, 15.6, 17.1, 17.2, 19.2_

  - [ ]* 2.2 Write integration tests for AudioRecorder
    - Test WAV file format validation (16-bit PCM, 16kHz, mono)
    - Test beep generation and playback
    - Test error handling for microphone unavailability
    - _Requirements: 1.1, 1.2, 1.3_

- [ ] 3. Implement Transcription Engine component
  - [~] 3.1 Create TranscriptionEngine class in transcription_engine.py
    - Load Faster Whisper model (base size) with configurable device (CPU/CUDA)
    - Implement transcribe() method returning TranscriptionResult with text and confidence
    - Implement confidence thresholding logic (< 0.4 → "__unclear__")
    - Implement should_flag_unclear() helper method
    - Add error handling for transcription failures
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 15.4, 15.5, 17.2, 20.1, 20.2_

  - [ ]* 3.2 Write property tests for confidence thresholding
    - **Property 3: Confidence Threshold Classification** - Validates: Requirements 2.5, 11.1
    - _Requirements: 2.5, 11.1_

  - [ ]* 3.3 Write integration tests for Faster Whisper integration
    - Test transcription with sample audio files
    - Test handling of silent audio (should return "__unclear__")
    - Test processing time requirements (< 2 seconds per 5-second sample)
    - _Requirements: 2.1, 2.2, 2.6, 2.7, 18.1_

- [ ] 4. Implement Session Manager component
  - [~] 4.1 Create SessionManager class in session_manager.py
    - Implement start_session() with timestamp-based session ID generation
    - Implement pause_session(), resume_session(), stop_session() with state transitions
    - Implement get_next_sample_id() with zero-padded 4-digit format and persistence
    - Implement save_state() and load_state() for JSON persistence
    - Implement get_current_session_dir() returning Path object
    - Add session statistics tracking (total samples, session samples, duration)
    - _Requirements: 1.4, 1.5, 1.6, 1.7, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_

  - [ ]* 4.2 Write property tests for Session Manager logic
    - **Property 1: Sample ID Sequential Formatting** - Validates: Requirements 1.4, 1.5, 1.7
    - **Property 2: Session ID Timestamp Formatting** - Validates: Requirements 3.1
    - **Property 4: State Persistence Round-Trip** - Validates: Requirements 3.2, 3.3, 3.4, 3.7
    - **Property 11: Counter Increment Invariant** - Validates: Requirements 9.3
    - _Requirements: 1.4, 1.5, 1.7, 3.1, 3.2, 3.3, 3.4, 3.7, 9.3_

- [~] 5. Checkpoint - Backend core components review
  - Ensure all tests pass, verify component interfaces match design specification. Ask the user if questions arise.

- [ ] 6. Implement Manifest Generator component
  - [~] 6.1 Create ManifestGenerator class in manifest_generator.py
    - Implement initialize_manifest() to create manifest.csv with required headers
    - Implement append_sample() with atomic file writing and locking
    - Implement absolute-to-relative path conversion for portability
    - Implement validate_manifest() with comprehensive checks (file existence, uniqueness, schema, consistency)
    - Add ValidationReport generation with detailed error lists
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.7, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 18.2_

  - [ ]* 6.2 Write property tests for Manifest Generator logic
    - **Property 5: Relative Path Conversion** - Validates: Requirements 4.4
    - **Property 6: ISO 8601 Timestamp Formatting** - Validates: Requirements 4.5
    - **Property 7: Manifest CSV Schema Validation** - Validates: Requirements 4.2, 13.3
    - **Property 8: Sample ID Uniqueness Validation** - Validates: Requirements 13.2
    - **Property 9: Sample Rate Consistency Validation** - Validates: Requirements 13.5
    - **Property 18: Validation Report Completeness** - Validates: Requirements 13.6, 13.7
    - _Requirements: 4.2, 4.4, 4.5, 13.2, 13.3, 13.5, 13.6, 13.7_

  - [ ]* 6.3 Write unit tests for manifest operations
    - Test manifest creation and header initialization
    - Test atomic append operations
    - Test file locking behavior
    - Test validation with various error conditions
    - _Requirements: 4.1, 4.2, 4.3, 4.7, 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ] 7. Implement quality safeguards module
  - [~] 7.1 Create quality detection functions in quality_safeguards.py
    - Implement low confidence detection and logging
    - Implement duplicate transcript detection (5 consecutive threshold)
    - Implement quality warnings file writer (logs/quality_warnings.log)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 15.7_

  - [ ]* 7.2 Write property tests for quality detection logic
    - **Property 10: Duplicate Transcript Detection** - Validates: Requirements 11.2
    - _Requirements: 11.2_

- [ ] 8. Implement WebSocket Server component
  - [~] 8.1 Create WebSocketManager class in websocket_manager.py
    - Implement connection management (connect, disconnect, active connections list)
    - Implement broadcast() method for sending WSMessage to all clients
    - Implement message serialization for different event types (sample_recorded, transcription_complete, state_change, stats_update, quality_warning, error)
    - Add connection state tracking and reconnection support
    - Ensure latency target of <500ms for event broadcasting
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 17.4, 18.3_

  - [ ]* 8.2 Write integration tests for WebSocket communication
    - Test connection lifecycle (connect, disconnect, reconnect)
    - Test message broadcasting to multiple clients
    - Test message serialization for all event types
    - Test latency requirements (<500ms)
    - _Requirements: 6.1, 6.6, 6.7, 18.3_

- [ ] 9. Implement Recording Loop Controller
  - [~] 9.1 Create RecordingLoopController class in recording_loop.py
    - Wire together AudioRecorder, TranscriptionEngine, SessionManager, ManifestGenerator, WebSocketManager
    - Implement start_loop() with asyncio task management
    - Implement execute_cycle() with full sequence: beep → wait → record → save → transcribe → update manifest → broadcast
    - Implement pause_loop() and stop_loop() with graceful cycle completion
    - Add error handling for each step (audio errors, transcription errors, manifest errors)
    - Implement quality checks integration (low confidence warnings, duplicate detection)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 11.1, 11.2, 11.4, 17.1, 17.2, 17.5_

  - [ ]* 9.2 Write integration tests for recording loop
    - Test complete cycle execution
    - Test pause/resume during active recording
    - Test stop during active recording
    - Test error recovery scenarios
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 17.1, 17.2_

- [ ] 10. Implement REST API endpoints with FastAPI
  - [~] 10.1 Create FastAPI application in main.py with all session control endpoints
    - Implement POST /api/session/start endpoint
    - Implement POST /api/session/pause endpoint
    - Implement POST /api/session/resume endpoint
    - Implement POST /api/session/stop endpoint
    - Implement GET /api/session/status endpoint
    - Implement GET /api/manifest/validate endpoint
    - Implement GET /api/stats endpoint
    - Add CORS middleware for frontend communication
    - Add error handling and JSON response formatting
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9, 17.9_

  - [ ]* 10.2 Write API endpoint tests
    - Test all session control endpoints with various states
    - Test status and stats endpoints
    - Test manifest validation endpoint
    - Test error responses and status codes
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9_

- [ ] 11. Implement WebSocket endpoint in FastAPI
  - [~] 11.1 Add WebSocket endpoint /ws to main.py
    - Accept WebSocket connections and register with WebSocketManager
    - Handle disconnections gracefully
    - Integrate with RecordingLoopController for event broadcasting
    - _Requirements: 6.1, 6.6, 17.4_

- [~] 12. Checkpoint - Backend Stage 1 complete
  - Ensure all backend tests pass, verify API endpoints are functional, test WebSocket connectivity. Ask the user if questions arise.

### Stage 2: Frontend UI

- [ ] 13. Set up frontend project structure with React
  - Create frontend/ directory with React app structure using Create React App or Vite
  - Set up project dependencies (React 18, WebSocket API)
  - Create component directory structure (components/, hooks/, styles/)
  - Configure development proxy to backend (localhost:8000)
  - _Requirements: 19.4_

- [ ] 14. Implement WebSocket custom hook
  - [~] 14.1 Create useWebSocket hook in hooks/useWebSocket.js
    - Implement WebSocket connection management with auto-reconnect
    - Implement connection state tracking (isConnected)
    - Implement message sending and receiving with event handlers
    - Implement reconnection logic (every 2 seconds on disconnect)
    - Add message parsing for different event types
    - _Requirements: 6.1, 6.6, 17.4_

  - [ ]* 14.2 Write unit tests for useWebSocket hook
    - Test connection lifecycle
    - Test reconnection logic
    - Test message handling
    - _Requirements: 6.1, 6.6_

- [ ] 15. Implement ControlPanel component
  - [~] 15.1 Create ControlPanel component in components/ControlPanel.jsx
    - Implement Start button with API call to POST /api/session/start
    - Implement Pause button with API call to POST /api/session/pause
    - Implement Resume button with API call to POST /api/session/resume
    - Implement Stop button with API call to POST /api/session/stop
    - Implement button state management based on recording state
    - Apply dark theme styling with electric blue (#4F8EF7) accent color
    - Add hover and click visual feedback
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [ ]* 15.2 Write property tests for button state logic
    - **Property 16: Button State Consistency** - Validates: Requirements 7.5, 7.6
    - _Requirements: 7.5, 7.6_

  - [ ]* 15.3 Write unit tests for ControlPanel component
    - Test button rendering in different states
    - Test API call triggering on button clicks
    - Test error handling for failed API calls
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ] 16. Implement VisualOrb component
  - [~] 16.1 Create VisualOrb component in components/VisualOrb.jsx
    - Implement orb container with CSS styling
    - Implement glow animation using CSS keyframes (electric blue pulse)
    - Implement countdown display (5, 4, 3, 2, 1) centered in orb
    - Implement state-based animations (beeping, recording, idle)
    - Add smooth transitions between states
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 16.2 Write property tests for countdown logic
    - **Property 19: Countdown Display Mapping** - Validates: Requirements 8.3
    - _Requirements: 8.3_

  - [ ]* 16.3 Write unit tests for VisualOrb component
    - Test orb rendering in different states
    - Test countdown display
    - Test animation triggers
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 17. Implement StatsDisplay component
  - [~] 17.1 Create StatsDisplay component in components/StatsDisplay.jsx
    - Implement total samples counter display
    - Implement session samples counter display
    - Implement WebSocket listener for stats_update events
    - Add auto-increment on sample_recorded events
    - Style counters prominently with dark theme
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 17.2 Write property tests for counter logic
    - **Property 11: Counter Increment Invariant** - Validates: Requirements 9.3
    - _Requirements: 9.3_

  - [ ]* 17.3 Write unit tests for StatsDisplay component
    - Test counter rendering
    - Test counter updates via WebSocket events
    - Test increment behavior
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 18. Implement TranscriptFeed component
  - [~] 18.1 Create TranscriptFeed component in components/TranscriptFeed.jsx
    - Implement transcript entry list display (last 10 entries)
    - Implement TranscriptEntry sub-component with sample ID, text, and confidence percentage
    - Implement confidence percentage conversion (0.0-1.0 → 0-100%)
    - Implement low confidence highlighting (< 40% with warning color)
    - Implement auto-scroll to most recent entry
    - Implement WebSocket listener for transcription_complete events
    - Style feed with dark theme and scrollable container
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [ ]* 18.2 Write property tests for transcript feed logic
    - **Property 12: Transcript Feed Window Management** - Validates: Requirements 10.1
    - **Property 13: Transcript Entry Completeness** - Validates: Requirements 10.2, 10.3, 10.4
    - **Property 14: Confidence Score Percentage Conversion** - Validates: Requirements 10.4
    - **Property 15: Low Confidence Highlighting Threshold** - Validates: Requirements 10.5
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 18.3 Write unit tests for TranscriptFeed component
    - Test entry rendering
    - Test last 10 entries limit
    - Test auto-scroll behavior
    - Test low confidence highlighting
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [ ] 19. Implement Notification component for quality warnings
  - [~] 19.1 Create Notification component in components/Notification.jsx
    - Implement notification display for low confidence warnings
    - Implement notification display for duplicate detection warnings
    - Implement WebSocket listener for quality_warning events
    - Add auto-dismiss after 5 seconds
    - Style notifications with appropriate warning colors
    - _Requirements: 11.5, 11.6_

  - [ ]* 19.2 Write unit tests for Notification component
    - Test notification rendering for different warning types
    - Test auto-dismiss behavior
    - _Requirements: 11.5, 11.6_

- [ ] 20. Implement App component and wire all components together
  - [~] 20.1 Create App component in App.jsx
    - Set up WebSocketProvider context wrapping all components
    - Import and render ControlPanel, VisualOrb, StatsDisplay, TranscriptFeed, Notification
    - Implement recording state management
    - Implement WebSocket event routing to appropriate components
    - Add global error boundary
    - Apply dark theme global styles with electric blue accent
    - _Requirements: 7.7, 17.6, 19.4_

  - [ ]* 20.2 Write integration tests for App component
    - Test component integration
    - Test WebSocket event flow
    - Test state management across components
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 21. Create CSS styling for dark theme
  - [~] 21.1 Create App.css in styles/
    - Implement dark theme color scheme (dark background, light text, electric blue #4F8EF7 accents)
    - Style ControlPanel buttons with hover and active states
    - Style VisualOrb with glow animations and countdown
    - Style StatsDisplay with prominent counter display
    - Style TranscriptFeed with scrollable container and entry cards
    - Style Notification with warning colors
    - Ensure responsive layout
    - _Requirements: 7.7, 7.8, 8.1, 8.2, 8.6, 9.5, 10.5_

- [~] 22. Checkpoint - Frontend Stage 2 complete
  - Ensure all frontend tests pass, verify UI renders correctly, test WebSocket integration with backend. Ask the user if questions arise.

### Stage 3: Integration, Testing & Polish

- [ ] 23. End-to-end integration testing
  - [ ]* 23.1 Write end-to-end tests for complete recording workflow
    - Test full cycle: start → beep → record → transcribe → display transcript → update counters
    - Test pause/resume functionality
    - Test stop and session finalization
    - Test manifest file generation and validation
    - Test state persistence across application restart
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 16.1, 16.2, 16.3_

  - [ ]* 23.2 Write end-to-end tests for error scenarios
    - Test microphone access failure handling
    - Test transcription failure handling
    - Test manifest update failure handling
    - Test WebSocket disconnection and reconnection
    - Test disk full scenario
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7_

  - [ ]* 23.3 Write end-to-end tests for quality safeguards
    - Test low confidence sample detection and UI warning
    - Test duplicate detection and UI warning
    - Test quality warnings logging
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [ ] 24. Performance validation
  - [ ]* 24.1 Write performance tests for latency requirements
    - Test transcription latency (< 2 seconds per sample)
    - Test manifest update latency (< 100ms)
    - Test WebSocket broadcast latency (< 500ms)
    - Test continuous recording for 4+ hours without memory leaks
    - Test UI rendering performance (60 FPS during animations)
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6_

- [ ] 25. Cross-platform compatibility testing
  - [ ]* 25.1 Test on Windows, Linux, and macOS
    - Verify microphone detection on each platform
    - Verify file path handling (forward slashes in manifest)
    - Test audio recording and WAV file format
    - Test frontend rendering in Chrome, Firefox, and Edge
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5_

- [ ] 26. Create configuration file with defaults
  - [~] 26.1 Create config.yaml in project root
    - Add audio configuration (sample_rate: 16000, duration: 5.0, channels: 1, beep settings)
    - Add transcription configuration (model_size: base, confidence_threshold: 0.4, device: cpu)
    - Add recording configuration (loop_delay: 1.0)
    - Add paths configuration (data_dir, manifest_file, state_file, logs_dir)
    - Add quality configuration (duplicate_detection_threshold: 5)
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

- [ ] 27. Create startup and deployment scripts
  - [~] 27.1 Create backend startup script (start_backend.sh / start_backend.bat)
    - Set up Python virtual environment activation
    - Install dependencies from requirements.txt
    - Start uvicorn server with appropriate host and port
    - _Requirements: 19.1_

  - [~] 27.2 Create frontend startup script (start_frontend.sh / start_frontend.bat)
    - Install npm dependencies
    - Start React development server
    - _Requirements: 19.4_

  - [~] 27.3 Create combined startup script (start_app.sh / start_app.bat)
    - Start backend in background
    - Start frontend in foreground
    - Add cleanup on exit
    - _Requirements: 19.1, 19.4_

- [ ] 28. Create requirements.txt and package.json
  - [~] 28.1 Create requirements.txt for backend dependencies
    - Add fastapi, uvicorn, sounddevice, faster-whisper, pyyaml, numpy, scipy, pytest, hypothesis
    - Pin versions for stability
    - _Requirements: 20.1, 20.2, 20.3_

  - [~] 28.2 Create package.json for frontend dependencies
    - Add react, react-dom, testing library dependencies
    - Add scripts for start, build, test
    - _Requirements: 19.4_

- [ ] 29. Create comprehensive README.md
  - [~] 29.1 Write README.md with setup and usage instructions
    - Add project overview and features
    - Add system requirements (Python 3.10+, Node.js 16+, microphone)
    - Add installation instructions for backend and frontend
    - Add usage instructions (starting the application, recording workflow)
    - Add configuration guide (config.yaml options)
    - Add troubleshooting section (common errors and solutions)
    - Add manifest format documentation for SpeechBrain compatibility
    - Add examples of training with SpeechBrain ECAPA-TDNN
    - _Requirements: 15.1, 19.1, 19.2, 19.3, 19.4, 20.1, 20.2, 20.3, 20.4, 20.5_

- [ ] 30. Create example configuration and .gitignore
  - [~] 30.1 Create config.yaml.example with documented defaults
    - _Requirements: 15.1, 15.7_

  - [~] 30.2 Create .gitignore
    - Ignore data/ directory, session_state.json, logs/, Python cache, Node modules, build artifacts
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [ ] 31. Final validation and quality checks
  - [~] 31.1 Run complete test suite (backend and frontend)
    - Ensure all property tests pass (100 iterations minimum)
    - Ensure all unit tests pass
    - Ensure all integration tests pass
    - Verify 80%+ code coverage for business logic
    - _Requirements: All_

  - [~] 31.2 Manual testing checklist
    - Test complete recording session (start → collect 20+ samples → stop)
    - Test pause/resume during recording
    - Test application restart with state persistence
    - Test manifest validation endpoint
    - Test quality warnings (low confidence, duplicates)
    - Test error scenarios (microphone disconnect)
    - Test on at least 2 different operating systems
    - _Requirements: All_

- [~] 32. Final checkpoint - Project complete
  - All tests passing, documentation complete, ready for user acceptance testing. Present demo to user and gather feedback.

## Notes

- Tasks marked with `*` are optional test-related sub-tasks that can be skipped for faster MVP delivery
- All tasks reference specific requirements from the requirements document for traceability
- Property tests validate universal correctness properties defined in the design document
- The three-stage structure allows for incremental development and testing: Backend → Frontend → Integration
- Backend Stage 1 focuses on core recording, transcription, and data management functionality
- Frontend Stage 2 focuses on user interface, real-time updates, and visual feedback
- Stage 3 focuses on end-to-end testing, cross-platform validation, and deployment readiness
- Each stage has checkpoint tasks to ensure quality and allow for user feedback
- The design uses Python/FastAPI for backend and React/JavaScript for frontend
- Configuration is managed through config.yaml for easy customization without code changes
- All processing is local with no cloud dependencies (zero-cost operation)
- WebSocket provides real-time communication between backend and frontend
- Manifest format is SpeechBrain-compatible for immediate use in model training

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1", "2.1", "13"]
    },
    {
      "id": 1,
      "tasks": ["2.2", "3.1", "26.1"]
    },
    {
      "id": 2,
      "tasks": ["3.2", "3.3", "4.1"]
    },
    {
      "id": 3,
      "tasks": ["4.2", "6.1", "7.1", "14.1"]
    },
    {
      "id": 4,
      "tasks": ["6.2", "6.3", "7.2", "14.2", "8.1"]
    },
    {
      "id": 5,
      "tasks": ["8.2", "9.1"]
    },
    {
      "id": 6,
      "tasks": ["9.2", "10.1", "11.1"]
    },
    {
      "id": 7,
      "tasks": ["10.2", "15.1"]
    },
    {
      "id": 8,
      "tasks": ["15.2", "15.3", "16.1"]
    },
    {
      "id": 9,
      "tasks": ["16.2", "16.3", "17.1"]
    },
    {
      "id": 10,
      "tasks": ["17.2", "17.3", "18.1"]
    },
    {
      "id": 11,
      "tasks": ["18.2", "18.3", "19.1"]
    },
    {
      "id": 12,
      "tasks": ["19.2", "20.1", "21.1"]
    },
    {
      "id": 13,
      "tasks": ["20.2", "23.1", "23.2", "23.3"]
    },
    {
      "id": 14,
      "tasks": ["24.1", "25.1"]
    },
    {
      "id": 15,
      "tasks": ["27.1", "27.2", "28.1", "28.2"]
    },
    {
      "id": 16,
      "tasks": ["27.3", "29.1", "30.1", "30.2"]
    },
    {
      "id": 17,
      "tasks": ["31.1", "31.2"]
    }
  ]
}
```
