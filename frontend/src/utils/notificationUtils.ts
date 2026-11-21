/**
 * Utility functions for parsing and accurately formatting notification timestamps.
 * Ensures timestamps originating from naive UTC storage are correctly parsed into
 * the user's local timezone and accurately formatted with high-contrast, human-readable labels.
 */

/**
 * Parses a notification date string into a Date object.
 * If the string has no timezone indicator (naive UTC from PostgreSQL/FastAPI),
 * it appends 'Z' to prevent browsers from misinterpreting it as local time.
 */
export const parseNotificationDate = (dateVal?: string | Date | null): Date => {
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

export interface FormattedNotificationTime {
  date: Date;
  relativeTime: string;
  timeStr: string;
  dateStr: string;
  displayDateTime: string;
  fullDateTime: string;
}

/**
 * Formats a notification date into accurate relative and calendar representations.
 */
export const formatNotificationTime = (dateVal?: string | Date | null): FormattedNotificationTime => {
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

export const isMessageNotification = (notif?: {
  type?: string | null;
  tag?: string | null;
  title?: string | null;
} | null): boolean => {
  if (!notif) return false;
  const type = String(notif.type || '').trim().toLowerCase();
  const tag = String(notif.tag || '').trim().toLowerCase();
  const title = String(notif.title || '').trim().toLowerCase();
  return (
    type === 'message' ||
    type === 'chat' ||
    tag === 'message' ||
    title.startsWith('new message')
  );
};

export const getMessagesPathForRole = (userRole?: string | null, pathname: string = ''): string => {
  const normRole = String(userRole || '').trim().toUpperCase();
  if (normRole === 'ADMIN') return '/admin/messages';
  if (normRole === 'HR' || pathname.startsWith('/hr')) return '/hr/messages';
  return '/candidate/messages';
};

export const extractMessageSenderHint = (notif?: {
  desc?: string | null;
  message?: string | null;
} | null): string => {
  const raw = String(notif?.desc || notif?.message || '').replace(/^\[Sender:[^\]]+\]\s*/i, '').trim();
  if (!raw) return '';
  const colonIdx = raw.indexOf(':');
  if (colonIdx > 0 && colonIdx <= 60) {
    return raw.slice(0, colonIdx).trim();
  }
  return '';
};

export const formatRawNotification = (n: any, userRole?: string | null) => {
  const normRole = String(userRole || '').trim().toUpperCase();
  const isCandidateRole = normRole === 'CANDIDATE';
  const isAdminRole = normRole === 'ADMIN';

  let iconName = isCandidateRole ? 'Briefcase' : 'AlertCircle';
  let bgColor = isCandidateRole ? 'bg-blue-50' : 'bg-slate-50';
  let textColor = isCandidateRole ? 'text-blue-600' : 'text-slate-600';
  let tag: string | null = isCandidateRole ? 'Update' : null;
  let tagColor: string | null = isCandidateRole ? 'bg-blue-100 text-blue-700' : null;

  if (isCandidateRole) {
    if (n.type === 'schedule') {
      iconName = 'MessageSquare';
      bgColor = 'bg-pink-50';
      textColor = 'text-[#D60041]';
      tag = 'Interview';
      tagColor = 'bg-pink-100 text-[#D60041]';
    } else if (n.type === 'job') {
      iconName = 'TrendingUp';
      bgColor = 'bg-green-50';
      textColor = 'text-green-600';
      tag = 'Match';
      tagColor = 'bg-green-100 text-green-700';
    } else if (n.type === 'message' || n.type === 'chat') {
      iconName = 'MessageSquare';
      bgColor = 'bg-blue-50';
      textColor = 'text-blue-600';
      tag = 'Message';
      tagColor = 'bg-blue-100 text-blue-700';
    } else if (n.type === 'application_update') {
      if (n.title?.includes('Accepted') || n.title?.includes('🎉')) {
        bgColor = 'bg-emerald-50';
        textColor = 'text-emerald-600';
        tag = 'Accepted';
        tagColor = 'bg-emerald-100 text-emerald-700';
      } else if (
        n.title?.includes('Rejected') ||
        n.message?.includes('regret') ||
        n.message?.includes('other candidates') ||
        n.desc?.includes('regret') ||
        n.desc?.includes('other candidates')
      ) {
        bgColor = 'bg-rose-50';
        textColor = 'text-rose-600';
        tag = 'Rejected';
        tagColor = 'bg-rose-100 text-rose-700';
      } else {
        bgColor = 'bg-pink-50';
        textColor = 'text-[#D60041]';
        tag = 'Update';
        tagColor = 'bg-pink-100 text-[#D60041]';
      }
    }
  } else {
    if (n.type === 'registration') {
      iconName = 'UserPlus';
      bgColor = 'bg-blue-50';
      textColor = 'text-blue-600';
    } else if (n.type === 'application' || n.type === 'application_update') {
      iconName = 'Briefcase';
      bgColor = 'bg-pink-50';
      textColor = 'text-[#D60041]';
      tag = 'Update';
      tagColor = 'bg-pink-100 text-[#D60041]';
    } else if (n.type === 'upload') {
      iconName = 'FileText';
      bgColor = 'bg-orange-50';
      textColor = 'text-orange-600';
    } else if (n.type === 'hr_registration') {
      iconName = 'ShieldCheck';
      bgColor = 'bg-indigo-50';
      textColor = 'text-indigo-600';
      tag = 'System';
      tagColor = 'bg-indigo-100 text-indigo-700';
    } else if (n.type === 'job_creation') {
      iconName = 'Zap';
      bgColor = 'bg-green-50';
      textColor = 'text-green-600';
    } else if (n.type === 'job_update') {
      iconName = 'Edit3';
      bgColor = 'bg-amber-50';
      textColor = 'text-amber-600';
    } else if (n.type === 'candidate_login') {
      iconName = 'Radio';
      bgColor = 'bg-green-50';
      textColor = 'text-green-600';
    } else if (n.type === 'hr_login') {
      iconName = 'Radio';
      bgColor = 'bg-purple-50';
      textColor = 'text-purple-600';
    } else if (n.type === 'message' || n.type === 'chat') {
      iconName = 'MessageSquare';
      bgColor = 'bg-blue-50';
      textColor = 'text-blue-600';
      tag = 'Message';
      tagColor = 'bg-blue-100 text-blue-700';
    }
  }

  const timeInfo = formatNotificationTime(n.created_at || new Date());
  const rawMessage = n.message ?? n.desc ?? '';
  const desc = isAdminRole && n.sender_role ? `[Sender: ${n.sender_role}] ${rawMessage}` : rawMessage;

  return {
    id: n.id,
    title: n.title,
    message: rawMessage,
    desc,
    sender_role: n.sender_role,
    time: timeInfo.relativeTime,
    relativeTime: timeInfo.relativeTime,
    timeStr: timeInfo.timeStr,
    dateStr: timeInfo.dateStr,
    displayDateTime: timeInfo.displayDateTime,
    fullDateTime: timeInfo.fullDateTime,
    createdAt: timeInfo.date,
    type: n.type,
    icon: iconName,
    bgColor,
    textColor,
    tag,
    tagColor,
    read: Boolean(n.is_read ?? n.read ?? false),
  };
};
