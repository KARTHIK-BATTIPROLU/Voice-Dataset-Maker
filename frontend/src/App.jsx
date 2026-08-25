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
import PromptCard from './components/PromptCard';
import './App.css';

const API_BASE = '/api';
const getWsUrl = () => {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.port === '3000'
    ? `${window.location.hostname}:9090`
    : window.location.host;
  return `${protocol}//${host}/ws`;
};
const WS_URL = getWsUrl();

function App() {
  const [recordingState, setRecordingState] = useState('idle');
  const [totalSamples, setTotalSamples] = useState(0);
  const [sessionSamples, setSessionSamples] = useState(0);
  const [transcriptEntries, setTranscriptEntries] = useState([]);
  const [isBeeping, setIsBeeping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const [notification, setNotification] = useState(null);

  // Enrollment specific states
  const [roomTag, setRoomTag] = useState('bedroom-laptop-mic');
  const [currentPrompt, setCurrentPrompt] = useState('');
  const [phraseIndex, setPhraseIndex] = useState(1);
  const [totalPhrases, setTotalPhrases] = useState(22);
  const [isHoldout, setIsHoldout] = useState(false);
  const [enrollmentResult, setEnrollmentResult] = useState(null);

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
      case 'PROMPT_PHRASE':
        setCurrentPrompt(payload.phrase);
        setPhraseIndex(payload.phrase_index);
        setTotalPhrases(payload.total_phrases);
        setIsHoldout(payload.is_holdout);
        break;

      case 'BEEP':
        setIsBeeping(true);
        setTimeout(() => setIsBeeping(false), 500);
        break;

      case 'RECORDING_START':
        setIsRecording(true);
        setCountdown(5);
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
        if (payload.warning_type === 'rejected_quality') {
          showNotification(
            `QUALITY REJECT: Sample #${payload.sample_id} - ${payload.reason}. Re-prompting phrase...`,
            'error'
          );
        } else if (payload.warning_type === 'low_confidence') {
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

      case 'ENROLLMENT_COMPLETE':
        setEnrollmentResult(payload);
        showNotification(
          `Speaker Enrollment Complete! Voiceprint saved to ${payload.voiceprint_path}`,
          'info'
        );
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
    setEnrollmentResult(null);
    try {
      const response = await fetch(`${API_BASE}/session/start?room_tag=${encodeURIComponent(roomTag)}`, {
        method: 'POST'
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to start session');
      }

      setRecordingState('active');
      setSessionSamples(0);
      showNotification(`Enrollment session started: ${data.session_id} [Room: ${roomTag}]`, 'info');
    } catch (error) {
      showNotification(error.message, 'error');
    }
  };

  const handleReset = async () => {
    try {
      const response = await fetch(`${API_BASE}/session/reset`, {
        method: 'POST'
      });
      const data = await response.json();
      setRecordingState('idle');
      setEnrollmentResult(null);
      setCurrentPrompt('');
      showNotification(data.message, 'info');
    } catch (error) {
      showNotification(`Failed to reset: ${error.message}`, 'error');
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
      showNotification('Finalizing enrollment and generating ECAPA-TDNN voiceprint...', 'info');
      const response = await fetch(`${API_BASE}/session/stop`, {
        method: 'POST'
      });
      const data = await response.json();
      setRecordingState('stopped');
      if (data.enrollment_result) {
        setEnrollmentResult(data.enrollment_result);
      }
      showNotification(
        `Session finalized! ${data.total_samples} total samples recorded.`,
        'info'
      );
    } catch (error) {
      showNotification(`Failed to stop: ${error.message}`, 'error');
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>ASTA Voice Enrollment System</h1>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '● Connected' : '○ Disconnected'}
        </div>
      </header>

      <main className="app-main">
        <PromptCard 
          currentPrompt={currentPrompt}
          phraseIndex={phraseIndex}
          totalPhrases={totalPhrases}
          isHoldout={isHoldout}
        />

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
          roomTag={roomTag}
          setRoomTag={setRoomTag}
          onStart={handleStart}
          onPause={handlePause}
          onResume={handleResume}
          onStop={handleStop}
          onReset={handleReset}
        />

        {enrollmentResult && (
          <div className="enrollment-result-card">
            <h3>🎉 Speaker Enrollment Complete</h3>
            <p><strong>Master Voiceprint:</strong> <code>{enrollmentResult.voiceprint_path}</code></p>
            <p><strong>Clips Kept:</strong> {enrollmentResult.kept?.length} / {enrollmentResult.total_enrollment_clips}</p>
            {enrollmentResult.dropped?.length > 0 && (
              <p className="text-warning"><strong>Dropped Inconsistent Clips:</strong> {enrollmentResult.dropped.join(', ')}</p>
            )}

            <h4>Holdout Verification Results (Honest Test)</h4>
            <ul className="holdout-list">
              {enrollmentResult.holdout_results?.map((res, idx) => (
                <li key={idx} className={res.passed ? 'holdout-pass' : 'holdout-fail'}>
                  Sample #{res.sample_id}: Similarity = <strong>{res.similarity}</strong> ({res.passed ? '✅ PASS (>= 0.65)' : '❌ BELOW THRESHOLD (< 0.65)'})
                </li>
              ))}
            </ul>
          </div>
        )}

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
