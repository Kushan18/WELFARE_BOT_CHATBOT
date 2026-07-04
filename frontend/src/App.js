import React, { useState, useEffect, useRef } from 'react';
import Chat from './components/Chat';
import ProfileModal from './components/ProfileModal';
import Background from './components/Background';

function genSession() { return 'sess_' + Math.random().toString(36).substring(2, 15); }

export default function App() {
  const [sessionId, setSessionId] = useState(() => {
    const existing = localStorage.getItem('wb_session_id');
    if (existing) return existing;
    const id = genSession();
    localStorage.setItem('wb_session_id', id);
    return id;
  });
  const [userName, setUserName] = useState(() => localStorage.getItem('wb_user_name') || '');
  const [showModal, setShowModal] = useState(false);
  const chatRef = useRef(null);

  useEffect(() => {
    if (userName) {
      localStorage.setItem('wb_user_name', userName);
    } else {
      localStorage.removeItem('wb_user_name');
    }
  }, [userName]);

  const handleOpenForm = () => {
    setShowModal(true);
  };

  const handleReset = () => {
    localStorage.removeItem('wb_user_name');
    const id = genSession();
    localStorage.setItem('wb_session_id', id);
    setUserName('');
    setSessionId(id);
  };

  const handleFormSuccess = () => {
    setShowModal(false);
    chatRef.current?.handleFormSubmitted();
  };

  return (
    <div style={{ height: '100%', width: '100%' }}>
      <Background />
      <Chat 
        ref={chatRef}
        key={sessionId} 
        sessionId={sessionId} 
        userName={userName} 
        onNameCapture={setUserName} 
        onOpenForm={handleOpenForm}
        onResetSession={handleReset}
      />
      {showModal && (
        <ProfileModal 
          sessionId={sessionId} 
          onClose={() => setShowModal(false)} 
          onSuccess={handleFormSuccess}
        />
      )}
    </div>
  );
}
