import { Link } from 'react-router-dom';
import { LEGAL_CONTACT_NAME } from '../config/seoConfig';
import './SiteFooter.css';

export default function SiteFooter({ compact = false }) {
  return (
    <footer className={`site-footer ${compact ? 'site-footer--compact' : ''}`}>
      <nav className="site-footer__nav" aria-label="Legal and information">
        <Link to="/about">About</Link>
        <Link to="/accessibility">Accessibility</Link>
        <Link to="/privacy">Privacy Policy</Link>
        <Link to="/terms">Terms of Use</Link>
      </nav>
      <p className="site-footer__copy">
        © {new Date().getFullYear()} {LEGAL_CONTACT_NAME} — Iron Sight
      </p>
    </footer>
  );
}
