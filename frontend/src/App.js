import React, { useState, useCallback } from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';
import PrescriptionUpload from './components/PrescriptionUpload';
import DrugCard from './components/DrugCard';
import DrugInfoPanel from './components/DrugInfoPanel';
import Disclaimer from './components/Disclaimer';
import ConfidenceIndicator from './components/ConfidenceIndicator';
import { uploadPrescription, getDrugInfo, confirmDrug } from './services/api';

function App() {
  // State management
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'Hello! I can help you understand your medications. You can either upload a prescription image OR type a drug name directly to learn about it.',
    },
  ]);
  const [prescriptionData, setPrescriptionData] = useState(null);
  const [selectedDrug, setSelectedDrug] = useState(null);
  const [drugInfo, setDrugInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingDrugInfo, setIsLoadingDrugInfo] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [pendingDrug, setPendingDrug] = useState(null); // Drug waiting for confirmation
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);

  // Add a new message to the chat
  const addMessage = useCallback((type, content, data = null) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        type,
        content,
        data,
      },
    ]);
  }, []);

  // Fetch drug info and display
  const fetchAndDisplayDrugInfo = useCallback(async (drugName, drug = null) => {
    setIsLoadingDrugInfo(true);
    addMessage('bot', `Fetching information for "${drugName}"...`);

    try {
      const info = await getDrugInfo(drugName);
      
      const drugObj = drug || {
        drug_id: `query-${Date.now()}`,
        drug_name: drugName,
        confidence: 1.0,
        confidence_level: 'HIGH',
      };
      
      setSelectedDrug(drugObj);
      setDrugInfo(info);
      
      addMessage(
        'bot',
        `Here's the information about ${drugName}. Check the panel below for details.`,
        { type: 'drug_info' }
      );
    } catch (err) {
      console.error('Drug info error:', err);
      addMessage(
        'bot',
        `Sorry, I couldn't find information for "${drugName}". Please check the spelling or try another drug name.`,
        { type: 'error' }
      );
    } finally {
      setIsLoadingDrugInfo(false);
    }
  }, [addMessage]);

  // Handle direct drug name query from chat
  const handleChatSubmit = useCallback(async (inputText) => {
    const text = inputText.trim();
    if (!text) return;

    setChatInput('');
    addMessage('user', text);

    // Check if we're awaiting confirmation for a low-confidence drug
    if (awaitingConfirmation && pendingDrug) {
      const confirmedName = text;
      setAwaitingConfirmation(false);
      
      // Update the pending drug with confirmed name
      const updatedDrug = {
        ...pendingDrug,
        drug_name: confirmedName,
        confidence_level: 'HIGH',
        requires_confirmation: false,
      };
      
      setPendingDrug(null);
      
      addMessage('bot', `Drug name confirmed as "${confirmedName}".`);
      
      // Now fetch drug info
      await fetchAndDisplayDrugInfo(confirmedName, updatedDrug);
      return;
    }

    // Normal drug query
    await fetchAndDisplayDrugInfo(text);
  }, [addMessage, awaitingConfirmation, pendingDrug, fetchAndDisplayDrugInfo]);

  // Get confidence label
  const getConfidenceLabel = (level, score) => {
    const percent = Math.round(score * 100);
    switch (level) {
      case 'HIGH':
        return `HIGH (${percent}%)`;
      case 'MEDIUM':
        return `MEDIUM (${percent}%)`;
      case 'LOW':
        return `LOW (${percent}%)`;
      default:
        return `${percent}%`;
    }
  };

  // Handle prescription upload
  const handleUpload = useCallback(async (file) => {
    setIsLoading(true);
    setPrescriptionData(null);
    setSelectedDrug(null);
    setDrugInfo(null);
    setPendingDrug(null);
    setAwaitingConfirmation(false);

    addMessage('user', `Uploaded: ${file.name}`);
    addMessage('bot', 'Processing your prescription... This may take a moment.');

    try {
      const result = await uploadPrescription(file);
      setPrescriptionData(result);

      if (result.medications && result.medications.length > 0) {
        // Show each drug with its confidence score
        for (const drug of result.medications) {
          const confidenceLabel = getConfidenceLabel(drug.confidence_level, drug.confidence);
          const dosageInfo = drug.dosage ? ` | Dosage: ${drug.dosage}` : '';
          const frequencyInfo = drug.frequency ? ` | Frequency: ${drug.frequency}` : '';
          
          addMessage(
            'bot',
            `📋 Found: "${drug.drug_name}"${dosageInfo}${frequencyInfo}\n🎯 Confidence: ${confidenceLabel}`,
            { type: 'drug_found', drug }
          );

          if (drug.confidence_level === 'LOW' || drug.requires_confirmation) {
            // Low confidence - ask for confirmation
            addMessage(
              'bot',
              `⚠️ The confidence score is LOW for "${drug.drug_name}". Please type the correct drug name to confirm, or type the same name if it looks correct:`,
              { type: 'confirmation_needed' }
            );
            setPendingDrug(drug);
            setAwaitingConfirmation(true);
            setIsLoading(false);
            return; // Wait for user confirmation
          } else {
            // High/Medium confidence - automatically fetch drug info
            setIsLoading(false);
            await fetchAndDisplayDrugInfo(drug.drug_name, drug);
          }
        }
      } else {
        addMessage(
          'bot',
          'I couldn\'t identify any medications in this image. Please try uploading a clearer image.',
          { type: 'error' }
        );
      }
    } catch (err) {
      console.error('Upload error:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to process prescription';
      addMessage('bot', `Error: ${errorMessage}`, { type: 'error' });
    } finally {
      setIsLoading(false);
    }
  }, [addMessage, fetchAndDisplayDrugInfo]);

  // Handle drug selection
  const handleDrugSelect = useCallback(async (drug) => {
    setSelectedDrug(drug);
    setDrugInfo(null);
    setIsLoadingDrugInfo(true);

    try {
      const info = await getDrugInfo(drug.drug_name);
      setDrugInfo(info);
    } catch (err) {
      console.error('Drug info error:', err);
      setDrugInfo({
        drug_name: drug.drug_name,
        uses: 'Unable to retrieve information. Please consult your healthcare provider.',
        side_effects: ['Information not available'],
        warnings: ['Always consult your healthcare provider'],
        disclaimer: 'This information is for educational purposes only.',
      });
    } finally {
      setIsLoadingDrugInfo(false);
    }
  }, []);

  // Handle drug name confirmation
  const handleConfirmDrug = useCallback(async (drugId, confirmedName) => {
    if (!prescriptionData) return;

    try {
      await confirmDrug(prescriptionData.prescription_id, drugId, confirmedName);
      
      // Update local state
      setPrescriptionData((prev) => ({
        ...prev,
        medications: prev.medications.map((med) =>
          med.drug_id === drugId
            ? { ...med, drug_name: confirmedName, confidence_level: 'HIGH', requires_confirmation: false }
            : med
        ),
      }));

      addMessage('bot', `Drug name confirmed: ${confirmedName}`);
    } catch (err) {
      console.error('Confirm error:', err);
      addMessage('bot', 'Failed to confirm drug name. Please try again.', { type: 'error' });
    }
  }, [prescriptionData, addMessage]);

  // Close drug info panel
  const handleCloseDrugInfo = useCallback(() => {
    setSelectedDrug(null);
    setDrugInfo(null);
  }, []);

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <h1>Prescription Reader</h1>
          <p>Upload a prescription or type a drug name to learn more</p>
        </div>
      </header>

      {/* Disclaimer Banner */}
      {process.env.REACT_APP_ENV === 'production' && (
        <div className="disclaimer-banner">
          <span className="disclaimer-icon">⚠️</span>
          <strong>EDUCATIONAL PROTOTYPE ONLY - NOT FOR CLINICAL USE</strong>
          <span className="disclaimer-text">
            This application does not provide medical advice. Always consult your healthcare provider.
          </span>
        </div>
      )}

      {/* Main content */}
      <main className="app-main">
        <div className="main-container">
          {/* Chat section */}
          <div className="chat-section">
            <ChatInterface 
              messages={messages} 
              chatInput={chatInput}
              setChatInput={setChatInput}
              onSubmit={handleChatSubmit}
              isLoading={isLoadingDrugInfo || isLoading}
              awaitingConfirmation={awaitingConfirmation}
              pendingDrugName={pendingDrug?.drug_name}
            />

            {/* Upload area */}
            <div className="upload-section">
              <PrescriptionUpload onUpload={handleUpload} isLoading={isLoading} />
            </div>

            {/* Medications grid */}
            {prescriptionData && prescriptionData.medications && (
              <div className="medications-section">
                <h3>Extracted Medications</h3>
                <div className="confidence-legend">
                  <ConfidenceIndicator level="HIGH" showLabel />
                  <ConfidenceIndicator level="MEDIUM" showLabel />
                  <ConfidenceIndicator level="LOW" showLabel />
                </div>
                <div className="medications-grid">
                  {prescriptionData.medications.map((drug) => (
                    <DrugCard
                      key={drug.drug_id}
                      drug={drug}
                      isSelected={selectedDrug?.drug_id === drug.drug_id}
                      onSelect={() => handleDrugSelect(drug)}
                      onConfirm={handleConfirmDrug}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Drug info panel - Now at bottom */}
        {selectedDrug && (
          <div className="info-section">
            <DrugInfoPanel
              drug={selectedDrug}
              drugInfo={drugInfo}
              isLoading={isLoadingDrugInfo}
              onClose={handleCloseDrugInfo}
            />
          </div>
        )}
      </main>

      {/* Footer with disclaimer */}
      <footer className="app-footer">
        <Disclaimer />
      </footer>
    </div>
  );
}

export default App;
