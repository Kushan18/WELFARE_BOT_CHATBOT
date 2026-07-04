import React, { useState } from 'react';
import axios from 'axios';
import './FeedbackModal.css';

const API = process.env.REACT_APP_API_URL || '';

export default function FeedbackModal({ sessionId, userName, onClose }) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [opinion, setOpinion] = useState('');
  const [suggestion, setSuggestion] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (rating === 0) {
      alert('Please select a star rating.');
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(API + '/api/feedback', {
        session_id: sessionId,
        user_name: userName || "Unknown",
        rating,
        opinion,
        suggestion
      });
      setSuccess(true);
      setTimeout(onClose, 2000); // Close automatically after 2s on success
    } catch (err) {
      alert('Failed to submit feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="feedback-modal-overlay">
      <div className="feedback-modal">
        <button className="feedback-close" onClick={onClose} aria-label="Close">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
        
        {success ? (
          <div className="feedback-success">
            <div className="success-icon">✓</div>
            <h3>Thank You!</h3>
            <p>Your feedback has been submitted successfully.</p>
          </div>
        ) : (
          <form className="feedback-form" onSubmit={handleSubmit}>
            <h2>Rate Your Experience</h2>
            <p className="feedback-subtitle">Help us improve WelfareBot by sharing your feedback.</p>
            
            <div className="star-rating">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  className={`star ${star <= (hoverRating || rating) ? 'filled' : ''}`}
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                >
                  {star <= (hoverRating || rating) ? '★' : '☆'}
                </button>
              ))}
            </div>

            <div className="form-group">
              <label>Opinion/Comments</label>
              <textarea 
                placeholder="What did you think of the chat?" 
                value={opinion} 
                onChange={e => setOpinion(e.target.value)}
                rows={3}
              />
            </div>

            <div className="form-group">
              <label>Suggestions</label>
              <textarea 
                placeholder="Any suggestions for improvement?" 
                value={suggestion} 
                onChange={e => setSuggestion(e.target.value)}
                rows={3}
              />
            </div>

            <button type="submit" className="btn-submit-feedback" disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit Feedback'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
