/**
 * Visual Orb Component
 * 
 * Glowing orb indicator with countdown display
 */

import { useEffect, useState } from 'react';
import './VisualOrb.css';

const VisualOrb = ({ isBeeping, isRecording, countdown }) => {
  const [glowClass, setGlowClass] = useState('');

  useEffect(() => {
    if (isBeeping) {
      setGlowClass('beep-pulse');
    } else if (isRecording) {
      setGlowClass('recording-glow');
    } else {
      setGlowClass('');
    }
  }, [isBeeping, isRecording]);

  return (
    <div className="orb-container">
      <div className={`orb ${glowClass}`}>
        {isRecording && countdown !== null && (
          <div className="countdown">{countdown}</div>
        )}
      </div>
    </div>
  );
};

export default VisualOrb;
