/**
 * Control Panel Component
 * 
 * Main control buttons for recording session management
 */

import { useState } from 'react';
import './ControlPanel.css';

const ControlPanel = ({ recordingState, roomTag, setRoomTag, onStart, onPause, onResume, onStop, onReset }) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleStart = async () => {
    setIsLoading(true);
    try {
      await onStart();
    } finally {
      setIsLoading(false);
    }
  };

  const handlePause = async () => {
    setIsLoading(true);
    try {
      await onPause();
    } finally {
      setIsLoading(false);
    }
  };

  const handleResume = async () => {
    setIsLoading(true);
    try {
      await onResume();
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    setIsLoading(true);
    try {
      await onStop();
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = async () => {
    if (window.confirm("Are you sure you want to reset the enrollment session? This clears session lock.")) {
      setIsLoading(true);
      try {
        await onReset();
      } finally {
        setIsLoading(false);
      }
    }
  };

  const isIdle = recordingState === 'idle' || recordingState === 'stopped';
  const isActive = recordingState === 'active';
  const isPaused = recordingState === 'paused';

  return (
    <div className="control-panel-container">
      {isIdle && (
        <div className="room-tag-input-group">
          <label htmlFor="roomTagInput">Room Tag / Provenance:</label>
          <input
            id="roomTagInput"
            type="text"
            placeholder="e.g. bedroom-laptop-mic"
            value={roomTag}
            onChange={(e) => setRoomTag(e.target.value)}
            disabled={isLoading}
            className="room-tag-input"
          />
        </div>
      )}

      <div className="control-panel">
        <button
          className="control-btn start-btn"
          onClick={handleStart}
          disabled={!isIdle || isLoading}
        >
          START ENROLLMENT
        </button>

        <button
          className="control-btn pause-btn"
          onClick={handlePause}
          disabled={!isActive || isLoading}
        >
          PAUSE
        </button>

        <button
          className="control-btn resume-btn"
          onClick={handleResume}
          disabled={!isPaused || isLoading}
        >
          RESUME
        </button>

        <button
          className="control-btn stop-btn"
          onClick={handleStop}
          disabled={(!isActive && !isPaused) || isLoading}
        >
          FINALIZE & ENROLL
        </button>

        <button
          className="control-btn reset-btn"
          onClick={handleReset}
          disabled={isLoading}
          title="Reset enrollment session state"
        >
          RESET
        </button>
      </div>
    </div>
  );
};

export default ControlPanel;
