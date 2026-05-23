import { Link } from 'react-router-dom';
import SEO from './SEO';
import SiteFooter from './SiteFooter';
import AccessibilityToolbar from './AccessibilityToolbar';
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
