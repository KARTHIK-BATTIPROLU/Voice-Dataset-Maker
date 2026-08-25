import React from 'react';
import './PromptCard.css';

export default function PromptCard({ currentPrompt, phraseIndex, totalPhrases, isHoldout }) {
  if (!currentPrompt) {
    return (
      <div className="prompt-card idle">
        <span className="prompt-status-tag">READY</span>
        <p className="prompt-text">Click <strong>Start Enrollment Session</strong> to begin recording.</p>
      </div>
    );
  }

  return (
    <div className={`prompt-card ${isHoldout ? 'holdout' : 'enrollment'}`}>
      <div className="prompt-header">
        <span className={`prompt-badge ${isHoldout ? 'badge-holdout' : 'badge-enrollment'}`}>
          {isHoldout ? '🔒 HOLDOUT TEST CLIP (NOT AVERAGED)' : '🎙️ ENROLLMENT CLIP'}
        </span>
        <span className="prompt-counter">
          Phrase {phraseIndex} of {totalPhrases}
        </span>
      </div>
      <p className="prompt-text">"{currentPrompt}"</p>
    </div>
  );
}
