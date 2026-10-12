/**
 * Utility functions for parsing and accurately formatting notification timestamps.
 * Ensures timestamps originating from naive UTC storage are correctly parsed into
 * the user's local timezone and accurately formatted with high-contrast, human-readable labels.
 */

/**
 * Parses a notification date string into a Date object.
 * If the string has no timezone indicator (naive UTC from PostgreSQL/FastAPI),
 * it appends 'Z' to prevent browsers from misinterpreting it as local time.
 * 
 * @param {string|Date} dateVal 
 * @returns {Date}
 */
export const parseNotificationDate = (dateVal) => {
  if (!dateVal) return new Date();
  if (dateVal instanceof Date) return dateVal;
  
  let s = String(dateVal).trim();
  // If naive ISO string (e.g. "2026-10-12T05:50:57.689" or "2026-10-12 05:50:57")
  if (!s.endsWith('Z') && !/[+-]\d{2}(:\d{2})?$/.test(s)) {
    s = s.replace(' ', 'T') + 'Z';
  }
  
  const d = new Date(s);
  return isNaN(d.getTime()) ? new Date(dateVal) : d;
};

/**
 * Formats a notification date into accurate relative and calendar representations.
 * 
 * @param {string|Date} dateVal 
 * @returns {{
 *   date: Date,
 *   relativeTime: string,
 *   timeStr: string,
 *   dateStr: string,
 *   displayDateTime: string,
 *   fullDateTime: string
 * }}
 */
export const formatNotificationTime = (dateVal) => {
  const d = parseNotificationDate(dateVal);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  // Relative time representation
  let relativeTime = 'Just now';
  if (diffSec >= 60 && diffSec < 3600) {
    relativeTime = `${Math.floor(diffSec / 60)}m ago`;
  } else if (diffSec >= 3600 && diffSec < 86400) {
    relativeTime = `${Math.floor(diffSec / 3600)}h ago`;
  } else if (diffSec >= 86400 && diffSec < 604800) {
    relativeTime = `${Math.floor(diffSec / 86400)}d ago`;
  } else if (diffSec >= 604800) {
    relativeTime = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  // Local 12-hour time (e.g. "1:50 PM")
  const timeStr = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  // Local calendar date (e.g. "Oct 12, 2026")
  const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  
  const isToday = d.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday = d.toDateString() === yesterday.toDateString();

  let displayDateTime = `${dateStr} • ${timeStr}`;
  if (isToday) {
    displayDateTime = `Today, ${timeStr}`;
  } else if (isYesterday) {
    displayDateTime = `Yesterday, ${timeStr}`;
  }

  const fullDateTime = d.toLocaleString('en-US', { 
    month: 'short', day: 'numeric', year: 'numeric', 
    hour: 'numeric', minute: '2-digit', hour12: true 
  });

  return {
    date: d,
    relativeTime,
    timeStr,
    dateStr,
    displayDateTime,
    fullDateTime
  };
};
