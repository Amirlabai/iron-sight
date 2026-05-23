import { renderToString } from 'react-dom/server';
import { Helmet } from 'react-helmet-async';
import { StaticRouter } from 'react-router-dom';
import { getRouteSeo, FAQ_ITEMS } from './config/seoConfig';

function PrerenderShell({ pathname, children, noindex = false }) {
  const seo = getRouteSeo(pathname);
  return (
    <>
      <Helmet>
        <title>{seo.title}</title>
        <meta name="description" content={seo.description} />
        <meta name="keywords" content={seo.keywords} />
        <link rel="canonical" href={seo.canonical} />
        {noindex ? <meta name="robots" content="noindex, nofollow" /> : null}
      </Helmet>
      <div className="legal-page-shell">
        <main id="legal-main" className="legal-page-main">
          {children}
        </main>
      </div>
    </>
  );
}

function AboutPrerender() {
  return (
    <PrerenderShell pathname="/about">
      <h1>About Iron Sight</h1>
      <p>
        Iron Sight is a web-based tactical map for real-time and historical alert-related events over
        Israel.
      </p>
      <h2>Frequently asked questions</h2>
      {FAQ_ITEMS.map((item) => (
        <section key={item.question}>
          <h3>{item.question}</h3>
          <p>{item.answer}</p>
        </section>
      ))}
    </PrerenderShell>
  );
}

function NotFoundPrerender() {
  return (
    <PrerenderShell pathname="/" noindex>
      <h1>Page not found</h1>
      <p>The page you requested does not exist.</p>
      <p>
        <a href="/">Return to dashboard</a>
      </p>
    </PrerenderShell>
  );
}

function LegalStub({ pathname, title }) {
  const seo = getRouteSeo(pathname);
  return (
    <PrerenderShell pathname={pathname}>
      <h1>{title}</h1>
      <p>{seo.description}</p>
    </PrerenderShell>
  );
}

const ROUTES = {
  '/about': AboutPrerender,
  '/accessibility': () => <LegalStub pathname="/accessibility" title="Accessibility Statement" />,
  '/privacy': () => <LegalStub pathname="/privacy" title="Privacy Policy" />,
  '/terms': () => <LegalStub pathname="/terms" title="Terms of Use" />,
};

export async function prerender(data) {
  const url = data?.url ?? '/';
  const pathname = url.replace(/\/?$/, '') || '/';
  const normalized = pathname.startsWith('/') ? pathname : `/${pathname}`;
  const Page = ROUTES[normalized] || NotFoundPrerender;
  const html = renderToString(
    <StaticRouter location={normalized}>
      <Page />
    </StaticRouter>,
  );
  return { html };
}
