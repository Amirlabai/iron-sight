import LegalPageLayout from '../components/LegalPageLayout';
import { LEGAL_CONTACT_EMAIL, LEGAL_CONTACT_NAME, joinUrl } from '../config/seoConfig';

export default function Terms() {
  return (
    <LegalPageLayout pathname="/terms" breadcrumbs={[{ name: 'Terms of Use', url: '/terms' }]}>
      <h1>Terms of Use</h1>
      <p className="legal-updated">Last updated: May 2026</p>

      <p>
        By using Iron Sight ({joinUrl('/')}), you agree to these terms. If you do not agree, do not use
        the site.
      </p>

      <h2>1. Site purpose</h2>
      <p>
        Iron Sight provides a free tactical map for awareness of alert-related events. It is not an
        official government service and does not replace official emergency instructions.
      </p>

      <h2>2. Acceptable use</h2>
      <ul>
        <li>Do not attempt to breach, scrape, or overload our systems</li>
        <li>Do not use the service for unlawful purposes</li>
        <li>Do not misrepresent affiliation with Iron Sight or any government body</li>
      </ul>

      <h2>3. Intellectual property</h2>
      <p>
        The application interface, branding, and presentation are owned by the operator. Third-party
        data and map tiles remain subject to their respective licenses.
      </p>

      <h2>4. No professional advice</h2>
      <p>
        All information is provided for general awareness only. You are solely responsible for decisions
        you make based on the map or notifications.
      </p>

      <h2>5. Limitation of liability</h2>
      <p>
        The service is provided &quot;as is.&quot; We do not guarantee completeness, accuracy, or
        timeliness of alerts. We are not liable for any direct or indirect damages arising from use or
        inability to use the service, including missed or delayed alerts.
      </p>

      <h2>6. Third-party services</h2>
      <p>
        The site relies on upstream alert sources, hosting providers, and analytics. We are not
        responsible for third-party outages or policies.
      </p>

      <h2>7. External links</h2>
      <p>Links to external sites are provided for convenience. We do not control their content.</p>

      <h2>8. Changes</h2>
      <p>We may update these terms. Continued use after publication constitutes acceptance.</p>

      <h2>9. Governing law</h2>
      <p>
        These terms are governed by the laws of the State of Israel. Exclusive jurisdiction for disputes
        lies with the competent courts in Tel Aviv-Yafo.
      </p>

      <h2>10. Contact</h2>
      <p>
        {LEGAL_CONTACT_NAME}
        <br />
        <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a>
      </p>
    </LegalPageLayout>
  );
}
