/**
 * Stats Display Component
 * 
 * Shows total and session sample counts
 */

import './StatsDisplay.css';

const StatsDisplay = ({ totalSamples, sessionSamples }) => {
  return (
    <div className="stats-display">
      <div className="stat-item">
        <div className="stat-label">This Session</div>
        <div className="stat-value">{sessionSamples}</div>
      </div>
      <div className="stat-divider"></div>
      <div className="stat-item">
        <div className="stat-label">Total Samples</div>
        <div className="stat-value">{totalSamples}</div>
      </div>
    </div>
  );
};

export default StatsDisplay;
