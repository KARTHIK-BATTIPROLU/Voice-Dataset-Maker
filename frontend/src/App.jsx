/**
 * ASTA Voice Dataset Collector - Main App
 * 
 * Real-time voice dataset collection with local transcription
 */

import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import ControlPanel from './components/ControlPanel';
import VisualOrb from './components/VisualOrb';
import StatsDisplay from './components/StatsDisplay';
import TranscriptFeed from './components/TranscriptFeed';
import Notification from './components/Notification';
import './App.css';

const API_BASE = '/api';
const WS_URL = `ws://${window.location.hostname}:8000/ws`;

function App() {
  const [recordingState, setRecordingState] = useState('idle');
  const [totalSamples, setTotalSamples] = useState(0);
  const [sessionSamples, setSessionSamples] = useState(0);
  const [transcriptEntries, setTranscriptEntries] = useState([]);
  const [isBeeping, setIsBeeping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const [notification, setNotification] = useState(null);

  const { isConnected, lastMessage } = useWebSocket(WS_URL);

  // Fetch initial status
  useEffect(() => {
    fetchSessionStatus();
  }, []);

  const fetchSessionStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/session/status`);
      const data = await response.json();
      setRecordingState(data.state);
      setTotalSamples(data.total_samples);
    } catch (error) {
      console.error('Failed to fetch session status:', error);
    }
  };

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    const { event_type, payload } = lastMessage;

    switch (event_type) {
      case 'BEEP':
        setIsBeeping(true);
        setTimeout(() => setIsBeeping(false), 500);
        break;

      case 'RECORDING_START':
        setIsRecording(true);
        setCountdown(5);
        // Countdown timer
        const interval = setInterval(() => {
          setCountdown((prev) => {
            if (prev <= 1) {
              clearInterval(interval);
              setIsRecording(false);
              return null;
            }
            return prev - 1;
          });
        }, 1000);
        break;

      case 'transcription_complete':
        const newEntry = {
          sampleId: payload.sample_id,
          transcript: payload.transcript,
          confidence: payload.confidence
        };
        setTranscriptEntries((prev) => [newEntry, ...prev].slice(0, 10));
        break;

      case 'stats_update':
        setTotalSamples(payload.total_samples);
        setSessionSamples(payload.session_samples);
        break;

      case 'state_change':
        setRecordingState(payload.state);
        break;

      case 'quality_warning':
        if (payload.warning_type === 'low_confidence') {
          showNotification(
            `Low confidence sample #${payload.sample_id} (${(payload.confidence * 100).toFixed(0)}%)`,
            'warning'
          );
        } else if (payload.warning_type === 'duplicate_detection') {
          showNotification(
            `Duplicate detected: "${payload.transcript}" repeated ${payload.occurrence_count} times`,
            'warning'
          );
        }
        break;

      case 'error':
        showNotification(payload.error_message, 'error');
        break;

      default:
        break;
    }
  }, [lastMessage]);

  const showNotification = (message, type = 'info') => {
    setNotification({ message, type });
  };

  const hideNotification = () => {
    setNotification(null);
  };

  const handleStart = async () => {
    try {
      const response = await fetch(`${API_BASE}/session/start`, {
        method: 'POST'
      });
      const data = await response.json();
      setRecordingState('active');
      setSessionSamples(0);
      showNotification(`Recording session started: ${data.session_id}`, 'info');
    } catch (error) {
      showNotification(`Failed to start session: ${error.message}`, 'error');
    }
  };

  const handlePause = async () => {
    try {
      await fetch(`${API_BASE}/session/pause`, {
        method: 'POST'
      });
      setRecordingState('paused');
      showNotification('Recording paused', 'info');
    } catch (error) {
      showNotification(`Failed to pause: ${error.message}`, 'error');
    }
  };

  const handleResume = async () => {
    try {
      await fetch(`${API_BASE}/session/resume`, {
        method: 'POST'
      });
      setRecordingState('active');
      showNotification('Recording resumed', 'info');
    } catch (error) {
      showNotification(`Failed to resume: ${error.message}`, 'error');
    }
  };

  const handleStop = async () => {
    try {
      const response = await fetch(`${API_BASE}/session/stop`, {
        method: 'POST'
      });
      const data = await response.json();
      setRecordingState('stopped');
      showNotification(
        `Session stopped: ${data.total_samples} samples recorded`,
        'info'
      );
    } catch (error) {
      showNotification(`Failed to stop: ${error.message}`, 'error');
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>ASTA Voice Dataset Collector</h1>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '● Connected' : '○ Disconnected'}
        </div>
      </header>

      <main className="app-main">
        <VisualOrb 
          isBeeping={isBeeping}
          isRecording={isRecording}
          countdown={countdown}
        />

        <StatsDisplay 
          totalSamples={totalSamples}
          sessionSamples={sessionSamples}
        />

        <ControlPanel
          recordingState={recordingState}
          onStart={handleStart}
          onPause={handlePause}
          onResume={handleResume}
          onStop={handleStop}
        />

        <TranscriptFeed entries={transcriptEntries} />
      </main>

      {notification && (
        <Notification
          message={notification.message}
          type={notification.type}
          onDismiss={hideNotification}
        />
      )}
    </div>
  );
}

export default App;
