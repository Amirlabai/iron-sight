const DEFAULT_SITE_URL = 'https://iron-sight-drab.vercel.app';

const KEYWORDS_EN =
  'Iron Sight, Israel alerts, rocket tracking, tactical radar, airspace monitoring, civil defense alerts, real-time alerts, drone tracking, PWA';

const KEYWORDS_HE =
  'מעקב אזעקות, רדאר טקטי, פיקוד העורף, מעקב טילים, התרעות בזמן אמת, מפה טקטית, אזעקות ישראל';

export function getSiteUrl() {
  const raw = import.meta.env.VITE_SITE_URL || DEFAULT_SITE_URL;
  return raw.replace(/\/+$/, '');
}

export function joinUrl(path = '/') {
  const base = getSiteUrl();
  if (!path || path === '/') return `${base}/`;
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalized}`;
}

function mergeKeywords(...parts) {
  return parts.filter(Boolean).join(', ');
}

const SITE_NAME = 'Iron Sight';
const DEFAULT_OG_IMAGE = '/og-image.png';
const ORG_EMAIL = 'amirlabay+support@gmail.com';
const ORG_NAME = 'Amir Labay';
const GITHUB_URL = 'https://github.com/amirlabay/iron-sight';

const ROUTE_SEO = {
  '/': {
    title: 'Iron Sight | Live Israel Alert Map',
    description:
      'Real-time tactical map for Israel civil defense alerts, rocket and drone tracking, and airspace monitoring. Independent tooling — not an official government service.',
    keywords: mergeKeywords(KEYWORDS_EN, KEYWORDS_HE),
    ogImageAlt: 'Iron Sight tactical alert map for Israel',
  },
  '/about': {
    title: 'About Iron Sight',
    description:
      'Learn how Iron Sight maps live Israel alerts, rockets, drones, and civil defense notifications with tactical visualization and optional push alerts.',
    keywords: mergeKeywords(
      'about Iron Sight, Israel alert map FAQ',
      'מעקב אזעקות, אודות Iron Sight',
    ),
    ogImageAlt: 'About Iron Sight',
  },
  '/accessibility': {
    title: 'Accessibility Statement',
    description:
      'Iron Sight accessibility statement: WCAG 2.1 AA effort, IS 5568 alignment, known limits for the tactical map, and how to report barriers.',
    keywords: mergeKeywords(
      'accessibility, WCAG, IS 5568, Iron Sight',
      'נגישות, תקן ישראלי 5568',
    ),
    ogImageAlt: 'Iron Sight accessibility statement',
  },
  '/privacy': {
    title: 'Privacy Policy',
    description:
      'How Iron Sight handles geolocation, push subscriptions, local preferences, analytics cookies, and data processed via Vercel, Render, and MongoDB.',
    keywords: mergeKeywords(
      'privacy policy, Iron Sight, Israel',
      'מדיניות פרטיות',
    ),
    ogImageAlt: 'Iron Sight privacy policy',
  },
  '/terms': {
    title: 'Terms of Use',
    description:
      'Terms of use for Iron Sight: informational alert map, acceptable use, liability limits, and governing law in Israel.',
    keywords: mergeKeywords(
      'terms of use, Iron Sight',
      'תנאי שימוש',
    ),
    ogImageAlt: 'Iron Sight terms of use',
  },
};

export function getRouteSeo(pathname) {
  const path = pathname === '' ? '/' : pathname.replace(/\/+$/, '') || '/';
  const route = ROUTE_SEO[path] || ROUTE_SEO['/'];
  const canonical = joinUrl(path === '/' ? '/' : path);
  return {
    path,
    siteName: SITE_NAME,
    title: route.title,
    description: route.description,
    keywords: route.keywords,
    canonical,
    ogUrl: canonical,
    ogImagePath: DEFAULT_OG_IMAGE,
    ogImageAlt: route.ogImageAlt,
    ogLocale: 'en_IL',
    ogType: 'website',
    twitterCard: 'summary_large_image',
  };
}

export const FAQ_ITEMS = [
  {
    question: 'What is Iron Sight?',
    answer:
      'Iron Sight is a free web application that visualizes live civil defense and tactical alerts over Israel on an interactive map, with optional browser notifications.',
  },
  {
    question: 'Is Iron Sight an official government app?',
    answer:
      'No. Iron Sight is independent tooling built for situational awareness. Always follow official Home Front Command and authorities for life-safety decisions.',
  },
  {
    question: 'What alerts does the map show?',
    answer:
      'The dashboard displays rocket, drone, infiltration, earthquake, and related alert categories derived from upstream public alert feeds, clustered for clarity.',
  },
  {
    question: 'Do I need to share my location?',
    answer:
      'Location is optional. You can receive all alerts, filter by radius, or match alerts to your area only if you grant geolocation in the alert preferences wizard.',
  },
  {
    question: 'Can I install Iron Sight on my phone?',
    answer:
      'Yes. Iron Sight is a progressive web app (PWA). Use your browser’s install or “Add to Home Screen” option for quick access.',
  },
  {
    question: 'Who operates Iron Sight?',
    answer:
      `Iron Sight is operated by ${ORG_NAME}. For support or privacy requests, email ${ORG_EMAIL}.`,
  },
];

export function getOrganizationJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: SITE_NAME,
    url: getSiteUrl(),
    contactPoint: {
      '@type': 'ContactPoint',
      email: ORG_EMAIL,
      contactType: 'customer support',
    },
    founder: {
      '@type': 'Person',
      name: ORG_NAME,
    },
    sameAs: [GITHUB_URL],
  };
}

export function getWebSiteJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: SITE_NAME,
    url: getSiteUrl(),
    inLanguage: 'en',
    publisher: { '@type': 'Organization', name: ORG_NAME },
  };
}

export function getWebApplicationJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebApplication',
    name: SITE_NAME,
    description: ROUTE_SEO['/'].description,
    url: getSiteUrl(),
    inLanguage: 'en',
    applicationCategory: 'UtilitiesApplication',
    operatingSystem: 'Web',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'ILS',
    },
  };
}

export function getFaqPageJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: FAQ_ITEMS.map((item) => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: item.answer,
      },
    })),
  };
}

export function getBreadcrumbJsonLd(items) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => {
      const entry = {
        '@type': 'ListItem',
        position: index + 1,
        name: item.name,
      };
      if (item.url) {
        entry.item = item.url.startsWith('http') ? item.url : joinUrl(item.url);
      }
      return entry;
    }),
  };
}

export { ORG_EMAIL, ORG_NAME, SITE_NAME };

/** Aliases used by legal pages */
export const LEGAL_CONTACT_EMAIL = ORG_EMAIL;
export const LEGAL_CONTACT_NAME = ORG_NAME;
export const ABOUT_FAQ = FAQ_ITEMS;
