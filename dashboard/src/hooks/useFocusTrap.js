import { useEffect, useRef } from 'react';

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

function getFocusableElements(container) {
  if (!container) return [];
  return Array.from(container.querySelectorAll(FOCUSABLE)).filter(
    (el) => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true',
  );
}

/**
 * Trap focus inside a modal dialog, handle Escape, restore focus on close (IS 5568).
 */
export function useFocusTrap(containerRef, { active, onEscape }) {
  const previousFocusRef = useRef(null);

  useEffect(() => {
    if (!active || !containerRef.current) return undefined;

    previousFocusRef.current = document.activeElement;
    const focusables = getFocusableElements(containerRef.current);
    if (focusables.length > 0) {
      focusables[0].focus();
    } else {
      containerRef.current.setAttribute('tabindex', '-1');
      containerRef.current.focus();
    }

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onEscape?.();
        return;
      }
      if (event.key !== 'Tab' || !containerRef.current) return;

      const elements = getFocusableElements(containerRef.current);
      if (elements.length === 0) return;

      const first = elements[0];
      const last = elements[elements.length - 1];
      const { activeElement } = document;

      if (event.shiftKey && activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      const previous = previousFocusRef.current;
      if (previous && typeof previous.focus === 'function' && document.contains(previous)) {
        previous.focus();
      }
    };
  }, [active, onEscape, containerRef]);
}
