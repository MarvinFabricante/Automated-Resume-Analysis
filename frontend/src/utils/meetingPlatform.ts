export const MEETING_PLATFORMS = [
  'Google Meet',
  'Zoom',
  'Microsoft Teams',
  'Other',
] as const;

export type MeetingPlatform = (typeof MEETING_PLATFORMS)[number];
export type KnownMeetingPlatform = Exclude<MeetingPlatform, 'Other'>;

export const KNOWN_MEETING_PLATFORMS: readonly KnownMeetingPlatform[] = [
  'Google Meet',
  'Zoom',
  'Microsoft Teams',
];

export const PLATFORM_PLACEHOLDERS: Record<MeetingPlatform | '', string> = {
  '': 'https://meet.google.com/... or https://zoom.us/j/...',
  'Google Meet': 'https://meet.google.com/abc-defg-hij',
  'Zoom': 'https://zoom.us/j/1234567890',
  'Microsoft Teams': 'https://teams.microsoft.com/l/meetup-join/...',
  'Other': 'https://...',
};

function parseValidHttpsUrl(value: string): { url: URL; host: string; path: string } | null {
  const trimmed = (value || '').trim();
  if (!trimmed || !trimmed.startsWith('https://') || /\s/.test(trimmed)) {
    return null;
  }
  try {
    const url = new URL(trimmed);
    const host = (url.hostname || '').toLowerCase().replace(/\.$/, '');
    if (!host || url.username || url.port === '0') {
      return null;
    }
    const labels = host.split('.');
    if (labels.length < 2 || labels.some((label) => !label)) {
      return null;
    }
    return { url, host, path: (url.pathname || '').toLowerCase() };
  } catch {
    return null;
  }
}

export function validMeetingLink(value: string): boolean {
  return parseValidHttpsUrl(value) !== null;
}

export function detectKnownMeetingPlatform(value: string): KnownMeetingPlatform | null {
  const parsed = parseValidHttpsUrl(value);
  if (!parsed) return null;
  const { host, path } = parsed;

  if (
    host === 'meet.google.com' ||
    host.endsWith('.meet.google.com') ||
    (host === 'g.co' && (path === '/meet' || path.startsWith('/meet/')))
  ) {
    return 'Google Meet';
  }

  if (
    host === 'zoom.us' ||
    host.endsWith('.zoom.us') ||
    host === 'zoom.com' ||
    host.endsWith('.zoom.com') ||
    host === 'zoomgov.com' ||
    host.endsWith('.zoomgov.com')
  ) {
    return 'Zoom';
  }

  if (
    host === 'teams.microsoft.com' ||
    host.endsWith('.teams.microsoft.com') ||
    host === 'teams.live.com' ||
    host.endsWith('.teams.live.com') ||
    host === 'teams.microsoft.us' ||
    host.endsWith('.teams.microsoft.us')
  ) {
    return 'Microsoft Teams';
  }

  return null;
}

export function detectMeetingPlatform(value: string): MeetingPlatform | null {
  if (!parseValidHttpsUrl(value)) return null;
  return detectKnownMeetingPlatform(value) || 'Other';
}

export function resolveMeetingPlatform(
  meetingLink?: string | null,
  platform?: string | null,
): MeetingPlatform | null {
  const cleanPlatform = (platform || '').trim();
  if (cleanPlatform && (MEETING_PLATFORMS as readonly string[]).includes(cleanPlatform)) {
    return cleanPlatform as MeetingPlatform;
  }
  return detectMeetingPlatform(meetingLink || '');
}

export interface MeetingLinkValidation {
  valid: boolean;
  error: string | null;
  detectedPlatform: MeetingPlatform | null;
  suggestedPlatform: MeetingPlatform | null;
}

export function validateMeetingLinkForPlatform(
  meetingLink: string,
  platform?: string | null,
): MeetingLinkValidation {
  const cleanPlatform = (platform || '').trim();
  const parsed = parseValidHttpsUrl(meetingLink);
  if (!parsed) {
    const example =
      cleanPlatform && cleanPlatform in PLATFORM_PLACEHOLDERS
        ? PLATFORM_PLACEHOLDERS[cleanPlatform as MeetingPlatform]
        : '';
    return {
      valid: false,
      error:
        cleanPlatform && cleanPlatform !== 'Other' && example
          ? `Enter a valid ${cleanPlatform} URL starting with https:// (e.g. ${example}).`
          : 'Enter a valid meeting URL starting with https://.',
      detectedPlatform: null,
      suggestedPlatform: null,
    };
  }

  const detectedKnown = detectKnownMeetingPlatform(meetingLink);
  const detectedPlatform: MeetingPlatform = detectedKnown || 'Other';

  if (cleanPlatform) {
    if ((KNOWN_MEETING_PLATFORMS as readonly string[]).includes(cleanPlatform)) {
      if (detectedKnown && detectedKnown !== cleanPlatform) {
        const example = PLATFORM_PLACEHOLDERS[cleanPlatform as MeetingPlatform];
        return {
          valid: false,
          error: `This link is a ${detectedKnown} URL and does not match ${cleanPlatform}. Enter a valid ${cleanPlatform} link (e.g. ${example}) or switch platform to ${detectedKnown}.`,
          detectedPlatform,
          suggestedPlatform: detectedKnown,
        };
      }
      if (detectedKnown !== cleanPlatform) {
        const example = PLATFORM_PLACEHOLDERS[cleanPlatform as MeetingPlatform];
        return {
          valid: false,
          error: `This link does not match ${cleanPlatform}. Enter a valid ${cleanPlatform} link (e.g. ${example}) or switch platform to Other.`,
          detectedPlatform,
          suggestedPlatform: 'Other',
        };
      }
    } else if (cleanPlatform === 'Other' && detectedKnown) {
      return {
        valid: false,
        error: `This link is a ${detectedKnown} URL. Select ${detectedKnown} instead of Other.`,
        detectedPlatform,
        suggestedPlatform: detectedKnown,
      };
    }
  }

  return {
    valid: true,
    error: null,
    detectedPlatform,
    suggestedPlatform: null,
  };
}

export function isMeetingLinkValidForPlatform(
  meetingLink: string,
  platform?: string | null,
): boolean {
  return validateMeetingLinkForPlatform(meetingLink, platform).valid;
}

export interface MeetingLinkChangeResult {
  platform: string;
  autoDetected: MeetingPlatform | null;
  switchedFrom: string | null;
}

/**
 * Automatically aligns the active meeting platform button based on the link entered.
 * - Entering a Google Meet, Zoom, or Microsoft Teams link immediately updates the selected platform
 *   (even if a different platform button was previously selected).
 * - Entering another valid meeting URL with a path/query selects "Other" when no platform is chosen yet.
 */
export function applyMeetingLinkChange(
  currentPlatform: string,
  nextLink: string,
): MeetingLinkChangeResult {
  const cleanCurrent = (currentPlatform || '').trim();
  const known = detectKnownMeetingPlatform(nextLink);

  if (known) {
    return {
      platform: known,
      autoDetected: known,
      switchedFrom: cleanCurrent && cleanCurrent !== known ? cleanCurrent : null,
    };
  }

  const parsed = parseValidHttpsUrl(nextLink);
  if (!cleanCurrent && parsed && (parsed.path.length > 1 || Boolean(parsed.url.search))) {
    return {
      platform: 'Other',
      autoDetected: 'Other',
      switchedFrom: null,
    };
  }

  return {
    platform: cleanCurrent,
    autoDetected: null,
    switchedFrom: null,
  };
}

export function getJoinButtonLabel(
  meetingLink?: string | null,
  platform?: string | null,
  options?: { compact?: boolean },
): string {
  const resolved = detectKnownMeetingPlatform(meetingLink || '') || resolveMeetingPlatform(meetingLink, platform);
  if (options?.compact) {
    if (resolved === 'Google Meet') return 'Join Meet';
    if (resolved === 'Zoom') return 'Join Zoom';
    if (resolved === 'Microsoft Teams') return 'Join Teams';
    return 'Join';
  }
  if (resolved === 'Google Meet') return 'Join Google Meet';
  if (resolved === 'Zoom') return 'Join Zoom';
  if (resolved === 'Microsoft Teams') return 'Join Microsoft Teams';
  return 'Join Meeting';
}
