import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/utils/interviewUtils.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
});
const { extractMessageLogs, getInterviewSmsStatus } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
);

test('provider acceptance is queued for every SMS event, including legacy logs', () => {
  for (const log_type of ['SMS_SENT', 'SMS_RESCHEDULED', 'SMS_CANCELED', 'SMS_BACKUP_SENT']) {
    const interview = { id: 1, logs: [{ id: 2, log_type, details: 'SMS delivered to +639175558899 [message_id=iSms-test]' }] };
    const [message] = extractMessageLogs([interview]);
    assert.equal(message.status, 'QUEUED');
    assert.equal(message.recipient, '+639175558899');
    assert.equal(getInterviewSmsStatus(interview), 'QUEUED');
  }
});

test('latest failed attempt stays failed and preserves the provider reason', () => {
  const interview = { id: 1, logs: [
    { id: 2, log_type: 'SMS_SENT', created_at: '2026-11-24T10:00:00Z' },
    { id: 3, log_type: 'SMS_FAILED', details: 'Insufficient credits', created_at: '2026-11-24T11:00:00Z' },
  ] };
  assert.equal(getInterviewSmsStatus(interview), 'FAILED');
  assert.equal(extractMessageLogs([interview])[0].details, 'Insufficient credits');
});

test('backup flags do not imply handset delivery', () => {
  assert.equal(extractMessageLogs([{ id: 1, sms_backup_sent: true }])[0].status, 'QUEUED');
  assert.equal(extractMessageLogs([], [{ id: 2, interview_id: 1, sms_backup_sent: true }])[0].status, 'QUEUED');
  assert.equal(getInterviewSmsStatus({ id: 1, logs: [] }), null);
});
