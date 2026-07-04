import React, { useState, useEffect, useRef, useCallback, useImperativeHandle, forwardRef } from 'react';
import axios from 'axios';
import MessageBubble from './MessageBubble';
import ChipRow from './ChipRow';
import PinModal from './PinModal';
import FeedbackModal from './FeedbackModal';
import './Chat.css';

const API = process.env.REACT_APP_API_URL || '';

const WELCOME = {
  id: 'w', role: 'bot',
  text: "Welcome to WelfareBot! I help Indian citizens discover government welfare schemes they're eligible for.|||To get started, could you tell me your name?",
  chips: [], confidenceScore: 100, timestamp: new Date()
};

const INITIAL_MESSAGES = WELCOME.text.split('|||').map((t, i, arr) => ({
  ...WELCOME,
  id: 'w' + i,
  text: t.trim(),
  chips: i === arr.length - 1 ? WELCOME.chips : [],
  confidenceScore: i === arr.length - 1 ? WELCOME.confidenceScore : null
}));

const Chat = forwardRef(({ sessionId, userName, onNameCapture, onOpenForm, onResetSession }, ref) => {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isOnline, setIsOnline] = useState(true);
  const [recording, setRecording] = useState(false);
  const [showPinPopup, setShowPinPopup] = useState(false);
  const [pinMode, setPinMode] = useState('setup');
  const [pinLockoutUntil, setPinLockoutUntil] = useState(null);
  const [chatEnded, setChatEnded] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [showEndChatConfirm, setShowEndChatConfirm] = useState(false);
  

  
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const msgCount = useRef(1);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    // 1. Check server health
    axios.get(API + '/health').then(() => setIsOnline(true)).catch(() => setIsOnline(false));

    // 2. Fetch past conversation history
    axios.get(API + `/conversation/${sessionId}`)
      .then(res => {
        if (res.data && res.data.messages && res.data.messages.length > 0) {
          const fetchedMessages = res.data.messages.map(m => ({
            id: m.id || Math.random(),
            role: m.role,
            text: m.text,
            chips: m.chips || [],
            applyLink: m.apply_link || '',
            showApplyButton: m.show_apply_button || false,
            confidenceScore: m.confidence_score,
            timestamp: new Date(m.timestamp)
          }));
          setMessages([...INITIAL_MESSAGES, ...fetchedMessages]);
        }
      })
      .catch(err => {
        console.error("Failed to load conversation history:", err);
      });
  }, [sessionId]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  const addMsg = useCallback((role, text, chips = [], applyLink = '', confidenceScore = null, showApplyButton = false) => {
    setMessages(prev => [...prev, { id: Date.now() + Math.random(), role, text, chips, applyLink, confidenceScore, showApplyButton, timestamp: new Date() }]);
  }, []);

  useImperativeHandle(ref, () => ({
    handleFormSubmitted() {
      sendMessage("Form Submitted");
    }
  }));

  const sendMessage = useCallback(async (text, hidden = false) => {
    const t = text.trim();
    if (!t || loading) return;
    
    if (!hidden) {
      addMsg('user', t);
    }
    
    setInput('');
    setLoading(true);
    msgCount.current += 1;
    if (!userName && msgCount.current <= 2 && !hidden) onNameCapture(t);
    
    try {
      const res = await axios.post(API + '/chat', { session_id: sessionId, message: t, is_hidden: hidden }, { timeout: 120000 });
      const { reply, show_form_choice, show_pin_popup, pin_mode, pin_lockout_until, chips, apply_link, show_apply_button, clear_session, confidence_score } = res.data;
      
      if (clear_session) {
        onResetSession();
        return;
      }
      
      if (reply) {
        const parts = reply.split('|||');
        parts.forEach((part, index) => {
          const isLast = index === parts.length - 1;
          addMsg('bot', part.trim(), isLast ? (chips || []) : [], isLast ? (apply_link || '') : '', isLast ? confidence_score : null, isLast ? show_apply_button : false);
        });
      }
      
      if (show_form_choice) onOpenForm();
      if (show_pin_popup) {
        setPinMode(pin_mode || 'setup');
        if (pin_lockout_until !== undefined) setPinLockoutUntil(pin_lockout_until);
        setShowPinPopup(true);
      }
    } catch (err) {
      const msg = err.code === 'ECONNABORTED' ? 'Request timed out - please try again.' : 'Something went wrong. Is the backend running?';
      addMsg('bot', msg);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [loading, sessionId, userName, addMsg, onNameCapture, onOpenForm, onResetSession]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('file', audioBlob, 'voice.webm');
        setLoading(true);
        try {
          const res = await axios.post(API + '/voice-input', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          if (res.data.show_pin_popup !== undefined) setShowPinPopup(res.data.show_pin_popup);
          if (res.data.pin_mode) setPinMode(res.data.pin_mode);
          if (res.data.pin_lockout_until !== undefined) setPinLockoutUntil(res.data.pin_lockout_until);

          if (res.data.status === 'success' && res.data.transcribed_text) {
            sendMessage(res.data.transcribed_text);
          } else if (res.data.clear_session) {
            onResetSession();
          } else {
            addMsg('bot', "Sorry, I couldn't transcribe the audio. Please type.");
          }
        } catch (err) {
          addMsg('bot', "Voice input transcription failed. Please use text.");
        } finally {
          setLoading(false);
        }
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.start();
      setRecording(true);
    } catch (err) {
      alert("Microphone permission denied or not supported.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
    }
  };

  const lastChips = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'bot' && messages[i].chips?.length > 0) {
        return { idx: i, chips: messages[i].chips, applyLink: messages[i].applyLink, msg: messages[i] };
      }
    }
    return null;
  })();

  return (
    <div className='chat-root'>
      <header className='chat-header'>
        <div className='chat-header-left'>
          <div className='bot-avatar'>
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.6"><rect x="4" y="8" width="16" height="12" rx="3"/><circle cx="9" cy="14" r="1.2" fill="#fff"/><circle cx="15" cy="14" r="1.2" fill="#fff"/><path d="M12 8V4M9 4h6"/></svg>
          </div>
          <div>
            <div className='bot-name'>WelfareBot</div>
            <div className='bot-status online'>
              <span className='status-dot' />{isOnline ? 'Online' : 'Offline'}
            </div>
          </div>
        </div>
        <div className='chat-header-actions'>
          {chatEnded ? (
            <button className='btn-header-action btn-start-chat-green' onClick={() => {
              onResetSession();
              setChatEnded(false);
            }}>
              Start Chat
            </button>
          ) : (
            <button className='btn-header-action btn-end-chat' onClick={() => {
              setShowEndChatConfirm(true);
            }}>
              End Chat
            </button>
          )}
        </div>
      </header>
      <div className='chat-messages'>
        {messages.map((msg, idx) => (
          <React.Fragment key={msg.id}>
            <MessageBubble message={msg} />
            {lastChips && lastChips.idx === idx && (
              <ChipRow 
                chips={lastChips.chips} 
                onChipClick={(c) => { 
                  const isFillForm = (chipText) => {
                    const t = chipText.toLowerCase();
                    return t.includes('fill form') || t.includes('form') || t.includes('फ़ॉर्म') || t.includes('ఫారమ్') || t.includes('படிவம்') || t.includes('ಫಾರ್ಮ್');
                  };
                  if (isFillForm(c)) {
                    onOpenForm(); 
                  } else if (c === 'Apply Now') {
                    if (lastChips.applyLink) {
                      window.open(lastChips.applyLink, '_blank');
                    } else {
                      sendMessage(c);
                    }
                  } else if (c === 'Start Over') {
                    onResetSession();
                    setChatEnded(false);
                  } else {
                    sendMessage(c); 
                  }
                }} 
                disabled={loading} 
              />
            )}
          </React.Fragment>
        ))}
        {loading && <div className='typing-indicator'><span /><span /><span /></div>}
        <div ref={bottomRef} />
      </div>
      <form className='chat-input-bar' onSubmit={e => { e.preventDefault(); sendMessage(input); }}>
        <button 
          type='button' 
          className={`btn-mic ${recording ? 'recording' : ''}`} 
          onClick={recording ? stopRecording : startRecording}
          disabled={loading}
          title={recording ? 'Stop recording' : 'Record voice'}
        >
          <svg width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'>
            <path d='M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z' />
            <path d='M19 10v2a7 7 0 0 1-14 0v-2' />
            <line x1='12' y1='19' x2='12' y2='23' />
            <line x1='8' y1='23' x2='16' y2='23' />
          </svg>
        </button>
        <input ref={inputRef} className='chat-input' type='text' value={input} onChange={e => setInput(e.target.value)} placeholder={chatEnded ? 'Chat has ended. Click Start Over to begin again.' : (loading ? 'WelfareBot is typing...' : (recording ? 'Recording voice... Click mic to send' : 'Type a message...'))} disabled={loading || recording || chatEnded} autoComplete='off' />
        <button className='btn-send' type='submit' disabled={loading || !input.trim() || recording || chatEnded}>
          <svg width='20' height='20' viewBox='0 0 24 24' fill='none'><path d='M22 2L11 13' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'/><path d='M22 2L15 22L11 13L2 9L22 2Z' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'/></svg>
        </button>
      </form>
      {showFeedbackModal && (
        <FeedbackModal 
          sessionId={sessionId} 
          userName={userName}
          onClose={() => setShowFeedbackModal(false)} 
        />
      )}
      {showEndChatConfirm && (
        <div className="feedback-modal-overlay">
          <div className="feedback-modal" style={{textAlign: 'center', padding: '2rem'}}>
            <h2 style={{marginBottom: '1rem'}}>End Chat</h2>
            <p style={{marginBottom: '2rem', color: 'var(--text-secondary)'}}>Do you really want to end the chat?</p>
            <div style={{display: 'flex', gap: '1rem', justifyContent: 'center'}}>
              <button 
                className="btn-submit-feedback" 
                style={{background: 'var(--bg-glass)', border: '1px solid var(--border)'}} 
                onClick={() => setShowEndChatConfirm(false)}
              >
                Cancel
              </button>
              <button 
                className="btn-submit-feedback" 
                style={{background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.5)'}}
                onClick={() => {
                  setShowEndChatConfirm(false);
                  setChatEnded(true);
                  setShowFeedbackModal(true);
                }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
      {showPinPopup && (
        <PinModal 
          mode={pinMode} 
          lockoutUntil={pinLockoutUntil}
          errorMsg={messages.length > 0 && messages[messages.length - 1].role === 'bot' && (messages[messages.length - 1].text.includes('Incorrect PIN') || messages[messages.length - 1].text.includes("PIN doesn't match") || messages[messages.length - 1].text.includes("Invalid PIN") || messages[messages.length - 1].text.includes("Too many attempts")) ? messages[messages.length - 1].text : null}
          onSubmit={(pin) => {
            setShowPinPopup(false);
            setPinLockoutUntil(null);
            sendMessage(pin, true);
          }} 
          onClose={() => setShowPinPopup(false)} 
        />
      )}
    </div>
  );
});

export default Chat;
