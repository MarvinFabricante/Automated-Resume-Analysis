"""Shared interview validation and applicant-facing details (naive times are Manila time)."""
from datetime import datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

MANILA = ZoneInfo('Asia/Manila')
ONLINE_INSTRUCTIONS = 'Please join a few minutes early and test your camera and microphone.'


def manila_time(value: datetime) -> datetime:
    return value.astimezone(MANILA) if value.tzinfo else value.replace(tzinfo=MANILA)


def validate_interview_details(interview_type, location, meeting_link):
    if interview_type not in ('Onsite', 'Online'):
        raise ValueError('Interview type is required. Choose Onsite or Online.')
    if interview_type == 'Onsite' and not (location or '').strip():
        raise ValueError('Location is required for an onsite interview.')
    if interview_type == 'Online':
        link = (meeting_link or '').strip()
        try:
            parsed = urlsplit(link)
            valid = (link.startswith('https://') and parsed.hostname and not parsed.username
                     and not any(c.isspace() for c in link) and parsed.port != 0)
        except ValueError:
            valid = False
        if not valid:
            raise ValueError('Meeting link must be a valid URL starting with https://.')


def interview_details_text(start_time, end_time=None, *, interview_type=None,
                           location=None, meeting_link=None, instructions=None, platform=None):
    kind = interview_type or ('Online' if meeting_link else 'Onsite' if location else 'Not specified')
    time = manila_time(start_time).strftime('%b %d, %Y at %I:%M %p')
    if end_time:
        time += ' – ' + manila_time(end_time).strftime('%I:%M %p')
    lines = [f'{time} (Philippine time)', f'Interview type: {kind}']
    if kind == 'Online' and meeting_link:
        lines.extend([f'Meeting link: {meeting_link}', ONLINE_INSTRUCTIONS])
        if platform:
            lines.append(f'Platform: {platform}')
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
