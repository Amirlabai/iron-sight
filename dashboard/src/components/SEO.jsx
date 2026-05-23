import { Helmet } from 'react-helmet-async';
import {
  getRouteSeo,
  joinUrl,
  getOrganizationJsonLd,
  getWebSiteJsonLd,
  getWebApplicationJsonLd,
  getFaqPageJsonLd,
  getBreadcrumbJsonLd,
} from '../config/seoConfig';

export default function SEO({
  pathname = '/',
  title,
  description,
  keywords,
  canonical,
  noindex = false,
  includeWebApp = false,
  includeFaq = false,
  breadcrumbs = null,
}) {
  const defaults = getRouteSeo(pathname);
  const resolvedTitle = title ?? defaults.title;
  const resolvedDescription = description ?? defaults.description;
  const resolvedKeywords = keywords ?? defaults.keywords;
  const resolvedCanonical = canonical ?? defaults.canonical;
  const ogImage = joinUrl(defaults.ogImagePath);

  const jsonLd = [];
  if (includeWebApp) {
    jsonLd.push(getWebApplicationJsonLd(), getOrganizationJsonLd(), getWebSiteJsonLd());
  }
  if (includeFaq) {
    jsonLd.push(getFaqPageJsonLd());
  }
  if (breadcrumbs?.length) {
    jsonLd.push(getBreadcrumbJsonLd(breadcrumbs));
  }

  return (
    <Helmet>
      <title>{resolvedTitle}</title>
      <meta name="description" content={resolvedDescription} />
      <meta name="keywords" content={resolvedKeywords} />
      <link rel="canonical" href={resolvedCanonical} />
      <meta
        name="robots"
        content={noindex ? 'noindex, follow' : 'index, follow, max-image-preview:large'}
      />

      <meta property="og:type" content={defaults.ogType} />
      <meta property="og:url" content={resolvedCanonical} />
      <meta property="og:title" content={resolvedTitle} />
      <meta property="og:description" content={resolvedDescription} />
      <meta property="og:image" content={ogImage} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />
      <meta property="og:image:alt" content={defaults.ogImageAlt} />
      <meta property="og:locale" content={defaults.ogLocale} />
      <meta property="og:site_name" content={defaults.siteName} />

      <meta name="twitter:card" content={defaults.twitterCard} />
      <meta name="twitter:url" content={resolvedCanonical} />
      <meta name="twitter:title" content={resolvedTitle} />
      <meta name="twitter:description" content={resolvedDescription} />
      <meta name="twitter:image" content={ogImage} />

      {/* Must be native elements only — function components inside Helmet crash react-helmet-async v3 */}
      {jsonLd.map((block, i) => (
        <script key={`jsonld-${i}`} type="application/ld+json">
          {JSON.stringify(block)}
        </script>
      ))}
    </Helmet>
  );
}
