import { useState } from 'react';
import LegalPageLayout from '../components/LegalPageLayout';
import { LEGAL_CONTACT_EMAIL, LEGAL_CONTACT_NAME, joinUrl } from '../config/seoConfig';

export default function Accessibility() {
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    const form = e.target;
    const name = form.name.value;
    const email = form.email.value;
    const message = form.message.value;
    const subject = encodeURIComponent('Accessibility report — Iron Sight');
    const body = encodeURIComponent(`Name: ${name}\nEmail: ${email}\n\n${message}`);
    window.location.href = `mailto:${LEGAL_CONTACT_EMAIL}?subject=${subject}&body=${body}`;
    setSubmitted(true);
  };

  return (
    <LegalPageLayout
      pathname="/accessibility"
      breadcrumbs={[{ name: 'Accessibility', url: '/accessibility' }]}
    >
      <h1>Accessibility Statement</h1>
      <p className="legal-updated">Last reviewed: May 2026</p>

      <h2>Conformance target</h2>
      <p>
        This site aims to meet the requirements of Israeli Standard IS 5568 for web accessibility,
        which adopts WCAG 2.1 Level AA. We are continually improving keyboard access, contrast, and
        screen reader support.
      </p>

      <h2>Accessibility features</h2>
      <ul>
        <li>Skip link to main content on legal pages and the tactical dashboard</li>
        <li>High contrast mode toggle (fixed overlay, bottom-left of the screen)</li>
        <li>Visible focus indicators on interactive controls</li>
        <li>ARIA labels on primary tactical controls</li>
        <li>Respect for prefers-reduced-motion where animations are used</li>
      </ul>

      <h2>Known limitations</h2>
      <ul>
        <li>
          <strong>Map (Leaflet):</strong> The live map is partially accessible. Zone shapes and pins
          may not be fully available to all assistive technologies. Text summaries appear in the
          sidebar where possible.
        </li>
        <li>Third-party fonts (Google Fonts) and icon libraries loaded from CDNs</li>
        <li>Browser push and geolocation depend on your device and browser</li>
        <li>Vercel Analytics (only after cookie consent)</li>
      </ul>

      <h2>Accessibility coordinator</h2>
      <p>
        <strong>{LEGAL_CONTACT_NAME}</strong>
        <br />
        Email:{' '}
        <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a>
      </p>

      <h2>Report an accessibility issue</h2>
      {submitted ? (
        <p role="status">Thank you. Your email client should open with your message.</p>
      ) : (
        <form onSubmit={handleSubmit} className="a11y-report-form">
          <p>
            <label htmlFor="a11y-name">
              Name
              <input id="a11y-name" name="name" type="text" required autoComplete="name" />
            </label>
          </p>
          <p>
            <label htmlFor="a11y-email">
              Email
              <input id="a11y-email" name="email" type="email" required autoComplete="email" />
            </label>
          </p>
          <p>
            <label htmlFor="a11y-message">
              Description of the issue
              <textarea id="a11y-message" name="message" rows={5} required />
            </label>
          </p>
          <button type="submit">Send report via email</button>
        </form>
      )}
    </LegalPageLayout>
  );
}
