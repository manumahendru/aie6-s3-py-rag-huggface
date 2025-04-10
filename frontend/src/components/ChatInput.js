import React, { useState } from 'react';
import './ChatInput.css';

const ChatInput = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage('');
    }
  };

  return (
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <input
        type="text"
        className="chat-input"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Ask a question about your document..."
        disabled={disabled}
      />
      <button 
        type="submit" 
        className="send-button"
        disabled={!message.trim() || disabled}
      >
        {disabled ? 'Thinking...' : 'Send'}
      </button>
    </form>
  );
};

export default ChatInput; 