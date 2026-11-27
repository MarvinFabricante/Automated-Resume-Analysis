import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/utils/meetingPlatform.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
});
const {
  applyMeetingLinkChange,
  detectKnownMeetingPlatform,
  detectMeetingPlatform,
  getJoinButtonLabel,
  isMeetingLinkValidForPlatform,
  resolveMeetingPlatform,
  validMeetingLink,
  validateMeetingLinkForPlatform,
} = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);

test('detects Google Meet, Zoom, Microsoft Teams, and Other URLs accurately', () => {
  assert.equal(detectKnownMeetingPlatform('https://meet.google.com/abc-defg-hij'), 'Google Meet');
  assert.equal(detectKnownMeetingPlatform('https://g.co/meet/mariwasa-panel'), 'Google Meet');
  assert.equal(detectKnownMeetingPlatform('https://zoom.us/j/1234567890'), 'Zoom');
  assert.equal(detectKnownMeetingPlatform('https://us02web.zoom.us/j/9876543210?pwd=abc'), 'Zoom');
  assert.equal(detectKnownMeetingPlatform('https://company.zoom.com/my/hr'), 'Zoom');
  assert.equal(detectKnownMeetingPlatform('https://teams.microsoft.com/l/meetup-join/19%3ameeting'), 'Microsoft Teams');
  assert.equal(detectKnownMeetingPlatform('https://teams.live.com/meet/938472938'), 'Microsoft Teams');

  assert.equal(detectKnownMeetingPlatform('https://meet.jit.si/mariwasa-interview'), null);
  assert.equal(detectMeetingPlatform('https://meet.jit.si/mariwasa-interview'), 'Other');
  assert.equal(detectMeetingPlatform('http://meet.google.com/abc-defg-hij'), null);
  assert.equal(validMeetingLink('https://zoom'), false);
});

test('entering a Google Meet link automatically switches active platform button from Zoom to Google Meet', () => {
  const result = applyMeetingLinkChange('Zoom', 'https://meet.google.com/abc-defg-hij');
  assert.equal(result.platform, 'Google Meet');
  assert.equal(result.autoDetected, 'Google Meet');
  assert.equal(result.switchedFrom, 'Zoom');
});

test('entering Zoom or Teams links automatically switches active platform button', () => {
  const toZoom = applyMeetingLinkChange('Google Meet', 'https://us06web.zoom.us/j/8844221100');
  assert.equal(toZoom.platform, 'Zoom');
  assert.equal(toZoom.switchedFrom, 'Google Meet');

  const toTeams = applyMeetingLinkChange('Zoom', 'https://teams.microsoft.com/l/meetup-join/abc');
  assert.equal(toTeams.platform, 'Microsoft Teams');
  assert.equal(toTeams.switchedFrom, 'Zoom');
});

test('typing a partial Zoom hostname does not prematurely switch away from Zoom to Other', () => {
  const partial = applyMeetingLinkChange('Zoom', 'https://us02web.zo');
  assert.equal(partial.platform, 'Zoom');
  assert.equal(partial.autoDetected, null);
  assert.equal(partial.switchedFrom, null);
});

test('auto-selects Other when platform is blank and a complete custom meeting URL is entered', () => {
  const other = applyMeetingLinkChange('', 'https://meet.jit.si/mariwasa-hr');
  assert.equal(other.platform, 'Other');
  assert.equal(other.autoDetected, 'Other');
  assert.equal(other.switchedFrom, null);
});

test('rejects Zoom platform paired with Google Meet link (panel feedback check)', () => {
  const check = validateMeetingLinkForPlatform('https://meet.google.com/abc-defg-hij', 'Zoom');
  assert.equal(check.valid, false);
  assert.equal(check.detectedPlatform, 'Google Meet');
  assert.equal(check.suggestedPlatform, 'Google Meet');
  assert.match(check.error, /Google Meet/i);
  assert.match(check.error, /Zoom/i);
  assert.equal(isMeetingLinkValidForPlatform('https://meet.google.com/abc-defg-hij', 'Zoom'), false);
});

test('rejects other platform/link mismatches and suggests the right platform', () => {
  const meetWithZoom = validateMeetingLinkForPlatform('https://zoom.us/j/1234567890', 'Google Meet');
  assert.equal(meetWithZoom.valid, false);
  assert.equal(meetWithZoom.suggestedPlatform, 'Zoom');

  const zoomWithGeneric = validateMeetingLinkForPlatform('https://meet.jit.si/mariwasa', 'Zoom');
  assert.equal(zoomWithGeneric.valid, false);
  assert.equal(zoomWithGeneric.suggestedPlatform, 'Other');

  const otherWithMeet = validateMeetingLinkForPlatform('https://meet.google.com/abc-defg-hij', 'Other');
  assert.equal(otherWithMeet.valid, false);
  assert.equal(otherWithMeet.suggestedPlatform, 'Google Meet');
});

test('accepts matching platform/link pairs and resolves platform cleanly', () => {
  assert.equal(isMeetingLinkValidForPlatform('https://zoom.us/j/1234567890', 'Zoom'), true);
  assert.equal(isMeetingLinkValidForPlatform('https://meet.google.com/abc-defg-hij', 'Google Meet'), true);
  assert.equal(isMeetingLinkValidForPlatform('https://teams.microsoft.com/l/meetup-join/123', 'Microsoft Teams'), true);
  assert.equal(isMeetingLinkValidForPlatform('https://meet.jit.si/mariwasa', 'Other'), true);
  assert.equal(resolveMeetingPlatform('https://meet.google.com/abc-defg-hij', ''), 'Google Meet');
});

test('renders platform-aware join button labels', () => {
  assert.equal(getJoinButtonLabel('https://meet.google.com/abc-defg-hij'), 'Join Google Meet');
  assert.equal(getJoinButtonLabel('https://zoom.us/j/1234567890'), 'Join Zoom');
  assert.equal(getJoinButtonLabel('https://teams.microsoft.com/l/meetup-join/123'), 'Join Microsoft Teams');
  assert.equal(getJoinButtonLabel('https://meet.jit.si/room', 'Other'), 'Join Meeting');
  assert.equal(getJoinButtonLabel('https://zoom.us/j/1234567890', null, { compact: true }), 'Join Zoom');
});
