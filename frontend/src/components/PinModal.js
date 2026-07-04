import React, { useState, useRef, useEffect } from 'react';
import './PinModal.css';

const PinModal = ({ mode, onSubmit, onClose, errorMsg, lockoutUntil }) => {
  const [pin, setPin] = useState(['', '', '', '']);
  const inputRefs = useRef([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [setupStep, setSetupStep] = useState('set'); // 'set' or 'confirm'
  const [tempPin, setTempPin] = useState('');
  const [localError, setLocalError] = useState(null);
  const [shake, setShake] = useState(false);
  const [success, setSuccess] = useState(false);
  const [remainingTime, setRemainingTime] = useState(0);

  useEffect(() => {
    let interval = null;
    if (lockoutUntil) {
      const targetTime = new Date(lockoutUntil).getTime();
      const updateTimer = () => {
        const now = new Date().getTime();
        const diff = Math.floor((targetTime - now) / 1000);
        if (diff > 0) {
          setRemainingTime(diff);
        } else {
          setRemainingTime(0);
          if (interval) clearInterval(interval);
        }
      };
      updateTimer();
      interval = setInterval(updateTimer, 1000);
    } else {
      setRemainingTime(0);
    }
    return () => { if (interval) clearInterval(interval); };
  }, [lockoutUntil]);

  useEffect(() => {
    if (inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, [setupStep]);

  useEffect(() => {
    if (errorMsg) {
      triggerError(errorMsg);
      setIsSubmitting(false);
    }
  }, [errorMsg]);

  const triggerError = (msg) => {
    setLocalError(msg);
    setShake(true);
    setPin(['', '', '', '']);
    setTimeout(() => {
      setShake(false);
      if (inputRefs.current[0]) inputRefs.current[0].focus();
    }, 500);
  };

  const handleChange = (index, value) => {
    if (value && !/^[0-9]+$/.test(value)) return;
    setLocalError(null); // Clear error on typing

    const newPin = [...pin];
    if (value.length > 1) {
      const pasted = value.slice(0, 4 - index).split('');
      for (let i = 0; i < pasted.length; i++) {
        newPin[index + i] = pasted[i];
      }
      setPin(newPin);
      
      const nextEmpty = newPin.findIndex(v => v === '');
      if (nextEmpty !== -1 && inputRefs.current[nextEmpty]) {
        inputRefs.current[nextEmpty].focus();
      } else if (nextEmpty === -1) {
        inputRefs.current[3].focus();
        checkAndSubmit(newPin);
      }
      return;
    }

    newPin[index] = value;
    setPin(newPin);

    if (value !== '' && index < 3) {
      inputRefs.current[index + 1].focus();
    }
    
    checkAndSubmit(newPin);
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !pin[index] && index > 0) {
      inputRefs.current[index - 1].focus();
    }
    if (e.key === 'Enter') {
      checkAndSubmit(pin, true);
    }
  };

  const checkAndSubmit = (currentPin, force = false) => {
    const pinString = currentPin.join('');
    if (pinString.length === 4) {
      if (mode === 'setup') {
        if (setupStep === 'set') {
          // Move to confirm step
          setTimeout(() => {
            setTempPin(pinString);
            setPin(['', '', '', '']);
            setSetupStep('confirm');
          }, 200);
        } else if (setupStep === 'confirm') {
          if (pinString === tempPin) {
            setSuccess(true);
            setIsSubmitting(true);
            setTimeout(() => {
              onSubmit(pinString);
            }, 800);
          } else {
            triggerError("PINs didn't match — try again");
            setTimeout(() => {
              setSetupStep('set');
              setTempPin('');
            }, 500);
          }
        }
      } else {
        // mode === 'login'
        setIsSubmitting(true);
        setTimeout(() => {
          onSubmit(pinString);
        }, 400);
      }
    }
  };

  const getTitle = () => {
    if (mode === 'login') return 'Enter your PIN';
    if (mode === 'setup') {
      if (success) return 'Success!';
      return setupStep === 'confirm' ? 'Confirm PIN' : 'Set up your PIN';
    }
    return 'Setup PIN';
  };

  const getSubtitle = () => {
    if (remainingTime > 0) return `Try again in ${Math.floor(remainingTime / 60).toString().padStart(2, '0')}:${(remainingTime % 60).toString().padStart(2, '0')}`;
    if (mode === 'login') return 'Please enter your 4-digit PIN to continue.';
    if (mode === 'setup') {
      if (success) return 'PIN set successfully.';
      return setupStep === 'confirm' ? 'Please re-enter to confirm.' : 'Create a 4-digit PIN to secure your account.';
    }
    return '';
  };

  const handleBack = () => {
    setSetupStep('set');
    setTempPin('');
    setPin(['', '', '', '']);
    setLocalError(null);
  };

  const handleForgotPin = () => {
    onSubmit('forgot_pin');
  };

  return (
    <div className="pin-modal-overlay">
      <div className={`pin-modal-container ${isSubmitting && !success ? 'submitting' : ''} ${shake ? 'shake' : ''}`}>
        {!isSubmitting && mode === 'setup' && setupStep === 'confirm' && !success && (
          <button className="pin-back-btn" onClick={handleBack} aria-label="Back">
            ←
          </button>
        )}
        <button className="pin-close-btn" onClick={onClose} aria-label="Close">
          &times;
        </button>
        <div className="pin-header">
          <div className="pin-icon">{success ? '✅' : '🔒'}</div>
          <h2>{getTitle()}</h2>
          <p className={localError ? 'error-text' : ''}>{localError || getSubtitle()}</p>
        </div>
        
        {!success && (
          <div className={`pin-inputs ${shake ? 'error' : ''}`}>
            {pin.map((digit, index) => (
              <input
                key={index}
                ref={el => inputRefs.current[index] = el}
                type="password"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                className={digit ? 'filled' : ''}
                disabled={isSubmitting || remainingTime > 0}
                autoComplete="off"
              />
            ))}
          </div>
        )}
        
        {isSubmitting && !success && remainingTime === 0 && (
          <div className="pin-loading">
            <div className="spinner"></div>
            <span>Verifying...</span>
          </div>
        )}

        {mode === 'login' && !isSubmitting && remainingTime === 0 && (
          <div className="forgot-pin-container">
            <button className="forgot-pin-btn" onClick={handleForgotPin}>Forgot PIN?</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PinModal;
