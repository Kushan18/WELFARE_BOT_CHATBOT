import React from 'react';
import './MessageBubble.css';

function formatTime(d) { return new Date(d).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }

export default function MessageBubble({ message }) {
  const isBot = message.role === 'bot';
  const score = message.confidenceScore;
  
  let badgeColorClass = '';
  let badgeLabel = '';
  
  if (isBot && score !== undefined && score !== null) {
    if (score >= 95) {
      badgeColorClass = 'badge-green';
      badgeLabel = `✓ ${score}%`;
    } else if (score >= 85) {
      badgeColorClass = 'badge-blue';
      badgeLabel = `✓ ${score}%`;
    } else {
      badgeColorClass = 'badge-yellow';
      badgeLabel = `${score}%`;
    }
  }

  return (
    <div className={`msg-row ${isBot ? 'bot' : 'user'}`}>
      {isBot && <div className='msg-avatar'>🤖</div>}
      <div className={`msg-bubble ${isBot ? 'bot' : 'user'}`}>
        {isBot && badgeLabel && (
          <span className={`confidence-badge ${badgeColorClass}`}>
            {badgeLabel}
          </span>
        )}
        <div className='msg-text'>{message.text}</div>
        {isBot && message.showApplyButton && message.applyLink && (
          <div style={{ marginTop: '10px' }}>
            <a href={message.applyLink} target="_blank" rel="noopener noreferrer" className="btn-send" style={{ textDecoration: 'none', padding: '8px 16px', display: 'inline-block', borderRadius: '20px', backgroundColor: '#2563eb', color: 'white', fontWeight: 'bold' }}>
              Apply Now ↗
            </a>
          </div>
        )}
        <div className='msg-time'>{formatTime(message.timestamp)}</div>
      </div>
    </div>
  );
}
