import { Link } from 'react-router-dom';
import LegalPageLayout from '../components/LegalPageLayout';
import { joinUrl } from '../config/seoConfig';

export default function NotFound() {
  return (
    <LegalPageLayout
      pathname="/"
      breadcrumbs={[{ name: 'Page not found' }]}
      seoExtras={{
        noindex: true,
        title: 'Page not found | IRON SIGHT',
        description: 'The requested page was not found on Iron Sight.',
        url: joinUrl('/404'),
      }}
    >
      <h1>Page not found</h1>
      <p>The page you requested does not exist.</p>
      <p>
        <Link to="/">Return to dashboard</Link> · <Link to="/about">About</Link>
      </p>
    </LegalPageLayout>
  );
}
