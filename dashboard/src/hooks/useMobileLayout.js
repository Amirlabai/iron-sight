import { useEffect, useState } from 'react';
import { MOBILE_LAYOUT_BREAKPOINT } from '../utils/constants';

export function useMobileLayout() {
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== 'undefined' && window.innerWidth <= MOBILE_LAYOUT_BREAKPOINT,
  );

  useEffect(() => {
    const update = () => setIsMobile(window.innerWidth <= MOBILE_LAYOUT_BREAKPOINT);
    window.addEventListener('resize', update);
    window.addEventListener('orientationchange', update);
    update();
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('orientationchange', update);
    };
  }, []);

  return isMobile;
}
