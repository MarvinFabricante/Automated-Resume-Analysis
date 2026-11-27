"""Shared interview validation and applicant-facing details (naive times are Manila time)."""
from datetime import datetime
from typing import Optional
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

MANILA = ZoneInfo('Asia/Manila')
ONLINE_INSTRUCTIONS = 'Please join a few minutes early and test your camera and microphone.'
MEETING_PLATFORMS = ('Google Meet', 'Zoom', 'Microsoft Teams', 'Other')
KNOWN_MEETING_PLATFORMS = ('Google Meet', 'Zoom', 'Microsoft Teams')

PLATFORM_EXAMPLES = {
    'Google Meet': 'https://meet.google.com/abc-defg-hij',
    'Zoom': 'https://zoom.us/j/1234567890',
    'Microsoft Teams': 'https://teams.microsoft.com/l/meetup-join/...',
    'Other': 'https://...',
}


def manila_time(value: datetime) -> datetime:
    return value.astimezone(MANILA) if value.tzinfo else value.replace(tzinfo=MANILA)


def _parse_valid_https_url(meeting_link: Optional[str]):
    link = (meeting_link or '').strip()
    if not link or not link.startswith('https://') or any(c.isspace() for c in link):
        return None
    try:
        parsed = urlsplit(link)
    except ValueError:
        return None
    hostname = (parsed.hostname or '').strip().lower().rstrip('.')
    if not hostname or parsed.username or parsed.port == 0:
        return None
    labels = hostname.split('.')
    if len(labels) < 2 or any(not label for label in labels):
        return None
    return parsed, hostname


def detect_known_meeting_platform(meeting_link: Optional[str]) -> Optional[str]:
    parsed_result = _parse_valid_https_url(meeting_link)
    if not parsed_result:
        return None
    parsed, host = parsed_result
    path = (parsed.path or '').lower()

    if (
        host == 'meet.google.com'
        or host.endswith('.meet.google.com')
        or (host == 'g.co' and (path == '/meet' or path.startswith('/meet/')))
    ):
        return 'Google Meet'

    if (
        host == 'zoom.us'
        or host.endswith('.zoom.us')
        or host == 'zoom.com'
        or host.endswith('.zoom.com')
        or host == 'zoomgov.com'
        or host.endswith('.zoomgov.com')
    ):
        return 'Zoom'

    if (
        host == 'teams.microsoft.com'
        or host.endswith('.teams.microsoft.com')
        or host == 'teams.live.com'
        or host.endswith('.teams.live.com')
        or host == 'teams.microsoft.us'
        or host.endswith('.teams.microsoft.us')
    ):
        return 'Microsoft Teams'

    return None


def detect_meeting_platform(meeting_link: Optional[str]) -> Optional[str]:
    if not _parse_valid_https_url(meeting_link):
        return None
    return detect_known_meeting_platform(meeting_link) or 'Other'


def resolve_meeting_platform(meeting_link: Optional[str], platform: Optional[str] = None) -> Optional[str]:
    clean_platform = (platform or '').strip() or None
    if clean_platform:
        return clean_platform
    return detect_meeting_platform(meeting_link)


def validate_interview_details(interview_type, location, meeting_link, platform=None):
    if interview_type not in ('Onsite', 'Online'):
        raise ValueError('Interview type is required. Choose Onsite or Online.')
    if interview_type == 'Onsite' and not (location or '').strip():
        raise ValueError('Location is required for an onsite interview.')
    if interview_type == 'Online':
        parsed_result = _parse_valid_https_url(meeting_link)
        if not parsed_result:
            raise ValueError('Meeting link must be a valid URL starting with https://.')

        clean_platform = (platform or '').strip() or None
        if clean_platform is not None:
            if clean_platform not in MEETING_PLATFORMS:
                raise ValueError(
                    f"Unsupported meeting platform '{clean_platform}'. Choose one of: {', '.join(MEETING_PLATFORMS)}."
                )
            detected_known = detect_known_meeting_platform(meeting_link)
            if clean_platform in KNOWN_MEETING_PLATFORMS:
                if detected_known and detected_known != clean_platform:
                    example = PLATFORM_EXAMPLES[clean_platform]
                    raise ValueError(
                        f'This link is a {detected_known} URL and does not match the selected platform ({clean_platform}). '
                        f'Enter a valid {clean_platform} link (e.g., {example}) or select {detected_known}.'
                    )
                if detected_known != clean_platform:
                    example = PLATFORM_EXAMPLES[clean_platform]
                    raise ValueError(
                        f'Meeting link does not match the selected platform ({clean_platform}). '
                        f'Enter a valid {clean_platform} link (e.g., {example}) or select Other.'
                    )
            elif clean_platform == 'Other' and detected_known is not None:
                raise ValueError(
                    f'This link is a {detected_known} URL. Select {detected_known} instead of Other.'
                )


def interview_details_text(start_time, end_time=None, *, interview_type=None,
                           location=None, meeting_link=None, instructions=None, platform=None):
    kind = interview_type or ('Online' if meeting_link else 'Onsite' if location else 'Not specified')
    time = manila_time(start_time).strftime('%b %d, %Y at %I:%M %p')
    if end_time:
        time += ' – ' + manila_time(end_time).strftime('%I:%M %p')
    lines = [f'{time} (Philippine time)', f'Interview type: {kind}']
    if kind == 'Online' and meeting_link:
        resolved_platform = resolve_meeting_platform(meeting_link, platform)
        lines.extend([f'Meeting link: {meeting_link}', ONLINE_INSTRUCTIONS])
        if resolved_platform:
            lines.append(f'Platform: {resolved_platform}')
    elif location:
        lines.append(f'Location: {location}')
    if instructions:
        lines.append(f'Instructions: {instructions}')
    return '\n'.join(lines)


def details_for_interview(interview):
    return interview_details_text(interview.start_time, interview.end_time, **{
        key: getattr(interview, key, None)
        for key in ('interview_type', 'location', 'meeting_link', 'instructions', 'platform')
    })
