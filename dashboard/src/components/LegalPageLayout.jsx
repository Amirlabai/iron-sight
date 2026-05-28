import { Link } from 'react-router-dom';
import { Moon, Sun } from 'lucide-react';
import SEO from './SEO';
import SiteFooter from './SiteFooter';
import AccessibilityToolbar from './AccessibilityToolbar';
import { useThemeMode } from '../hooks/useThemeMode';
import '../pages/LegalPage.css';

export default function LegalPageLayout({
  pathname,
  children,
  breadcrumbs = [],
  seoExtras = {},
}) {
  const {
    noindex = false,
    includeFaq = false,
    includeFaqSchema = false,
    title,
    description,
    keywords,
    url,
  } = seoExtras;

  const crumbItems = [{ name: 'Home', url: '/' }, ...breadcrumbs];
  const { isLightMode, toggleThemeMode } = useThemeMode();

  return (
    <>
      <div className="legal-page-shell">
        <SEO
          pathname={pathname}
          title={title}
          description={description}
          keywords={keywords}
          canonical={url}
          noindex={noindex}
          includeFaq={includeFaq || includeFaqSchema}
          breadcrumbs={crumbItems}
        />
        <a href="#legal-main" className="skip-link">
          Skip to content
        </a>
        <header className="legal-page-header">
          <Link to="/" className="legal-page-home-link">
            ← IRON SIGHT
          </Link>
          <button
            type="button"
            className="legal-page-theme-btn"
            onClick={toggleThemeMode}
            aria-label={isLightMode ? 'Switch to dark mode' : 'Switch to light mode'}
            title={isLightMode ? 'Dark mode' : 'Light mode'}
          >
            {isLightMode ? <Moon size={18} aria-hidden /> : <Sun size={18} aria-hidden />}
            <span className="legal-page-theme-btn__label">
              {isLightMode ? 'Dark' : 'Light'}
            </span>
          </button>
        </header>
        <main id="legal-main" className="legal-page-main">
          {children}
        </main>
        <SiteFooter />
      </div>
      <AccessibilityToolbar legalPage />
    </>
  );
}
