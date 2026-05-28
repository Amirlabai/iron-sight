import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { HelmetProvider } from 'react-helmet-async';
import { registerSW } from 'virtual:pwa-register';
import './index.css';
import './components/AccessibilityToolbar.css';
import { initThemeFromStorage } from './hooks/useThemeMode';
import { initHighContrastFromStorage } from './hooks/useHighContrast';
import App from './App.jsx';

initThemeFromStorage();
initHighContrastFromStorage();

function isStandalonePwa() {
  return (
    window.matchMedia('(display-mode: standalone)').matches
    || window.navigator.standalone === true
  );
}

registerSW({
  immediate: true,
  onNeedRefresh() {
    if (!isStandalonePwa()) return;
    if (sessionStorage.getItem('iron_sight_sw_reload')) return;
    sessionStorage.setItem('iron_sight_sw_reload', '1');
    window.location.reload();
  },
});

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HelmetProvider>
      <App />
    </HelmetProvider>
  </StrictMode>,
);
