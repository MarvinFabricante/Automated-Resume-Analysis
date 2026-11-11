'use client';

const ATS_BROADCAST_CHANNEL = 'mariwasa_ats_updates';

export type AtsTag =
  | 'Dashboard'
  | 'Jobs'
  | 'Candidates'
  | 'Applications'
  | 'Users'
  | 'Interviews'
  | 'CalendarEvents'
  | 'PhysicalResumes';

export function getTagsForRealtimeEvent(eventType?: string): AtsTag[] {
  const norm = String(eventType || '').toLowerCase();
  if (
    norm === 'application' ||
    norm === 'application_update' ||
    norm === 'applications_updated' ||
    norm === 'upload'
  ) {
    return ['Applications', 'Dashboard', 'Candidates'];
  }
  if (norm === 'schedule') {
    return ['Applications', 'Dashboard', 'Interviews', 'CalendarEvents'];
  }
  if (norm === 'job_creation' || norm === 'job_update') {
    return ['Jobs', 'Dashboard'];
  }
  if (norm === 'registration') {
    return ['Candidates', 'Dashboard', 'Users'];
  }
  if (norm === 'physical_resume') {
    return ['PhysicalResumes', 'Dashboard'];
  }
  return ['Applications', 'Dashboard', 'Candidates'];
}

export function broadcastAtsUpdate(eventType: string = 'applications_updated'): void {
  if (typeof window === 'undefined' || !('BroadcastChannel' in window)) return;
  try {
    const channel = new BroadcastChannel(ATS_BROADCAST_CHANNEL);
    channel.postMessage({ type: eventType, ts: Date.now() });
    channel.close();
  } catch {
    // BroadcastChannel unavailable or restricted
  }
}

export function subscribeAtsUpdates(onEvent: (eventType: string) => void): () => void {
  if (typeof window === 'undefined' || !('BroadcastChannel' in window)) {
    return () => {};
  }
  let channel: BroadcastChannel | null = null;
  try {
    channel = new BroadcastChannel(ATS_BROADCAST_CHANNEL);
    channel.onmessage = (ev: MessageEvent) => {
      onEvent(ev?.data?.type || 'applications_updated');
    };
  } catch {
    channel = null;
  }
  return () => {
    try {
      channel?.close();
    } catch {
      // ignore close errors
    }
  };
}

