import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(
  new URL('../src/utils/applicationTracker.ts', import.meta.url),
  'utf8'
);
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
});
const {
  computeApplicationTracker,
  isWithdrawnStatus,
  isResolvedStatus,
  isActiveApplicationStatus,
  isShortlistEligibleStatus,
  normalizeAppStatus,
} = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
);

test('Issue #1: Skipped Shortlisted stage is marked Done with subtle Skipped by HR note when Interview Scheduled', () => {
  const futureStart = new Date(Date.now() + 48 * 3600 * 1000).toISOString();
  const futureEnd = new Date(Date.now() + 49 * 3600 * 1000).toISOString();

  const tracker = computeApplicationTracker({
    status: 'Interview Scheduled',
    statusHistory: [
      { old_status: 'Submitted', new_status: 'Under Review', created_at: '2026-11-20T08:00:00Z' },
      { old_status: 'Under Review', new_status: 'Interview Scheduled', created_at: '2026-11-21T09:00:00Z' },
    ],
    interviews: [
      { id: 10, status: 'SCHEDULED', start_time: futureStart, end_time: futureEnd },
    ],
    createdAt: '2026-11-19T10:00:00Z',
  });

  assert.equal(tracker.stages.length, 5);
  assert.deepEqual(
    tracker.stages.map((s) => s.label),
    ['Submitted', 'Under Review', 'Shortlisted', 'Interview Scheduled', 'Initial Interview Result']
  );

  // Submitted, Under Review, and skipped Shortlisted are all Done
  assert.equal(tracker.stages[0].state, 'done');
  assert.equal(tracker.stages[1].state, 'done');
  assert.equal(tracker.stages[2].state, 'done');
  assert.equal(tracker.stages[2].skipped, true);
  assert.equal(tracker.stages[2].skippedNote, 'Skipped by HR');

  // Interview Scheduled is Active, Initial Interview Result is Upcoming
  assert.equal(tracker.stages[3].state, 'active');
  assert.equal(tracker.stages[4].state, 'upcoming');
  assert.deepEqual(tracker.skippedStageKeys, ['shortlisted']);
});

test('Issue #1: Existing data with Under Review status and a booked interview still computes Interview Scheduled as Active and Shortlisted as Done (Skipped by HR)', () => {
  const futureStart = new Date(Date.now() + 24 * 3600 * 1000).toISOString();
  const futureEnd = new Date(Date.now() + 25 * 3600 * 1000).toISOString();

  const tracker = computeApplicationTracker({
    status: 'Under Review',
    statusHistory: [
      { old_status: 'Submitted', new_status: 'Under Review', created_at: '2026-11-20T08:00:00Z' },
    ],
    interviews: [
      { id: 11, status: 'SCHEDULED', start_time: futureStart, end_time: futureEnd },
    ],
    createdAt: '2026-11-19T10:00:00Z',
  });

  assert.equal(tracker.stages[0].state, 'done');
  assert.equal(tracker.stages[1].state, 'done');
  assert.equal(tracker.stages[2].state, 'done');
  assert.equal(tracker.stages[2].skipped, true);
  assert.equal(tracker.stages[3].state, 'active');
  assert.equal(tracker.stages[4].state, 'upcoming');
});

test('Issue #5: Initial Interview Result becomes Active with Awaiting result once interview time has passed without a recorded result', () => {
  const pastStart = new Date(Date.now() - 4 * 3600 * 1000).toISOString();
  const pastEnd = new Date(Date.now() - 3 * 3600 * 1000).toISOString();

  const tracker = computeApplicationTracker({
    status: 'Interview Scheduled',
    statusHistory: [
      { old_status: 'Submitted', new_status: 'Under Review', created_at: '2026-11-18T08:00:00Z' },
      { old_status: 'Under Review', new_status: 'Shortlisted', created_at: '2026-11-19T08:00:00Z' },
      { old_status: 'Shortlisted', new_status: 'Interview Scheduled', created_at: '2026-11-20T08:00:00Z' },
    ],
    interviews: [
      { id: 12, status: 'SCHEDULED', start_time: pastStart, end_time: pastEnd },
    ],
    createdAt: '2026-11-17T10:00:00Z',
  });

  assert.equal(tracker.stages[0].state, 'done');
  assert.equal(tracker.stages[1].state, 'done');
  assert.equal(tracker.stages[2].state, 'done');
  assert.equal(tracker.stages[2].skipped, false);
  assert.equal(tracker.stages[3].state, 'done');
  assert.equal(tracker.stages[4].state, 'active');
  assert.equal(tracker.stages[4].outcome, 'awaiting');
  assert.equal(tracker.stages[4].badgeText, 'Awaiting result');
  assert.equal(tracker.isPassed, false);
  assert.equal(tracker.isNotSelected, false);
});

test('Issue #5: Passed Initial Interview shows endorsed label and marks application read-only', () => {
  const tracker = computeApplicationTracker({
    status: 'Passed initial interview',
    statusHistory: [
      { old_status: 'Submitted', new_status: 'Under Review', created_at: '2026-11-18T08:00:00Z' },
      { old_status: 'Under Review', new_status: 'Shortlisted', created_at: '2026-11-19T08:00:00Z' },
      { old_status: 'Shortlisted', new_status: 'Interview Scheduled', created_at: '2026-11-20T08:00:00Z' },
      { old_status: 'Interview Scheduled', new_status: 'Passed initial interview', created_at: '2026-11-22T08:00:00Z' },
    ],
    createdAt: '2026-11-17T10:00:00Z',
  });

  assert.equal(tracker.isPassed, true);
  assert.equal(tracker.isReadOnly, true);
  assert.equal(tracker.stages[4].state, 'done');
  assert.equal(tracker.stages[4].outcome, 'passed');
  assert.match(tracker.stages[4].subtitle, /Passed Initial Interview/);
  assert.match(tracker.stages[4].subtitle, /outside the system/i);
});

test('Issue #5: Not selected marks Initial Interview Result done with Not selected outcome', () => {
  const tracker = computeApplicationTracker({
    status: 'Not Selected',
    statusHistory: [
      { old_status: 'Submitted', new_status: 'Under Review', created_at: '2026-11-18T08:00:00Z' },
      { old_status: 'Under Review', new_status: 'Not Selected', created_at: '2026-11-20T08:00:00Z' },
    ],
    createdAt: '2026-11-17T10:00:00Z',
  });

  assert.equal(tracker.isNotSelected, true);
  assert.equal(tracker.stages[0].state, 'done');
  assert.equal(tracker.stages[1].state, 'done');
  assert.equal(tracker.stages[4].state, 'done');
  assert.equal(tracker.stages[4].outcome, 'not_selected');
  assert.equal(tracker.stages[4].badgeText, 'Not selected');
});

test('Issue #7: Withdrawn end state replaces active tracker with date + reason, zero active stages, and Not applicable later stages', () => {
  const tracker = computeApplicationTracker({
    status: 'Withdrawn by applicant',
    statusHistory: [
      { old_status: 'Submitted', new_status: 'Under Review', created_at: '2026-11-18T08:00:00Z' },
      { old_status: 'Under Review', new_status: 'Interview Scheduled', created_at: '2026-11-19T08:00:00Z' },
      {
        old_status: 'Interview Scheduled',
        new_status: 'Withdrawn by applicant',
        reason: 'Applicant withdrew application',
        created_at: '2026-11-21T12:00:00Z',
      },
    ],
    createdAt: '2026-11-17T10:00:00Z',
    resolvedAt: '2026-11-21T12:00:00Z',
  });

  assert.equal(tracker.isWithdrawn, true);
  assert.equal(tracker.isReadOnly, true);
  assert.equal(tracker.currentStageIndex, -1);
  assert.equal(tracker.withdrawalInfo?.reasonCategory, 'Withdrawn by applicant');
  assert.ok(tracker.withdrawalInfo?.withdrawnDateLabel);

  // Zero active stages
  assert.equal(tracker.stages.filter((s) => s.state === 'active').length, 0);

  // Stages reached up to Interview Scheduled are Done (Shortlisted skipped), Result is Not applicable
  assert.equal(tracker.stages[0].state, 'done');
  assert.equal(tracker.stages[1].state, 'done');
  assert.equal(tracker.stages[2].state, 'done');
  assert.equal(tracker.stages[2].skipped, true);
  assert.equal(tracker.stages[3].state, 'done');
  assert.equal(tracker.stages[4].state, 'not_applicable');
  assert.equal(tracker.stages[4].badgeText, 'Not applicable');
});

test('Issue #7: Withdrawn reasons map cleanly for Account deletion requested and Hired elsewhere in company', () => {
  const acctDel = computeApplicationTracker({
    status: 'Withdrawn by applicant',
    statusHistory: [
      {
        old_status: 'Submitted',
        new_status: 'Withdrawn by applicant',
        reason: 'Account deletion requested',
        created_at: '2026-11-22T09:00:00Z',
      },
    ],
    createdAt: '2026-11-20T09:00:00Z',
  });
  assert.equal(acctDel.withdrawalInfo?.reasonCategory, 'Account deletion requested');
  assert.equal(acctDel.stages[0].state, 'done');
  assert.equal(acctDel.stages[1].state, 'not_applicable');

  const hiredElsewhere = computeApplicationTracker({
    status: 'Withdrawn – hired elsewhere in company',
    statusHistory: [
      {
        old_status: 'Under Review',
        new_status: 'Withdrawn – hired elsewhere in company',
        reason: 'Hired elsewhere in company',
        created_at: '2026-11-22T10:00:00Z',
      },
    ],
    createdAt: '2026-11-20T09:00:00Z',
  });
  assert.equal(hiredElsewhere.withdrawalInfo?.reasonCategory, 'Hired elsewhere in company');
  assert.equal(hiredElsewhere.stages.filter((s) => s.state === 'active').length, 0);
});

test('Issue #7 & #8: Status classification helpers exclude Withdrawn, Passed, and Not Selected from active/shortlist pools', () => {
  assert.equal(isWithdrawnStatus('Withdrawn by applicant'), true);
  assert.equal(isWithdrawnStatus('Withdrawn – hired elsewhere in company'), true);
  assert.equal(isWithdrawnStatus('WITHDRAWN'), true);

  for (const resolved of [
    'Withdrawn by applicant',
    'Withdrawn – hired elsewhere in company',
    'Passed initial interview',
    'Not Selected',
    'Archived',
    'Rejected',
  ]) {
    assert.equal(isResolvedStatus(resolved), true, `${resolved} should be resolved`);
    assert.equal(isActiveApplicationStatus(resolved), false, `${resolved} should NOT be active`);
    assert.equal(isShortlistEligibleStatus(resolved), false, `${resolved} should NOT be shortlist-eligible`);
  }

  for (const active of ['Submitted', 'Pending', 'Under Review', 'Shortlisted', 'Interview Scheduled', 'Interviewed']) {
    assert.equal(isActiveApplicationStatus(active), true, `${active} should be active`);
    assert.equal(isShortlistEligibleStatus(active), true, `${active} should be shortlist-eligible`);
  }

  assert.equal(normalizeAppStatus('Reviewed'), 'Under Review');
  assert.equal(normalizeAppStatus('Pending'), 'Submitted');
});
