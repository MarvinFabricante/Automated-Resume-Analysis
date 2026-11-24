import React, { useEffect, useLayoutEffect, useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';

export interface PortalDropdownItem {
  id: string;
  label: React.ReactNode;
  onSelect: () => void;
  disabled?: boolean;
  active?: boolean;
  className?: string;
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
}

interface PortalDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  anchorRef: React.RefObject<HTMLElement | null>;
  items?: PortalDropdownItem[];
  children?: React.ReactNode;
  align?: 'left' | 'right';
  minWidth?: number;
  maxWidth?: number;
  matchAnchorWidth?: boolean;
  offset?: number;
  maxHeight?: number;
  className?: string;
  ariaLabel?: string;
}

const VIEWPORT_PADDING = 8;

const PortalDropdown: React.FC<PortalDropdownProps> = ({
  isOpen,
  onClose,
  anchorRef,
  items,
  children,
  align = 'left',
  minWidth = 176,
  maxWidth = 340,
  matchAnchorWidth = false,
  offset = 6,
  maxHeight = 280,
  className = '',
  ariaLabel = 'Menu',
}) => {
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [coords, setCoords] = useState<{
    top: number;
    left: number;
    width?: number;
    maxHeight: number;
    placement: 'bottom' | 'top';
    ready: boolean;
  }>({
    top: -9999,
    left: -9999,
    maxHeight,
    placement: 'bottom',
    ready: false,
  });
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);

  const computePosition = useCallback(() => {
    const anchor = anchorRef.current;
    const menu = menuRef.current;
    if (!anchor || typeof window === 'undefined') return;

    const anchorRect = anchor.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    const desiredWidth = matchAnchorWidth
      ? Math.max(anchorRect.width, minWidth)
      : Math.min(maxWidth, Math.max(minWidth, menu?.offsetWidth || minWidth));
    const clampedWidth = Math.min(desiredWidth, viewportWidth - VIEWPORT_PADDING * 2);

    const measuredHeight = menu?.scrollHeight || maxHeight;
    const spaceBelow = viewportHeight - anchorRect.bottom - offset - VIEWPORT_PADDING;
    const spaceAbove = anchorRect.top - offset - VIEWPORT_PADDING;

    const shouldFlipUp =
      spaceBelow < Math.min(measuredHeight, maxHeight) && spaceAbove > spaceBelow;

    const placement: 'bottom' | 'top' = shouldFlipUp ? 'top' : 'bottom';
    const availableVerticalSpace = Math.max(
      120,
      Math.min(maxHeight, placement === 'bottom' ? spaceBelow : spaceAbove)
    );
    const actualMenuHeight = Math.min(measuredHeight, availableVerticalSpace);

    let top =
      placement === 'bottom'
        ? anchorRect.bottom + offset
        : anchorRect.top - offset - actualMenuHeight;

    // Clamp vertically inside viewport
    top = Math.max(
      VIEWPORT_PADDING,
      Math.min(top, viewportHeight - actualMenuHeight - VIEWPORT_PADDING)
    );

    let left =
      align === 'right' ? anchorRect.right - clampedWidth : anchorRect.left;

    // Clamp horizontally inside viewport
    left = Math.max(
      VIEWPORT_PADDING,
      Math.min(left, viewportWidth - clampedWidth - VIEWPORT_PADDING)
    );

    setCoords({
      top,
      left,
      width: matchAnchorWidth ? clampedWidth : undefined,
      maxHeight: availableVerticalSpace,
      placement,
      ready: true,
    });
  }, [anchorRef, align, minWidth, maxWidth, matchAnchorWidth, offset, maxHeight]);

  // Reposition synchronously on open and whenever items/children change
  useLayoutEffect(() => {
    if (!isOpen) {
      setCoords((prev) => (prev.ready ? { ...prev, ready: false } : prev));
      setFocusedIndex(-1);
      return;
    }
    computePosition();
    const raf = window.requestAnimationFrame(computePosition);
    return () => window.cancelAnimationFrame(raf);
  }, [isOpen, computePosition, items?.length]);

  // Reposition on scroll (capture phase catches nested scrollable containers!) and resize
  useEffect(() => {
    if (!isOpen) return;
    let rafId: number | null = null;
    const handleReposition = () => {
      if (rafId !== null) return;
      rafId = window.requestAnimationFrame(() => {
        rafId = null;
        computePosition();
      });
    };
    window.addEventListener('scroll', handleReposition, true);
    window.addEventListener('resize', handleReposition);
    return () => {
      window.removeEventListener('scroll', handleReposition, true);
      window.removeEventListener('resize', handleReposition);
      if (rafId !== null) window.cancelAnimationFrame(rafId);
    };
  }, [isOpen, computePosition]);

  // Close on outside pointer down
  useEffect(() => {
    if (!isOpen) return;
    const handlePointerDown = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node | null;
      if (!target) return;
      if (menuRef.current?.contains(target)) return;
      if (anchorRef.current?.contains(target)) return;
      onClose();
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('touchstart', handlePointerDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('touchstart', handlePointerDown);
    };
  }, [isOpen, onClose, anchorRef]);

  // Keyboard navigation: Escape, ArrowUp, ArrowDown, Home, End, Enter, Tab
  useEffect(() => {
    if (!isOpen) return;
    const enabledIndices = items
      ? items
          .map((item, idx) => (item.disabled ? -1 : idx))
          .filter((idx) => idx >= 0)
      : [];

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onClose();
        anchorRef.current?.focus?.();
        return;
      }
      if (e.key === 'Tab') {
        onClose();
        return;
      }
      if (!items || enabledIndices.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setFocusedIndex((prev) => {
          const pos = enabledIndices.indexOf(prev);
          return enabledIndices[(pos + 1) % enabledIndices.length];
        });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setFocusedIndex((prev) => {
          const pos = enabledIndices.indexOf(prev);
          return pos <= 0
            ? enabledIndices[enabledIndices.length - 1]
            : enabledIndices[pos - 1];
        });
      } else if (e.key === 'Home') {
        e.preventDefault();
        setFocusedIndex(enabledIndices[0]);
      } else if (e.key === 'End') {
        e.preventDefault();
        setFocusedIndex(enabledIndices[enabledIndices.length - 1]);
      } else if (e.key === 'Enter' || e.key === ' ') {
        if (focusedIndex >= 0 && items[focusedIndex] && !items[focusedIndex].disabled) {
          e.preventDefault();
          items[focusedIndex].onSelect();
          onClose();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, items, focusedIndex, onClose, anchorRef]);

  // Focus active button when navigating via keyboard
  useEffect(() => {
    if (!isOpen || focusedIndex < 0 || !menuRef.current) return;
    const btn = menuRef.current.querySelector<HTMLButtonElement>(
      `[data-portal-item-idx="${focusedIndex}"]`
    );
    btn?.focus();
  }, [isOpen, focusedIndex]);

  if (!isOpen || typeof document === 'undefined') return null;

  const menuNode = (
    <div
      ref={menuRef}
      role="menu"
      aria-label={ariaLabel}
      data-placement={coords.placement}
      style={{
        position: 'fixed',
        top: `${coords.top}px`,
        left: `${coords.left}px`,
        minWidth: `${minWidth}px`,
        maxWidth: `min(${maxWidth}px, calc(100vw - ${VIEWPORT_PADDING * 2}px))`,
        width: coords.width ? `${coords.width}px` : undefined,
        maxHeight: `${coords.maxHeight}px`,
        zIndex: 9999,
        visibility: coords.ready ? 'visible' : 'hidden',
      }}
      className={`overflow-y-auto bg-white rounded-xl shadow-2xl border border-slate-200/90 py-1.5 text-left ${className}`}
      onClick={(e) => e.stopPropagation()}
    >
      {items
        ? items.map((item, idx) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              data-portal-item-idx={idx}
              disabled={item.disabled}
              onMouseEnter={() => {
                if (!item.disabled) setFocusedIndex(idx);
              }}
              onClick={(e) => {
                e.stopPropagation();
                if (item.disabled) return;
                item.onSelect();
                onClose();
              }}
              className={`w-full px-3.5 py-2 text-left text-xs font-semibold flex items-center justify-between gap-2 transition-colors outline-none ${
                item.disabled
                  ? 'opacity-45 cursor-not-allowed text-slate-400'
                  : 'cursor-pointer hover:bg-slate-50 focus:bg-slate-100'
              } ${item.active ? 'bg-rose-50/70 text-[#D60041] font-bold' : 'text-slate-700'} ${
                item.className || ''
              }`}
            >
              <span className="flex items-center gap-2 min-w-0 truncate">
                {item.leadingIcon}
                <span className="truncate">{item.label}</span>
              </span>
              {item.trailingIcon}
            </button>
          ))
        : children}
    </div>
  );

  return createPortal(menuNode, document.body);
};

export default PortalDropdown;
