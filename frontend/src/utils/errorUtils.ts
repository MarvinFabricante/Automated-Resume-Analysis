/**
 * Formats an API error `detail` payload (string, FastAPI validation error array,
 * or object) into a human-readable string safe for alerts and UI messages.
 */
export function formatApiErrorDetail(detail: unknown, fallback: string): string {
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object') {
          const record = item as Record<string, unknown>;
          const loc = Array.isArray(record.loc)
            ? record.loc.filter((part) => part !== 'body').join('.')
            : '';
          const msg = record.msg || record.message;
          if (typeof msg === 'string' && msg.trim()) {
            return loc ? `${loc}: ${msg}` : msg;
          }
          try {
            return JSON.stringify(item);
          } catch {
            return '';
          }
        }
        return String(item);
      })
      .filter(Boolean);

    return messages.length > 0 ? messages.join('\n') : fallback;
  }

  if (typeof detail === 'object') {
    const record = detail as Record<string, unknown>;
    if (typeof record.message === 'string' && record.message.trim()) return record.message;
    if (typeof record.msg === 'string' && record.msg.trim()) return record.msg;
    if (typeof record.detail === 'string' && record.detail.trim()) return record.detail;
    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }

  return String(detail);
}

export function toPositiveIntOrUndefined(value: unknown): number | undefined {
  if (value === null || value === undefined || value === '') return undefined;
  const num = Number(value);
  if (!Number.isFinite(num) || num <= 0) return undefined;
  return Math.round(num);
}

export function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === 'string' ? item.trim() : String(item ?? '').trim()))
    .filter(Boolean);
}

