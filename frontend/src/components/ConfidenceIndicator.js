import React from 'react';
import './ConfidenceIndicator.css';

/**
 * ConfidenceIndicator - Visual badge showing confidence level
 */
function ConfidenceIndicator({ level, showLabel = false }) {
  const getConfig = () => {
    switch (level) {
      case 'HIGH':
        return {
          color: '#10b981',
          bgColor: '#d1fae5',
          label: 'High',
          icon: '✓',
        };
      case 'MEDIUM':
        return {
          color: '#f59e0b',
          bgColor: '#fef3c7',
          label: 'Medium',
          icon: '~',
        };
      case 'LOW':
        return {
          color: '#ef4444',
          bgColor: '#fee2e2',
          label: 'Low',
          icon: '!',
        };
      default:
        return {
          color: '#6b7280',
          bgColor: '#f3f4f6',
          label: 'Unknown',
          icon: '?',
        };
    }
  };

  const config = getConfig();

  return (
    <div
      className="confidence-indicator"
      style={{
        backgroundColor: config.bgColor,
        color: config.color,
      }}
    >
      <span className="confidence-icon">{config.icon}</span>
      {showLabel && <span className="confidence-label">{config.label}</span>}
    </div>
  );
}

export default ConfidenceIndicator;
