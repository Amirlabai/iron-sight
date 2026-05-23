import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Contrast } from 'lucide-react';
import { useHighContrast } from '../hooks/useHighContrast';
import './AccessibilityToolbar.css';

const VIEWPORT_OVERLAY_ID = 'a11y-viewport-overlay';

function getViewportOverlay() {
  return document.getElementById(VIEWPORT_OVERLAY_ID);
}

export default function AccessibilityToolbar({ legalPage = false }) {
  const { enabled, toggle } = useHighContrast();
  const [portaled, setPortaled] = useState(false);

  useEffect(() => {
    if (!legalPage) return undefined;
    const overlay = getViewportOverlay();
    if (!overlay) return undefined;
    overlay.removeAttribute('hidden');
    overlay.style.cssText =
      'position:fixed;inset:0;z-index:10050;pointer-events:none;overflow:visible;';
    setPortaled(true);
    return () => {
      overlay.setAttribute('hidden', '');
      overlay.style.cssText = '';
    };
  }, [legalPage]);

  const legalToolbarStyle = {
    position: 'absolute',
    bottom: 'max(16px, env(safe-area-inset-bottom))',
    left: 'max(16px, env(safe-area-inset-left))',
    pointerEvents: 'auto',
    zIndex: 1,
  };

  const toolbar = legalPage ? (
    <div className="legal-a11y-toolbar" style={legalToolbarStyle}>
      <button
        type="button"
        className="a11y-toolbar__btn"
        onClick={toggle}
        aria-pressed={enabled}
        aria-label="Toggle high contrast mode"
        title="High contrast"
      >
        <Contrast size={18} aria-hidden />
        <span className="a11y-toolbar__label">High contrast</span>
      </button>
    </div>
  ) : (
    <div className="a11y-toolbar dashboard-a11y-toolbar">
      <button
        type="button"
        className="a11y-toolbar__btn"
        onClick={toggle}
        aria-pressed={enabled}
        aria-label="Toggle high contrast mode"
        title="High contrast"
      >
        <Contrast size={18} aria-hidden />
        <span className="a11y-toolbar__label">High contrast</span>
      </button>
    </div>
  );

  if (legalPage) {
    if (!portaled) return null;
    const overlay = getViewportOverlay();
    if (!overlay) return null;
    return createPortal(toolbar, overlay);
  }

  return toolbar;
}
