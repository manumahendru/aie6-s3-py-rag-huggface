import React, { useState, useEffect, useRef } from 'react';
import './Chat.css';
import ChatInput from './ChatInput';
import Message from './Message';

// Get websocket URL from environment or fallback to default
const getWsUrl = () => {
  // Use environment variable if available
  if (process.env.REACT_APP_WS_URL) {
    return process.env.REACT_APP_WS_URL;
  }
  // Otherwise, construct URL dynamically
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host; // Includes hostname and port
  return `${protocol}//${host}`;
};

const Chat = ({ session }) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const webSocketRef = useRef(null);
  const messagesEndRef = useRef(null);
  
  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  useEffect(() => {
    // Add initial system message
    setMessages([
      {
        id: 'system-1',
        text: `You've uploaded "${session.filename}". Ask any questions about this document!`,
        sender: 'system'
      }
    ]);
    
    // Clean up WebSocket on unmount
    return () => {
      if (webSocketRef.current) {
        webSocketRef.current.close();
      }
    };
  }, [session]);
  
  const handleSendMessage = async (message) => {
    if (!message.trim()) return;
    
    // Add user message to chat
    const userMessageId = `user-${Date.now()}`;
    setMessages(prevMessages => [
      ...prevMessages,
      { id: userMessageId, text: message, sender: 'user' }
    ]);
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Create a new WebSocket connection for each message
      if (webSocketRef.current) {
        webSocketRef.current.close();
      }
      
      // Use the WebSocket URL from environment or default
      const wsUrl = `${getWsUrl()}/chat/${session.session_id}`;
      console.log(`WebSocket URL: ${wsUrl}`);
      const ws = new WebSocket(wsUrl);

      webSocketRef.current = ws;
      
      // Add assistant message placeholder
      const assistantMessageId = `assistant-${Date.now()}`;
      setMessages(prevMessages => [
        ...prevMessages,
        { id: assistantMessageId, text: '', sender: 'assistant', isStreaming: true }
      ]);
      
      let fullResponse = '';
      
      ws.onopen = () => {
        ws.send(JSON.stringify({ query: message }));
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.error) {
          setError(data.error);
          return;
        }
        
        if (data.chunk) {
          fullResponse += data.chunk;
          
          // Update the streaming message with new content
          setMessages(prevMessages => 
            prevMessages.map(msg => 
              msg.id === assistantMessageId 
                ? { ...msg, text: fullResponse } 
                : msg
            )
          );
        }
        
        if (data.done) {
          // Mark message as no longer streaming
          setMessages(prevMessages => 
            prevMessages.map(msg => 
              msg.id === assistantMessageId 
                ? { ...msg, isStreaming: false } 
                : msg
            )
          );
          
          ws.close();
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Error connecting to the server');
        setIsLoading(false);
      };
      
      ws.onclose = () => {
        setIsLoading(false);
      };
      
    } catch (err) {
      console.error('Error sending message:', err);
      setError('Failed to send message');
      setIsLoading(false);
    }
  };
  
  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>Chat with your document: {session.filename}</h2>
      </div>
      
      <div className="messages-container">
        {messages.map(message => (
          <Message 
            key={message.id} 
            text={message.text} 
            sender={message.sender}
            isStreaming={message.isStreaming}
          />
        ))}
        {error && (
          <div className="error-message">
            Error: {error}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <ChatInput 
        onSendMessage={handleSendMessage} 
        disabled={isLoading} 
      />
    </div>
  );
};

export default Chat; 