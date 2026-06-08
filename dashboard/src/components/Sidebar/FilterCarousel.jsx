import React from 'react';

const TIMEFRAME_PRESET_IDS = ['all', '1', '12', '24'];
const DRAG_CLICK_THRESHOLD_PX = 6;

function prefersReducedMotion() {
  return typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function isTimeframePreset(value) {
  return TIMEFRAME_PRESET_IDS.includes(value);
}

export default function FilterCarousel({
  className = '',
  value,
  onChange,
  items,
  getItemKey = (item) => item.id,
  getItemValue = (item) => item.id,
  renderItem,
  ariaLabel,
  enabled = true,
}) {
  const scrollerRef = React.useRef(null);
  const itemRefs = React.useRef(new Map());
  const didInitialScrollRef = React.useRef(false);
  const isDraggingRef = React.useRef(false);
  const dragRef = React.useRef({
    active: false,
    moved: false,
    pointerId: null,
    startX: 0,
    startScrollLeft: 0,
  });
  const suppressClickRef = React.useRef(false);

  const setItemRef = (key) => (el) => {
    if (el) itemRefs.current.set(key, el);
    else itemRefs.current.delete(key);
  };

  const updateEdgePadding = React.useCallback(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    scroller.style.setProperty('--carousel-edge-pad', `${scroller.clientWidth / 2}px`);
  }, []);

  const scrollToValue = React.useCallback((targetValue, behavior = 'auto') => {
    const scroller = scrollerRef.current;
    if (!scroller || targetValue == null) return;
    const item = items.find((entry) => getItemValue(entry) === targetValue);
    if (!item) return;
    const el = itemRefs.current.get(getItemKey(item));
    if (!el) return;

    const targetLeft = el.offsetLeft - (scroller.clientWidth - el.offsetWidth) / 2;
    scroller.scrollTo({ left: Math.max(0, targetLeft), behavior });
  }, [items, getItemKey, getItemValue]);

  const findCenteredValue = React.useCallback(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return null;
    const center = scroller.scrollLeft + scroller.clientWidth / 2;
    let closest = null;
    let minDist = Infinity;
    for (const item of items) {
      const key = getItemKey(item);
      const el = itemRefs.current.get(key);
      if (!el) continue;
      const itemCenter = el.offsetLeft + el.offsetWidth / 2;
      const dist = Math.abs(itemCenter - center);
      if (dist < minDist) {
        minDist = dist;
        closest = getItemValue(item);
      }
    }
    return closest;
  }, [items, getItemKey, getItemValue]);

  const settleAfterUserScroll = React.useCallback(() => {
    const centered = findCenteredValue();
    if (centered == null || value == null) return;
    if (centered !== value) {
      onChange(centered);
    }
  }, [findCenteredValue, onChange, value]);

  React.useEffect(() => {
    if (!enabled) return undefined;
    const scroller = scrollerRef.current;
    if (!scroller) return undefined;

    updateEdgePadding();
    const ro = new ResizeObserver(() => {
      const activeValue = value ?? findCenteredValue();
      updateEdgePadding();
      if (activeValue != null) {
        requestAnimationFrame(() => scrollToValue(activeValue, 'auto'));
      }
    });
    ro.observe(scroller);
    return () => ro.disconnect();
  }, [enabled, findCenteredValue, scrollToValue, updateEdgePadding, value]);

  React.useEffect(() => {
    if (!enabled || didInitialScrollRef.current) return undefined;
    const frame = requestAnimationFrame(() => {
      if (value != null) {
        scrollToValue(value, 'auto');
      } else {
        scrollerRef.current?.scrollTo({ left: 0, behavior: 'auto' });
      }
      didInitialScrollRef.current = true;
    });
    return () => cancelAnimationFrame(frame);
  }, [enabled, scrollToValue, value]);

  React.useEffect(() => {
    if (!enabled || !didInitialScrollRef.current || isDraggingRef.current) return;
    if (value == null) return;
    scrollToValue(value, prefersReducedMotion() ? 'auto' : 'smooth');
  }, [enabled, value, scrollToValue]);

  React.useEffect(() => {
    if (!enabled) return undefined;
    const scroller = scrollerRef.current;
    if (!scroller) return undefined;

    const onScrollEnd = () => {
      if (isDraggingRef.current) return;
      settleAfterUserScroll();
    };

    scroller.addEventListener('scrollend', onScrollEnd);
    return () => scroller.removeEventListener('scrollend', onScrollEnd);
  }, [enabled, settleAfterUserScroll]);

  const handlePointerDown = (event) => {
    if (!enabled || event.pointerType === 'mouse' && event.button !== 0) return;
    const scroller = scrollerRef.current;
    if (!scroller) return;

    isDraggingRef.current = true;
    dragRef.current = {
      active: true,
      moved: false,
      pointerId: event.pointerId,
      startX: event.clientX,
      startScrollLeft: scroller.scrollLeft,
    };
    scroller.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event) => {
    const drag = dragRef.current;
    if (!drag.active || drag.pointerId !== event.pointerId) return;

    const deltaX = event.clientX - drag.startX;
    if (Math.abs(deltaX) > DRAG_CLICK_THRESHOLD_PX) {
      drag.moved = true;
    }

    const scroller = scrollerRef.current;
    if (!scroller) return;
    scroller.scrollLeft = drag.startScrollLeft - deltaX;
  };

  const finishPointerDrag = (event) => {
    const drag = dragRef.current;
    if (!drag.active || drag.pointerId !== event.pointerId) return;

    const scroller = scrollerRef.current;
    if (scroller?.hasPointerCapture(event.pointerId)) {
      scroller.releasePointerCapture(event.pointerId);
    }

    const wasMoved = drag.moved;
    drag.active = false;
    drag.moved = false;
    isDraggingRef.current = false;

    if (wasMoved) {
      suppressClickRef.current = true;
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 0);
      settleAfterUserScroll();
      return;
    }

    isDraggingRef.current = false;
  };

  const handleItemClick = (itemValue) => {
    if (suppressClickRef.current) return;
    onChange(itemValue);
    if (enabled) {
      scrollToValue(itemValue, prefersReducedMotion() ? 'auto' : 'smooth');
    }
  };

  if (!enabled) {
    return (
      <div className={className} role="group" aria-label={ariaLabel}>
        {items.map((item) => {
          const itemValue = getItemValue(item);
          const key = getItemKey(item);
          const isSelected = itemValue === value;
          return (
            <React.Fragment key={key}>
              {renderItem(item, {
                isSelected,
                onSelect: () => handleItemClick(itemValue),
              })}
            </React.Fragment>
          );
        })}
      </div>
    );
  }

  return (
    <div className={`filter-carousel-wrap ${className}`.trim()}>
      <div className="filter-carousel-fade filter-carousel-fade--left" aria-hidden="true" />
      <div
        ref={scrollerRef}
        className="filter-carousel"
        role="listbox"
        aria-label={ariaLabel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishPointerDrag}
        onPointerCancel={finishPointerDrag}
      >
        <div className="filter-carousel__edge" aria-hidden="true" />
        {items.map((item) => {
          const itemValue = getItemValue(item);
          const key = getItemKey(item);
          const isSelected = itemValue === value;
          return (
            <div
              key={key}
              ref={setItemRef(key)}
              className="filter-carousel__slot"
              role="presentation"
            >
              {renderItem(item, {
                isSelected,
                onSelect: () => handleItemClick(itemValue),
              })}
            </div>
          );
        })}
        <div className="filter-carousel__edge" aria-hidden="true" />
      </div>
      <div className="filter-carousel-fade filter-carousel-fade--right" aria-hidden="true" />
    </div>
  );
}
