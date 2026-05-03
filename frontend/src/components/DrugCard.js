import React, { useState } from 'react';
import ConfidenceIndicator from './ConfidenceIndicator';
import './DrugCard.css';

/**
 * DrugCard - Displays a single drug with confidence indicator
 */
function DrugCard({ drug, isSelected, onSelect, onConfirm }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(drug.drug_name);

  const handleConfirm = () => {
    if (editedName.trim()) {
      onConfirm(drug.drug_id, editedName.trim());
      setIsEditing(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleConfirm();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
      setEditedName(drug.drug_name);
    }
  };

  return (
    <div
      className={`drug-card ${isSelected ? 'selected' : ''} ${
        drug.requires_confirmation ? 'needs-confirmation' : ''
      }`}
      onClick={() => !isEditing && onSelect()}
    >
      <div className="drug-card-header">
        <ConfidenceIndicator level={drug.confidence_level} />
        <span className="confidence-percent">
          {Math.round(drug.confidence * 100)}%
        </span>
      </div>

      <div className="drug-card-body">
        {isEditing ? (
          <div className="edit-mode" onClick={(e) => e.stopPropagation()}>
            <input
              type="text"
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
              className="edit-input"
            />
            <div className="edit-actions">
              <button className="btn-confirm" onClick={handleConfirm}>
                ✓
              </button>
              <button
                className="btn-cancel"
                onClick={() => {
                  setIsEditing(false);
                  setEditedName(drug.drug_name);
                }}
              >
                ✕
              </button>
            </div>
          </div>
        ) : (
          <>
            <h4 className="drug-name">{drug.drug_name}</h4>
            {drug.dosage && <p className="drug-detail">💊 {drug.dosage}</p>}
            {drug.frequency && <p className="drug-detail">⏰ {drug.frequency}</p>}
          </>
        )}
      </div>

      {drug.requires_confirmation && !isEditing && (
        <button
          className="confirm-btn"
          onClick={(e) => {
            e.stopPropagation();
            setIsEditing(true);
          }}
        >
          Confirm Name
        </button>
      )}

      {isSelected && !isEditing && (
        <div className="selected-indicator">
          <span>→ View Info</span>
        </div>
      )}
    </div>
  );
}

export default DrugCard;
