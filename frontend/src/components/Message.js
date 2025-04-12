import React from 'react';
import './Message.css';

const Message = ({ text, sender, isStreaming }) => {
  const getMessageClassName = () => {
    switch (sender) {
      case 'user':
        return 'message user-message';
      case 'assistant':
        return 'message assistant-message';
      case 'system':
        return 'message system-message';
      default:
        return 'message';
    }
  };

  return (
    <div className={getMessageClassName()}>
      <div className="message-content">
        {text}
        {isStreaming && <span className="cursor-blink">|</span>}
      </div>
      {sender !== 'system' && (
        <div className="message-sender">
          {sender === 'user' ? 'You' : 'Assistant'}
        </div>
      )}
    </div>
  );
};

export default Message; 