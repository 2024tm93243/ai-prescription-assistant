import React from 'react';
import './DrugInfoPanel.css';

/**
 * DrugInfoPanel - Shows educational information about a selected drug
 */
function DrugInfoPanel({ drug, drugInfo, isLoading, onClose }) {
  return (
    <div className="drug-info-panel">
      <div className="panel-header">
        <h3>{drug.drug_name}</h3>
        <button className="close-btn" onClick={onClose}>
          ✕
        </button>
      </div>

      {isLoading ? (
        <div className="panel-loading">
          <div className="spinner"></div>
          <p>Loading drug information...</p>
        </div>
      ) : drugInfo ? (
        <div className="panel-content">
          {/* Uses Section */}
          <div className="info-section">
            <h4>
              <span className="section-icon">💊</span>
              General Uses
            </h4>
            <p>{drugInfo.uses}</p>
          </div>

          {/* Side Effects Section */}
          <div className="info-section">
            <h4>
              <span className="section-icon">⚠️</span>
              Common Side Effects
            </h4>
            <ul>
              {drugInfo.side_effects?.map((effect, index) => (
                <li key={index}>{effect}</li>
              ))}
            </ul>
          </div>

          {/* OTC Recommendations Section */}
          {drugInfo.otc_for_side_effects && drugInfo.otc_for_side_effects.length > 0 && (
            <div className="info-section otc-recommendations">
              <h4>
                <span className="section-icon">💊</span>
                OTC Options for Side Effects (Educational Only)
              </h4>
              <div className="otc-disclaimer-strong">
                ⚠️ <strong>IMPORTANT:</strong> Always consult your doctor or pharmacist before taking
                any OTC medication with your prescription drugs!
              </div>
              {drugInfo.otc_for_side_effects.map((otc, index) => (
                <div key={index} className="otc-item">
                  <div className="otc-side-effect">
                    <strong>For {otc.side_effect}:</strong>
                  </div>
                  <ul className="otc-options-list">
                    {otc.otc_options?.map((option, idx) => (
                      <li key={idx}>{option}</li>
                    ))}
                  </ul>
                  {otc.caution && (
                    <div className="otc-caution">
                      <span className="caution-icon">⚠️</span>
                      {otc.caution}
                    </div>
                  )}
                </div>
              ))}
              {drugInfo.otc_disclaimer && (
                <div className="otc-disclaimer-footer">
                  {drugInfo.otc_disclaimer}
                </div>
              )}
            </div>
          )}

          {/* Warnings Section */}
          <div className="info-section warnings">
            <h4>
              <span className="section-icon">🛑</span>
              Safety Warnings
            </h4>
            <ul>
              {drugInfo.warnings?.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          </div>

          {/* Prescription Details */}
          {(drug.dosage || drug.frequency || drug.route) && (
            <div className="info-section prescription-details">
              <h4>
                <span className="section-icon">📋</span>
                Prescription Details
              </h4>
              <div className="details-grid">
                {drug.dosage && (
                  <div className="detail-item">
                    <span className="detail-label">Dosage</span>
                    <span className="detail-value">{drug.dosage}</span>
                  </div>
                )}
                {drug.frequency && (
                  <div className="detail-item">
                    <span className="detail-label">Frequency</span>
                    <span className="detail-value">{drug.frequency}</span>
                  </div>
                )}
                {drug.route && (
                  <div className="detail-item">
                    <span className="detail-label">Route</span>
                    <span className="detail-value">{drug.route}</span>
                  </div>
                )}
                {drug.duration && (
                  <div className="detail-item">
                    <span className="detail-label">Duration</span>
                    <span className="detail-value">{drug.duration}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Disclaimer */}
          {drugInfo.disclaimer && (
            <div className="info-disclaimer">
              <p>{drugInfo.disclaimer}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="panel-error">
          <p>Unable to load drug information.</p>
        </div>
      )}
    </div>
  );
}

export default DrugInfoPanel;
