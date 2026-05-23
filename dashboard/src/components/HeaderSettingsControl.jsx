import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Settings } from 'lucide-react';
import './HeaderSettingsControl.css';

const LEGAL_LINKS = [
  { to: '/about', label: 'About' },
  { to: '/accessibility', label: 'Accessibility' },
  { to: '/privacy', label: 'Privacy Policy' },
  { to: '/terms', label: 'Terms of Use' },
];

export default function HeaderSettingsControl({
  isMobile,
  iconSize,
  prefsActive,
  onOpenPreferences,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const rootRef = useRef(null);
  const menuId = useId();

  const closeMenu = useCallback(() => setMenuOpen(false), []);

  useEffect(() => {
    if (!isMobile || !menuOpen) return undefined;

    const onPointerDown = (event) => {
      if (rootRef.current?.contains(event.target)) return;
      closeMenu();
    };

    const onKeyDown = (event) => {
      if (event.key === 'Escape') closeMenu();
    };

    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [isMobile, menuOpen, closeMenu]);

  const handleCogClick = () => {
    if (isMobile) {
      setMenuOpen((open) => !open);
      return;
    }
    onOpenPreferences();
  };

  const handleOpenPreferences = () => {
    closeMenu();
    onOpenPreferences();
  };

  return (
    <div className="header-settings" ref={rootRef}>
      <button
        type="button"
        className={`icon-btn ${prefsActive ? 'icon-btn-active' : ''}`}
        onClick={handleCogClick}
        aria-label={isMobile ? 'Settings menu' : 'Alert notification preferences'}
        aria-expanded={isMobile ? menuOpen : undefined}
        aria-haspopup={isMobile ? 'menu' : undefined}
        aria-controls={isMobile ? menuId : undefined}
      >
        <Settings size={iconSize} aria-hidden />
      </button>

      {isMobile && menuOpen ? (
        <div
          id={menuId}
          className="header-settings__menu"
          role="menu"
          aria-label="Settings and legal"
        >
          <button
            type="button"
            className="header-settings__item"
            role="menuitem"
            onClick={handleOpenPreferences}
          >
            Alert preferences
          </button>
          {LEGAL_LINKS.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="header-settings__item"
              role="menuitem"
              onClick={closeMenu}
            >
              {label}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
