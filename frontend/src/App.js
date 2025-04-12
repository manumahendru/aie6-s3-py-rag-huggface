import React, { useState } from 'react';
import './App.css';
import FileUpload from './components/FileUpload';
import Chat from './components/Chat';

function App() {
  const [session, setSession] = useState(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>RAG Application</h1>
      </header>
      <main className="app-main">
        {!session ? (
          <FileUpload onSessionCreated={setSession} />
        ) : (
          <Chat session={session} />
        )}
      </main>
    </div>
  );
}

export default App; 