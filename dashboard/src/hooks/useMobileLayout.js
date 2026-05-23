import { useEffect, useState } from 'react';
import { MOBILE_LAYOUT_BREAKPOINT } from '../utils/constants';

const mobileQuery = () =>
  typeof window !== 'undefined' &&
  window.matchMedia(`(max-width: ${MOBILE_LAYOUT_BREAKPOINT}px)`).matches;

export function useMobileLayout() {
  const [isMobile, setIsMobile] = useState(mobileQuery);

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_LAYOUT_BREAKPOINT}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    update();
    return () => mq.removeEventListener('change', update);
  }, []);

  return isMobile;
}
