import LegalPageLayout from '../components/LegalPageLayout';
import { LEGAL_CONTACT_EMAIL, LEGAL_CONTACT_NAME, joinUrl } from '../config/seoConfig';

export default function Privacy() {
  return (
    <LegalPageLayout
      pathname="/privacy"
      breadcrumbs={[{ name: 'Privacy Policy', url: '/privacy' }]}
    >
      <h1>Privacy Policy</h1>
      <p className="legal-updated">Last updated: May 2026</p>

      <p>
        This policy explains how Iron Sight ({joinUrl('/')}) collects and uses information when you use
        the service.
      </p>

      <h2>1. Information we collect</h2>
      <ul>
        <li>
          <strong>Optional geolocation</strong> — only if you grant permission in your browser for
          location-based alert preferences.
        </li>
        <li>
          <strong>Push notification subscription</strong> — if you opt in to browser notifications.
        </li>
        <li>
          <strong>Local preferences</strong> — alert scope, onboarding state, high-contrast mode, and
          cookie consent stored in your browser (localStorage).
        </li>
        <li>
          <strong>Technical usage</strong> — Vercel Analytics (aggregated, after you accept cookies).
        </li>
        <li>
          <strong>Server-side data</strong> — alert history and related tactical data processed by our
          API for map display and archives.
        </li>
      </ul>

      <h2>2. How we use information</h2>
      <ul>
        <li>Display alerts and map data</li>
        <li>Deliver notifications you requested</li>
        <li>Improve reliability and performance</li>
        <li>Comply with legal obligations</li>
      </ul>

      <h2>3. Third-party services</h2>
      <ul>
        <li>Vercel — hosting and analytics</li>
        <li>Render — API backend</li>
        <li>MongoDB Atlas — data storage</li>
        <li>Google Fonts — typography (CDN)</li>
        <li>Your browser — push and geolocation APIs</li>
      </ul>

      <h2>4. Retention</h2>
      <p>
        Alert history may be retained on our servers for operational and archive purposes. Local
        browser data remains until you clear it or uninstall the PWA.
      </p>

      <h2>5. Security</h2>
      <p>
        We use HTTPS and reasonable safeguards. No method of transmission over the Internet is 100%
        secure.
      </p>

      <h2>6. Your rights</h2>
      <p>
        Under the Israeli Privacy Protection Law, you may request access, correction, or deletion of
        personal data we hold about you. Contact us at the email below.
      </p>

      <h2 id="cookies">7. Cookies and similar technologies</h2>
      <p>
        The cookie notice appears on the live tactical map only (not on legal or informational pages). We
        use cookies and local storage for: (a) remembering your cookie consent choice; (b) alert and UI
        preferences; (c) Vercel Analytics only after you click Accept (not when you choose Essential
        only). You can clear site data in your browser settings.
      </p>

      <h2>8. Policy updates</h2>
      <p>We may update this policy. The &quot;Last updated&quot; date will change when we do.</p>

      <h2>9. Contact</h2>
      <p>
        {LEGAL_CONTACT_NAME}
        <br />
        <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a>
      </p>
    </LegalPageLayout>
  );
}
