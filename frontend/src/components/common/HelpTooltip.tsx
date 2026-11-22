import React, { useState, useRef, useEffect, useId, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { HelpCircle } from 'lucide-react';

interface HelpTooltipProps {
  content?: string;
  text?: string;
  className?: string;
  label?: string;
}

export const HelpTooltip: React.FC<HelpTooltipProps> = ({
  content,
  text,
  className = '',
  label = 'More information',
}) => {
  const message = content || text || '';
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const tooltipId = useId();

  const showTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastInteractionRef = useRef<'mouse' | 'touch' | 'pen' | 'keyboard'>('mouse');
  const lastTouchAtRef = useRef<number>(0);

  // Floating coordinates for portal rendering
  const [coords, setCoords] = useState<{
    top: number;
    left: number;
    placement: 'top' | 'bottom';
    arrowLeft: number;
  }>({
    top: 0,
    left: 0,
    placement: 'top',
    arrowLeft: 140,
  });

  const clearTimers = useCallback(() => {
    if (showTimerRef.current) {
      clearTimeout(showTimerRef.current);
      showTimerRef.current = null;
    }
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  const updatePosition = useCallback(() => {
    if (!triggerRef.current) return;
    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipEl = tooltipRef.current;

    const tooltipWidth = tooltipEl ? tooltipEl.offsetWidth : 280;
    const tooltipHeight = tooltipEl ? tooltipEl.offsetHeight : 68;
    const margin = 8;

    // Check vertical collision: if space above is less than tooltip height + margin, flip to bottom
    const fitsAbove = triggerRect.top >= tooltipHeight + margin + 4;
    const placement: 'top' | 'bottom' = fitsAbove ? 'top' : 'bottom';

    // Compute top position
    let top = placement === 'top'
      ? triggerRect.top - tooltipHeight - margin
      : triggerRect.bottom + margin;

    // Viewport clamping vertically
    top = Math.max(8, Math.min(window.innerHeight - tooltipHeight - 8, top));

    // Horizontal positioning: align center with trigger
    const triggerCenter = triggerRect.left + triggerRect.width / 2;
    let left = triggerCenter - tooltipWidth / 2;

    // Horizontal clamping: keep at least 12px from viewport edges
    const maxLeft = Math.max(12, window.innerWidth - tooltipWidth - 12);
    left = Math.max(12, Math.min(left, maxLeft));

    // Relative arrow position pointing back to the trigger center
    const arrowLeft = Math.max(16, Math.min(tooltipWidth - 16, triggerCenter - left));

    setCoords({ top, left, placement, arrowLeft });
  }, []);

  const scheduleOpen = useCallback(() => {
    clearTimers();
    showTimerRef.current = setTimeout(() => {
      setIsOpen(true);
    }, 150); // 150ms show delay
  }, [clearTimers]);

  const scheduleClose = useCallback(() => {
    clearTimers();
    hideTimerRef.current = setTimeout(() => {
      setIsOpen(false);
    }, 100); // 100ms grace period
  }, [clearTimers]);

  const cancelClose = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  // Update position whenever open state changes or DOM updates
  useEffect(() => {
    if (!isOpen) return;

    // Position immediately and again after paint to measure exact size
    updatePosition();
    const frameId = requestAnimationFrame(() => {
      updatePosition();
    });

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        clearTimers();
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };

    const handleClickOutside = (e: PointerEvent) => {
      if (
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node) &&
        tooltipRef.current &&
        !tooltipRef.current.contains(e.target as Node)
      ) {
        clearTimers();
        setIsOpen(false);
      }
    };

    const handleScrollOrResize = () => {
      updatePosition();
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('pointerdown', handleClickOutside);
    window.addEventListener('scroll', handleScrollOrResize, true);
    window.addEventListener('resize', handleScrollOrResize);

    return () => {
      cancelAnimationFrame(frameId);
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('pointerdown', handleClickOutside);
      window.removeEventListener('scroll', handleScrollOrResize, true);
      window.removeEventListener('resize', handleScrollOrResize);
    };
  }, [isOpen, updatePosition, clearTimers]);

  // Clean up timers on unmount
  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, [clearTimers]);

  if (!message) return null;

  return (
    <span className={`inline-flex items-center relative ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        aria-label={label}
        aria-describedby={isOpen ? tooltipId : undefined}
        onPointerDown={(e) => {
          const pType = (e.pointerType as 'mouse' | 'touch' | 'pen') || 'mouse';
          lastInteractionRef.current = pType;
          if (pType === 'touch') {
            lastTouchAtRef.current = Date.now();
          }
        }}
        onKeyDown={() => {
          lastInteractionRef.current = 'keyboard';
        }}
        onClick={(e) => {
          e.stopPropagation();
          clearTimers();
          setIsOpen((prev) => !prev);
        }}
        onMouseEnter={() => {
          if (lastInteractionRef.current === 'touch' || Date.now() - lastTouchAtRef.current < 500) return;
          scheduleOpen();
        }}
        onMouseLeave={() => {
          if (lastInteractionRef.current === 'touch' || Date.now() - lastTouchAtRef.current < 500) return;
          scheduleClose();
        }}
        onFocus={(e) => {
          if (lastInteractionRef.current === 'touch' || Date.now() - lastTouchAtRef.current < 500) return;
          if (lastInteractionRef.current === 'keyboard' || e.currentTarget.matches(':focus-visible')) {
            clearTimers();
            setIsOpen(true);
          }
        }}
        onBlur={() => {
          if (lastInteractionRef.current === 'touch' || Date.now() - lastTouchAtRef.current < 500) return;
          scheduleClose();
        }}
        className="text-slate-400 hover:text-slate-600 focus:text-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D10043]/40 rounded-full min-w-[44px] min-h-[44px] -m-2.5 p-2.5 transition-colors cursor-pointer touch-manipulation inline-flex items-center justify-center"
      >
        <HelpCircle size={14} className="shrink-0" aria-hidden="true" />
      </button>

      {isOpen && typeof document !== 'undefined' && createPortal(
        <div
          ref={tooltipRef}
          id={tooltipId}
          role="tooltip"
          onMouseEnter={cancelClose}
          onMouseLeave={scheduleClose}
          style={{
            position: 'fixed',
            top: `${coords.top}px`,
            left: `${coords.left}px`,
            width: '280px',
            maxWidth: 'calc(100vw - 24px)',
            zIndex: 99999,
          }}
          className="p-3 bg-slate-900 text-white text-[11px] sm:text-xs leading-relaxed font-normal rounded-xl shadow-2xl border border-slate-700/80 pointer-events-auto transition-opacity duration-150 motion-reduce:transition-none"
        >
          {message}
          {/* Visual Pointer / Arrow */}
          <span
            aria-hidden="true"
            style={{ left: `${coords.arrowLeft}px` }}
            className={`absolute -translate-x-1/2 border-4 border-transparent pointer-events-none ${
              coords.placement === 'top'
                ? 'top-full border-t-slate-900'
                : 'bottom-full border-b-slate-900'
            }`}
          />
        </div>,
        document.body
      )}
    </span>
  );
};

export default HelpTooltip;
