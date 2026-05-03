import React, { useEffect, useRef } from 'react';
import './ChatInterface.css';

/**
 * ChatInterface - Displays chat messages in a chatbot-style UI with input
 */
function ChatInterface({ 
  messages, 
  chatInput, 
  setChatInput, 
  onSubmit, 
  isLoading,
  awaitingConfirmation,
  pendingDrugName 
}) {
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when awaiting confirmation
  useEffect(() => {
    if (awaitingConfirmation && inputRef.current) {
      inputRef.current.focus();
    }
  }, [awaitingConfirmation]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (chatInput.trim() && !isLoading) {
      onSubmit(chatInput);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Determine placeholder text
  const getPlaceholder = () => {
    if (awaitingConfirmation && pendingDrugName) {
      return `Confirm or correct the drug name "${pendingDrugName}"...`;
    }
    return "Type a drug name (e.g., Paracetamol, Amoxicillin)...";
  };

  return (
    <div className="chat-interface">
      <div className="chat-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`chat-message ${message.type === 'user' ? 'user-message' : 'bot-message'} ${
              message.data?.type === 'error' ? 'error-message' : ''
            } ${message.data?.type === 'warning' ? 'warning-message' : ''} ${
              message.data?.type === 'confirmation_needed' ? 'confirmation-message' : ''
            }`}
          >
            <div className="message-avatar">
              {message.type === 'user' ? '👤' : '🤖'}
            </div>
            <div className="message-content">
              <p>{message.content}</p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Chat Input */}
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          className={`chat-input ${awaitingConfirmation ? 'awaiting-confirmation' : ''}`}
          placeholder={getPlaceholder()}
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <button 
          type="submit" 
          className={`chat-send-btn ${awaitingConfirmation ? 'confirm-btn-active' : ''}`}
          disabled={!chatInput.trim() || isLoading}
        >
          {isLoading ? (
            <span className="btn-spinner"></span>
          ) : awaitingConfirmation ? (
            '✓'
          ) : (
            '➤'
          )}
        </button>
      </form>
    </div>
  );
}

export default ChatInterface;
