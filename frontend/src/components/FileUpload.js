import React, { useState } from 'react';
import './FileUpload.css';

// Get API URL from environment or fallback to default
const getApiUrl = () => {
  return process.env.REACT_APP_BACKEND_URL || '';
};

const FileUpload = ({ onSessionCreated }) => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    // Check if file is PDF or TXT
    const fileExtension = file.name.split('.').pop().toLowerCase();
    if (fileExtension !== 'pdf' && fileExtension !== 'txt') {
      setError('Only PDF and TXT files are supported');
      return;
    }

    try {
      setIsUploading(true);
      
      const formData = new FormData();
      formData.append('file', file);

      const apiUrl = `${getApiUrl()}/upload`;
      console.log(`Uploading to: ${apiUrl}`);

      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload file');
      }

      const data = await response.json();
      onSessionCreated(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="file-upload">
      <h2>Upload a Document</h2>
      <p className="upload-instruction">Upload a PDF or text file to start asking questions about it.</p>
      
      <form onSubmit={handleSubmit} className="upload-form">
        <div className="file-input-container">
          <input
            type="file"
            id="file"
            accept=".pdf,.txt"
            onChange={handleFileChange}
            className="file-input"
          />
          <label htmlFor="file" className="file-label">
            {file ? file.name : 'Choose a file'}
          </label>
        </div>
        
        <button 
          type="submit" 
          className="upload-button" 
          disabled={isUploading}
        >
          {isUploading ? 'Uploading...' : 'Upload'}
        </button>
      </form>
      
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default FileUpload; 