export type TrackerStageKey =
  | 'submitted'
  | 'under_review'
  | 'shortlisted'
  | 'interview_scheduled'
  | 'initial_interview_result';

export type TrackerStageState = 'done' | 'active' | 'upcoming' | 'not_applicable';

export type ResultOutcome = 'pending' | 'awaiting' | 'passed' | 'not_selected';

export interface StatusHistoryRecord {
  id?: number | string;
  old_status?: string | null;
  new_status?: string | null;
  changed_by?: string | null;
  change_type?: string | null;
  reason?: string | null;
  created_at?: string | null;
  timestamp?: string | null;
}

export interface InterviewRecord {
  id?: number | string;
  job_application_id?: number | string;
  combined_application_ids?: Array<number | string>;
  status?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  title?: string | null;
  created_at?: string | null;
}

export interface ComputedTrackerStage {
  key: TrackerStageKey;
  index: number;
  label: string;
  state: TrackerStageState;
  skipped: boolean;
  skippedNote?: string;
  timestamp?: string | null;
  dateLabel?: string | null;
  subtitle: string;
  badgeText?: string;
  outcome?: ResultOutcome;
}

export interface WithdrawalInfo {
  isWithdrawn: boolean;
  withdrawnAt: string | null;
  withdrawnDateLabel: string | null;
  reasonCategory: 'Withdrawn by applicant' | 'Account deletion requested' | 'Hired elsewhere in company';
  detailNote?: string | null;
}

export interface ComputedApplicationTracker {
  normalizedStatus: string;
  displayStatus: string;
  isWithdrawn: boolean;
  isPassed: boolean;
  isNotSelected: boolean;
  isResolved: boolean;
  isActive: boolean;
  isOnHold: boolean;
  isReadOnly: boolean;
  currentStageIndex: number; // -1 when withdrawn
  completedStagesCount: number;
  totalStages: number;
  resultOutcome: ResultOutcome;
  withdrawalInfo: WithdrawalInfo | null;
  stages: ComputedTrackerStage[];
  skippedStageKeys: TrackerStageKey[];
}

export const TRACKER_STAGE_DEFINITIONS: Array<{
  key: TrackerStageKey;
  index: number;
  label: string;
}> = [
  { key: 'submitted', index: 0, label: 'Submitted' },
  { key: 'under_review', index: 1, label: 'Under Review' },
  { key: 'shortlisted', index: 2, label: 'Shortlisted' },
  { key: 'interview_scheduled', index: 3, label: 'Interview Scheduled' },
  { key: 'initial_interview_result', index: 4, label: 'Initial Interview Result' },
];

const INACTIVE_INTERVIEW_STATUSES = new Set([
  'CANCELED',
  'CANCELLED',
  'REJECTED',
  'NO_SHOW',
]);

export function normalizeAppStatus(status?: string | null): string {
  const s = String(status || '').trim().toUpperCase();
  if (!s || s === 'SUBMITTED' || s === 'PENDING') return 'Submitted';
  if (s === 'UNDER REVIEW' || s === 'REVIEWED' || s === 'SCREENED') return 'Under Review';
  if (s === 'SHORTLISTED' || s === 'SHORTLIST') return 'Shortlisted';
  if (
    s === 'INTERVIEW SCHEDULED' ||
    s === 'TECHNICAL INTERVIEW' ||
    s === 'INTERVIEW' ||
    s === 'FINAL INTERVIEW'
  ) {
    return 'Interview Scheduled';
  }
  if (s === 'INTERVIEWED') return 'Interviewed';
  if (s === 'ON HOLD' || s === 'ON_HOLD') return 'On Hold';
  if (
    s === 'WITHDRAWN – HIRED ELSEWHERE IN COMPANY' ||
    s === 'WITHDRAWN - HIRED ELSEWHERE IN COMPANY' ||
    s === 'WITHDRAWN_HIRED_ELSEWHERE' ||
    (s.includes('WITHDRAWN') && s.includes('HIRED'))
  ) {
    return 'Withdrawn – hired elsewhere in company';
  }
  if (s === 'WITHDRAWN' || s === 'WITHDRAWN BY APPLICANT' || s.startsWith('WITHDRAWN')) {
    return 'Withdrawn by applicant';
  }
  if (
    s === 'PASSED INITIAL INTERVIEW' ||
    s === 'PASSED INITIAL INTERVIEW – ENDORSED FOR NEXT STAGE' ||
    s === 'PASSED INITIAL INTERVIEW - ENDORSED FOR NEXT STAGE' ||
    s === 'PASSED' ||
    s === 'ACCEPTED' ||
    s === 'HIRED' ||
    s === 'OFFER_ACCEPTED'
  ) {
    return 'Passed initial interview';
  }
  if (
    s === 'NOT SELECTED' ||
    s === 'NOT_SELECTED' ||
    s === 'REJECTED' ||
    s === 'ARCHIVED' ||
    s === 'PASSED_OVER' ||
    s === 'CLOSED'
  ) {
    return 'Not Selected';
  }
  return status ? String(status).trim() : 'Submitted';
}

export function isWithdrawnStatus(status?: string | null): boolean {
  const norm = normalizeAppStatus(status);
  return (
    norm === 'Withdrawn by applicant' ||
    norm === 'Withdrawn – hired elsewhere in company'
  );
}

export function isPassedStatus(status?: string | null): boolean {
  return normalizeAppStatus(status) === 'Passed initial interview';
}

export function isNotSelectedStatus(status?: string | null): boolean {
  return normalizeAppStatus(status) === 'Not Selected';
}

export function isResolvedStatus(status?: string | null): boolean {
  return isWithdrawnStatus(status) || isPassedStatus(status) || isNotSelectedStatus(status);
}

export function isActiveApplicationStatus(status?: string | null): boolean {
  return !isResolvedStatus(status);
}

export function isShortlistEligibleStatus(status?: string | null): boolean {
  return !isResolvedStatus(status);
}

export function getDisplayStatusLabel(status?: string | null): string {
  const norm = normalizeAppStatus(status);
  if (norm === 'Passed initial interview') {
    return 'Passed Initial Interview – Endorsed for next stage';
  }
  if (norm === 'Not Selected') {
    return 'Not selected';
  }
  return norm;
}

export function getStageIndexForNormalizedStatus(normStatus: string): number {
  switch (normStatus) {
    case 'Submitted':
      return 0;
    case 'Under Review':
      return 1;
    case 'Shortlisted':
      return 2;
    case 'Interview Scheduled':
      return 3;
    case 'Interviewed':
    case 'Passed initial interview':
      return 4;
    default:
      return -1;
  }
}

export function formatTrackerDate(value?: string | Date | null): string | null {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function parseTimeMs(value?: string | Date | null): number {
  if (!value) return NaN;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? NaN : d.getTime();
}

function sortHistoryAsc(history: StatusHistoryRecord[] = []): StatusHistoryRecord[] {
  return [...history].sort((a, b) => {
    const aMs = parseTimeMs(a.created_at || a.timestamp);
    const bMs = parseTimeMs(b.created_at || b.timestamp);
    if (Number.isNaN(aMs) && Number.isNaN(bMs)) return 0;
    if (Number.isNaN(aMs)) return -1;
    if (Number.isNaN(bMs)) return 1;
    return aMs - bMs;
  });
}

export function extractWithdrawalInfo(params: {
  status?: string | null;
  statusHistory?: StatusHistoryRecord[];
  resolvedAt?: string | null;
  updatedAt?: string | null;
}): WithdrawalInfo | null {
  const { status, statusHistory = [], resolvedAt, updatedAt } = params;
  if (!isWithdrawnStatus(status)) return null;

  const norm = normalizeAppStatus(status);
  const sorted = sortHistoryAsc(statusHistory);
  const withdrawEntry = [...sorted]
    .reverse()
    .find((h) => isWithdrawnStatus(h.new_status));

  const rawReason = String(withdrawEntry?.reason || '').trim();
  const rawReasonLower = rawReason.toLowerCase();

  let reasonCategory: WithdrawalInfo['reasonCategory'] = 'Withdrawn by applicant';
  if (
    norm === 'Withdrawn – hired elsewhere in company' ||
    rawReasonLower.includes('hired elsewhere') ||
    rawReasonLower.includes('accepted another role')
  ) {
    reasonCategory = 'Hired elsewhere in company';
  } else if (rawReasonLower.includes('account deletion')) {
    reasonCategory = 'Account deletion requested';
  }

  const withdrawnAt =
    withdrawEntry?.created_at ||
    withdrawEntry?.timestamp ||
    resolvedAt ||
    updatedAt ||
    null;

  const isDuplicateNote =
    !rawReason ||
    rawReasonLower === reasonCategory.toLowerCase() ||
    rawReasonLower === norm.toLowerCase();

  return {
    isWithdrawn: true,
    withdrawnAt,
    withdrawnDateLabel: formatTrackerDate(withdrawnAt),
    reasonCategory,
    detailNote: isDuplicateNote ? null : rawReason,
  };
}

export interface ComputeTrackerInput {
  status?: string | null;
  statusHistory?: StatusHistoryRecord[];
  interviews?: InterviewRecord[];
  createdAt?: string | null;
  resolvedAt?: string | null;
  updatedAt?: string | null;
  now?: Date;
}

export function computeApplicationTracker(input: ComputeTrackerInput): ComputedApplicationTracker {
  const {
    status,
    statusHistory = [],
    interviews = [],
    createdAt = null,
    resolvedAt = null,
    updatedAt = null,
    now = new Date(),
  } = input;

  const normStatus = normalizeAppStatus(status);
  const displayStatus = getDisplayStatusLabel(status);
  const withdrawn = isWithdrawnStatus(normStatus);
  const passed = isPassedStatus(normStatus);
  const notSelected = isNotSelectedStatus(normStatus);
  const resolved = withdrawn || passed || notSelected;
  const onHold = normStatus === 'On Hold';
  const nowMs = now.getTime();

  const sortedHistory = sortHistoryAsc(statusHistory);
  const hasHistory = sortedHistory.length > 0;

  // Record every explicitly visited pipeline stage from status history
  const visitedStageTimestamps = new Map<number, string | null>();
  visitedStageTimestamps.set(0, createdAt);

  let lastActiveStageBeforeTerminal = 0;

  for (const h of sortedHistory) {
    const oldNorm = h.old_status ? normalizeAppStatus(h.old_status) : null;
    const newNorm = h.new_status ? normalizeAppStatus(h.new_status) : null;
    const ts = h.created_at || h.timestamp || null;

    if (oldNorm) {
      const oldIdx = getStageIndexForNormalizedStatus(oldNorm);
      if (oldIdx >= 0) {
        if (!visitedStageTimestamps.has(oldIdx)) {
          visitedStageTimestamps.set(oldIdx, oldIdx === 0 ? createdAt : null);
        }
        if (oldIdx <= 3 && !isResolvedStatus(oldNorm)) {
          lastActiveStageBeforeTerminal = Math.max(lastActiveStageBeforeTerminal, oldIdx);
        }
        if (oldNorm === 'Interviewed') {
          visitedStageTimestamps.set(3, visitedStageTimestamps.get(3) ?? null);
          lastActiveStageBeforeTerminal = Math.max(lastActiveStageBeforeTerminal, 3);
        }
      }
    }

    if (newNorm) {
      const newIdx = getStageIndexForNormalizedStatus(newNorm);
      if (newIdx >= 0) {
        if (newNorm === 'Passed initial interview') {
          visitedStageTimestamps.set(4, ts);
        } else if (newNorm === 'Interviewed') {
          visitedStageTimestamps.set(4, ts);
          lastActiveStageBeforeTerminal = Math.max(lastActiveStageBeforeTerminal, 3);
        } else {
          visitedStageTimestamps.set(newIdx, ts);
          if (newIdx <= 3) {
            lastActiveStageBeforeTerminal = Math.max(lastActiveStageBeforeTerminal, newIdx);
          }
        }
      }
    }
  }

  // Inspect interviews (non-canceled and completed)
  const nonCanceledInterviews = (interviews || []).filter(
    (iv) => !INACTIVE_INTERVIEW_STATUSES.has(String(iv?.status || '').trim().toUpperCase())
  );
  const completedInterviews = nonCanceledInterviews.filter(
    (iv) => String(iv?.status || '').trim().toUpperCase() === 'COMPLETED'
  );
  const scheduledInterviews = nonCanceledInterviews.filter(
    (iv) => String(iv?.status || '').trim().toUpperCase() !== 'COMPLETED'
  );

  // Latest active or completed interview (for date/timestamp detection)
  const relevantInterviews = [...nonCanceledInterviews].sort((a, b) => {
    const aMs = parseTimeMs(a.start_time || a.created_at);
    const bMs = parseTimeMs(b.start_time || b.created_at);
    return (Number.isNaN(bMs) ? 0 : bMs) - (Number.isNaN(aMs) ? 0 : aMs);
  });
  const latestRelevantInterview = relevantInterviews[0] || null;
  const hasAnyInterviewRecord = relevantInterviews.length > 0;

  if (hasAnyInterviewRecord && !visitedStageTimestamps.has(3)) {
    visitedStageTimestamps.set(
      3,
      latestRelevantInterview?.created_at || latestRelevantInterview?.start_time || null
    );
  }

  // Has the interview date passed (and interview is not canceled)?
  const interviewDatePassed =
    normStatus === 'Interviewed' ||
    completedInterviews.length > 0 ||
    scheduledInterviews.some((iv) => {
      const endMs = parseTimeMs(iv.end_time || iv.start_time);
      return !Number.isNaN(endMs) && endMs <= nowMs;
    });

  // Helper to decide if an earlier stage was skipped by HR
  const isStageSkipped = (stageIdx: number, maxStageIdx: number): boolean => {
    if (stageIdx <= 0 || stageIdx >= maxStageIdx) return false;
    if (visitedStageTimestamps.has(stageIdx)) return false;
    // For Shortlisted (idx 2): if we reached Interview Scheduled+ without Shortlisted in history
    // OR current status is still Under Review while an interview was booked directly
    if (stageIdx === 2) {
      return hasHistory || normStatus === 'Under Review' || normStatus === 'Submitted' || hasAnyInterviewRecord;
    }
    // For Under Review (idx 1) or Interview Scheduled (idx 3): only flag skipped if we have history evidence
    return hasHistory;
  };

  // ── CASE 1: WITHDRAWN (End State) ─────────────────────────────────────────
  if (withdrawn) {
    const withdrawalInfo = extractWithdrawalInfo({
      status,
      statusHistory: sortedHistory,
      resolvedAt,
      updatedAt,
    });

    // Determine highest stage reached prior to withdrawal
    let maxReached = lastActiveStageBeforeTerminal;
    // Check withdrawal history entry's old_status explicitly
    const wdEntry = [...sortedHistory].reverse().find((h) => isWithdrawnStatus(h.new_status));
    if (wdEntry?.old_status) {
      const wdPrevNorm = normalizeAppStatus(wdEntry.old_status);
      const wdPrevIdx = getStageIndexForNormalizedStatus(wdPrevNorm);
      if (wdPrevIdx >= 0) {
        maxReached = Math.max(maxReached, Math.min(wdPrevIdx, 3));
      }
    }
    // Also consider if any interview existed (even if later cancelled by withdrawal)
    if ((interviews || []).length > 0) {
      maxReached = Math.max(maxReached, 3);
    }

    const stages: ComputedTrackerStage[] = TRACKER_STAGE_DEFINITIONS.map((def) => {
      if (def.index <= maxReached) {
        const skipped = isStageSkipped(def.index, maxReached);
        const ts = visitedStageTimestamps.get(def.index) || (def.index === 0 ? createdAt : null);
        return {
          key: def.key,
          index: def.index,
          label: def.label,
          state: 'done',
          skipped,
          skippedNote: skipped ? 'Skipped by HR' : undefined,
          timestamp: ts,
          dateLabel: formatTrackerDate(ts),
          subtitle: skipped
            ? 'Completed (Skipped by HR)'
            : def.index === 0
              ? 'Application submitted'
              : 'Completed prior to withdrawal',
          badgeText: 'Done',
        };
      }
      return {
        key: def.key,
        index: def.index,
        label: def.label,
        state: 'not_applicable',
        skipped: false,
        timestamp: null,
        dateLabel: null,
        subtitle: 'Not applicable',
        badgeText: 'Not applicable',
      };
    });

    return {
      normalizedStatus: normStatus,
      displayStatus,
      isWithdrawn: true,
      isPassed: false,
      isNotSelected: false,
      isResolved: true,
      isActive: false,
      isOnHold: false,
      isReadOnly: true,
      currentStageIndex: -1,
      completedStagesCount: stages.filter((s) => s.state === 'done').length,
      totalStages: TRACKER_STAGE_DEFINITIONS.length,
      resultOutcome: 'pending',
      withdrawalInfo,
      stages,
      skippedStageKeys: stages.filter((s) => s.skipped).map((s) => s.key),
    };
  }

  // ── CASE 2: PASSED INITIAL INTERVIEW (End State) ──────────────────────────
  if (passed) {
    const resultTs = visitedStageTimestamps.get(4) || resolvedAt || updatedAt || null;
    const stages: ComputedTrackerStage[] = TRACKER_STAGE_DEFINITIONS.map((def) => {
      if (def.index < 4) {
        const skipped = isStageSkipped(def.index, 4);
        const ts = visitedStageTimestamps.get(def.index) || (def.index === 0 ? createdAt : null);
        return {
          key: def.key,
          index: def.index,
          label: def.label,
          state: 'done',
          skipped,
          skippedNote: skipped ? 'Skipped by HR' : undefined,
          timestamp: ts,
          dateLabel: formatTrackerDate(ts),
          subtitle: skipped ? 'Completed (Skipped by HR)' : 'Completed',
          badgeText: 'Done',
        };
      }
      return {
        key: def.key,
        index: def.index,
        label: def.label,
        state: 'done',
        skipped: false,
        timestamp: resultTs,
        dateLabel: formatTrackerDate(resultTs),
        subtitle: 'Passed Initial Interview – Endorsed for next stage. HR will contact you outside the system.',
        badgeText: 'Passed',
        outcome: 'passed',
      };
    });

    return {
      normalizedStatus: normStatus,
      displayStatus,
      isWithdrawn: false,
      isPassed: true,
      isNotSelected: false,
      isResolved: true,
      isActive: false,
      isOnHold: false,
      isReadOnly: true,
      currentStageIndex: 4,
      completedStagesCount: 5,
      totalStages: TRACKER_STAGE_DEFINITIONS.length,
      resultOutcome: 'passed',
      withdrawalInfo: null,
      stages,
      skippedStageKeys: stages.filter((s) => s.skipped).map((s) => s.key),
    };
  }

  // ── CASE 3: NOT SELECTED (End State, feedback report stays viewable) ──────
  if (notSelected) {
    const nsEntry = [...sortedHistory].reverse().find((h) => isNotSelectedStatus(h.new_status));
    const resultTs = nsEntry?.created_at || nsEntry?.timestamp || resolvedAt || updatedAt || null;
    const reachedInterview =
      visitedStageTimestamps.has(3) ||
      visitedStageTimestamps.has(4) ||
      hasAnyInterviewRecord ||
      lastActiveStageBeforeTerminal >= 3;

    let maxReachedBeforeDecision = lastActiveStageBeforeTerminal;
    if (nsEntry?.old_status) {
      const prevIdx = getStageIndexForNormalizedStatus(normalizeAppStatus(nsEntry.old_status));
      if (prevIdx >= 0) {
        maxReachedBeforeDecision = Math.max(maxReachedBeforeDecision, Math.min(prevIdx, 3));
      }
    }
    if (reachedInterview) {
      maxReachedBeforeDecision = 3;
    }

    const stages: ComputedTrackerStage[] = TRACKER_STAGE_DEFINITIONS.map((def) => {
      if (def.index === 4) {
        return {
          key: def.key,
          index: def.index,
          label: def.label,
          state: 'done',
          skipped: false,
          timestamp: resultTs,
          dateLabel: formatTrackerDate(resultTs),
          subtitle: 'Not selected — your feedback report remains viewable.',
          badgeText: 'Not selected',
          outcome: 'not_selected',
        };
      }
      if (def.index <= maxReachedBeforeDecision) {
        const skipped = isStageSkipped(def.index, maxReachedBeforeDecision + 1);
        const ts = visitedStageTimestamps.get(def.index) || (def.index === 0 ? createdAt : null);
        return {
          key: def.key,
          index: def.index,
          label: def.label,
          state: 'done',
          skipped,
          skippedNote: skipped ? 'Skipped by HR' : undefined,
          timestamp: ts,
          dateLabel: formatTrackerDate(ts),
          subtitle: skipped ? 'Completed (Skipped by HR)' : 'Completed',
          badgeText: 'Done',
        };
      }
      return {
        key: def.key,
        index: def.index,
        label: def.label,
        state: 'not_applicable',
        skipped: false,
        timestamp: null,
        dateLabel: null,
        subtitle: 'Not applicable',
        badgeText: 'Not applicable',
      };
    });

    return {
      normalizedStatus: normStatus,
      displayStatus,
      isWithdrawn: false,
      isPassed: false,
      isNotSelected: true,
      isResolved: true,
      isActive: false,
      isOnHold: false,
      isReadOnly: false,
      currentStageIndex: 4,
      completedStagesCount: stages.filter((s) => s.state === 'done').length,
      totalStages: TRACKER_STAGE_DEFINITIONS.length,
      resultOutcome: 'not_selected',
      withdrawalInfo: null,
      stages,
      skippedStageKeys: stages.filter((s) => s.skipped).map((s) => s.key),
    };
  }

  // ── CASE 4: ACTIVE PIPELINE ───────────────────────────────────────────────
  // Compute effective current stage from status + status history + interviews (fixes legacy data on display!)
  let currentStageIndex = getStageIndexForNormalizedStatus(normStatus);
  if (onHold) {
    currentStageIndex = Math.max(1, lastActiveStageBeforeTerminal);
  }
  if (currentStageIndex < 0) {
    currentStageIndex = 0;
  }

  // If HR scheduled an interview without updating status past Under Review / Submitted,
  // compute stage 3 (Interview Scheduled) on display automatically!
  if (hasAnyInterviewRecord && currentStageIndex < 3) {
    currentStageIndex = 3;
  }

  // Also ensure currentStageIndex never regresses behind active status history progression
  // unless an explicit cancellation/undo reverted it (in which case current normStatus is authoritative
  // when no active interview exists).
  let resultOutcome: ResultOutcome = 'pending';

  // Issue #5: Show Initial Interview Result as Upcoming while scheduled,
  // and Active (with "Awaiting result") after the interview date has passed and no result is recorded.
  if (currentStageIndex >= 3 && interviewDatePassed) {
    currentStageIndex = 4;
    resultOutcome = 'awaiting';
  } else if (normStatus === 'Interviewed') {
    currentStageIndex = 4;
    resultOutcome = 'awaiting';
  }

  const defaultSubtitles: Record<TrackerStageKey, { done: string; active: string; upcoming: string }> = {
    submitted: {
      done: 'Application received',
      active: 'Application received and queued for review',
      upcoming: 'Pending submission',
    },
    under_review: {
      done: 'Reviewed by Mariwasa HR',
      active: 'HR team is reviewing your application',
      upcoming: 'Upcoming review stage',
    },
    shortlisted: {
      done: 'Shortlisted for interview',
      active: 'Shortlisted — awaiting interview schedule',
      upcoming: 'Pending shortlisting decision',
    },
    interview_scheduled: {
      done: 'Initial interview scheduled',
      active: 'Initial interview booked',
      upcoming: 'Pending interview booking',
    },
    initial_interview_result: {
      done: 'Result recorded',
      active: 'Awaiting result from HR',
      upcoming: 'Pending until HR records the result',
    },
  };

  const stages: ComputedTrackerStage[] = TRACKER_STAGE_DEFINITIONS.map((def) => {
    const ts = visitedStageTimestamps.get(def.index) || (def.index === 0 ? createdAt : null);

    if (def.index < currentStageIndex) {
      const skipped = isStageSkipped(def.index, currentStageIndex);
      return {
        key: def.key,
        index: def.index,
        label: def.label,
        state: 'done',
        skipped,
        skippedNote: skipped ? 'Skipped by HR' : undefined,
        timestamp: ts,
        dateLabel: formatTrackerDate(ts),
        subtitle: skipped ? 'Completed (Skipped by HR)' : defaultSubtitles[def.key].done,
        badgeText: 'Done',
      };
    }

    if (def.index === currentStageIndex) {
      const isAwaitingResult = def.index === 4 && resultOutcome === 'awaiting';
      return {
        key: def.key,
        index: def.index,
        label: def.label,
        state: 'active',
        skipped: false,
        timestamp: ts,
        dateLabel: formatTrackerDate(ts),
        subtitle: onHold
          ? 'Application is currently On Hold'
          : isAwaitingResult
            ? 'Interview date has passed — awaiting result from HR'
            : defaultSubtitles[def.key].active,
        badgeText: onHold ? 'On Hold' : isAwaitingResult ? 'Awaiting result' : 'Active',
        outcome: def.index === 4 ? resultOutcome : undefined,
      };
    }

    return {
      key: def.key,
      index: def.index,
      label: def.label,
      state: 'upcoming',
      skipped: false,
      timestamp: null,
      dateLabel: null,
      subtitle: defaultSubtitles[def.key].upcoming,
      badgeText: 'Upcoming',
      outcome: def.index === 4 ? 'pending' : undefined,
    };
  });

  return {
    normalizedStatus: normStatus,
    displayStatus,
    isWithdrawn: false,
    isPassed: false,
    isNotSelected: false,
    isResolved: false,
    isActive: true,
    isOnHold: onHold,
    isReadOnly: false,
    currentStageIndex,
    completedStagesCount: stages.filter((s) => s.state === 'done').length,
    totalStages: TRACKER_STAGE_DEFINITIONS.length,
    resultOutcome,
    withdrawalInfo: null,
    stages,
    skippedStageKeys: stages.filter((s) => s.skipped).map((s) => s.key),
  };
}
