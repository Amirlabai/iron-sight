import { useEffect, useState } from 'react';

/** Window + visualViewport dimensions for responsive layout (sidebar sheet, etc.). */
export function useViewportSize() {
  const [viewport, setViewport] = useState(() => ({
    width: window.innerWidth,
    height: window.innerHeight,
  }));

  useEffect(() => {
    const onResize = () => {
      setViewport({ width: window.innerWidth, height: window.innerHeight });
    };
    window.addEventListener('resize', onResize);
    window.addEventListener('orientationchange', onResize);
    const vv = window.visualViewport;
    const onVisualViewport = () => {
      const w = Math.round(vv?.width ?? window.innerWidth);
      const h = Math.round(vv?.height ?? window.innerHeight);
      setViewport((prev) => (prev.width === w && prev.height === h ? prev : { width: w, height: h }));
    };
    vv?.addEventListener('resize', onVisualViewport);
    vv?.addEventListener('scroll', onVisualViewport);
    return () => {
      window.removeEventListener('resize', onResize);
      window.removeEventListener('orientationchange', onResize);
      vv?.removeEventListener('resize', onVisualViewport);
      vv?.removeEventListener('scroll', onVisualViewport);
    };
  }, []);

  return viewport;
}
