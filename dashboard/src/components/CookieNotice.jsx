import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { useFocusTrap } from '../hooks/useFocusTrap';
import './CookieNotice.css';

export default function CookieNotice({ show, onAccept, onEssentialOnly }) {
  const dialogRef = useRef(null);

  useFocusTrap(dialogRef, {
    active: show,
    onEscape: onEssentialOnly,
  });

  if (!show) return null;

  return (
    <div
      ref={dialogRef}
      className="cookie-notice"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cookie-notice-title"
    >
      <p id="cookie-notice-title" className="cookie-notice__text">
        We use cookies for basic analytics (Vercel Analytics) after you accept, plus local storage for
        preferences. See our{' '}
        <Link to="/privacy#cookies">Privacy Policy</Link>.
      </p>
      <div className="cookie-notice__actions">
        <button type="button" className="cookie-notice__secondary" onClick={onEssentialOnly}>
          Essential only
        </button>
        <button type="button" className="cookie-notice__accept" onClick={onAccept}>
          Accept
        </button>
      </div>
    </div>
  );
}
