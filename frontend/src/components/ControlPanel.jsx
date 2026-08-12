/**
 * Control Panel Component
 * 
 * Main control buttons for recording session management
 */

import { useState } from 'react';
import './ControlPanel.css';

const ControlPanel = ({ recordingState, onStart, onPause, onResume, onStop }) => {
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

  const isIdle = recordingState === 'idle' || recordingState === 'stopped';
  const isActive = recordingState === 'active';
  const isPaused = recordingState === 'paused';

  return (
    <div className="control-panel">
      <button
        className="control-btn start-btn"
        onClick={handleStart}
        disabled={!isIdle || isLoading}
      >
        START
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
        STOP
      </button>
    </div>
  );
};

export default ControlPanel;
