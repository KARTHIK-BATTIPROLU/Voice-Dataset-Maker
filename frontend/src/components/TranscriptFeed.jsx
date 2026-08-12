/**
 * Transcript Feed Component
 * 
 * Displays last 10 transcripts with confidence scores
 */

import './TranscriptFeed.css';

const TranscriptFeed = ({ entries }) => {
  const getConfidenceBarWidth = (confidence) => {
    return `${confidence * 100}%`;
  };

  const isLowConfidence = (confidence) => {
    return confidence < 0.4;
  };

  return (
    <div className="transcript-feed">
      <h3 className="feed-title">Live Transcript Feed</h3>
      <div className="feed-container">
        {entries.length === 0 ? (
          <div className="feed-empty">No samples recorded yet</div>
        ) : (
          entries.map((entry, index) => (
            <div
              key={entry.sampleId || index}
              className={`transcript-entry ${isLowConfidence(entry.confidence) ? 'low-confidence' : ''}`}
            >
              <div className="entry-header">
                <span className="entry-id">#{entry.sampleId}</span>
                <span className="entry-confidence">
                  {(entry.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="entry-transcript">{entry.transcript}</div>
              <div className="confidence-bar-container">
                <div
                  className="confidence-bar"
                  style={{ width: getConfidenceBarWidth(entry.confidence) }}
                ></div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default TranscriptFeed;
