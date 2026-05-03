import React from 'react';
import './Disclaimer.css';

/**
 * Disclaimer - Fixed educational disclaimer shown in footer
 */
function Disclaimer() {
  return (
    <div className="disclaimer">
      <div className="disclaimer-content">
        <span className="disclaimer-icon">⚕️</span>
        <p>
          <strong>DISCLAIMER:</strong> This information is for educational purposes only 
          and is not intended as medical advice. Do not change your medication regimen 
          without consulting your healthcare provider. Always follow your doctor's 
          instructions regarding dosage, timing, and duration of treatment.
        </p>
      </div>
    </div>
  );
}

export default Disclaimer;
