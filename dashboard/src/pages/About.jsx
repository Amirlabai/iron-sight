import { Link } from 'react-router-dom';
import LegalPageLayout from '../components/LegalPageLayout';
import { ABOUT_FAQ } from '../config/seoConfig';

export default function About() {
  return (
    <LegalPageLayout
      pathname="/about"
      breadcrumbs={[{ name: 'About', url: '/about' }]}
      seoExtras={{ includeFaq: true }}
    >
      <h1>About Iron Sight</h1>
      <p className="legal-updated">Last updated: May 2026</p>

      <p>
        Iron Sight is a web-based tactical map for real-time and historical alert-related events over
        Israel. It helps users visualize rockets, drones, and related threats on an interactive map with
        archive and timeframe views.
      </p>

      <h2>What you can do</h2>
      <ul>
        <li>View live alert activity on a tactical map</li>
        <li>Browse historical events and time ranges</li>
        <li>Opt in to browser push notifications and location-based preferences</li>
        <li>Install the app as a Progressive Web App (PWA) on supported devices</li>
      </ul>

      <h2>Important disclaimer</h2>
      <p>
        Iron Sight is <strong>independent community tooling</strong>. It is not affiliated with or
        endorsed by the Israel Defense Forces, Home Front Command, or any government agency. Always
        follow official instructions from authorized sources during emergencies.
      </p>

      <h2>Open the map</h2>
      <p>
        <Link to="/">Go to the live tactical dashboard</Link>
      </p>

      <h2>Frequently asked questions</h2>
      {ABOUT_FAQ.map((item) => (
        <section key={item.question}>
          <h3>{item.question}</h3>
          <p>{item.answer}</p>
        </section>
      ))}

      <h2>Legal</h2>
      <p>
        <Link to="/privacy">Privacy Policy</Link> · <Link to="/terms">Terms of Use</Link> ·{' '}
        <Link to="/accessibility">Accessibility Statement</Link>
      </p>
    </LegalPageLayout>
  );
}
