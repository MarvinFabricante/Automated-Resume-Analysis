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

const VALID_RESUME_MIMES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
];
const VALID_RESUME_EXTENSIONS = /\.(pdf|docx|doc|txt)$/i;

/**
 * Validates a resume file for presence, non-zero size, supported type/extension, and size limit.
 * Returns an error message string if invalid, or null if valid.
 */
export function validateResumeFile(
  file: File | null | undefined,
  maxSizeMb = 5
): string | null {
  if (!file) {
    return 'No file was selected. Please choose a valid PDF, DOCX, DOC, or TXT resume file.';
  }
  if (file.size === 0) {
    return `"${file.name}" is empty (0 bytes). Please upload a valid non-empty resume file.`;
  }
  const hasValidMime = Boolean(file.type && VALID_RESUME_MIMES.includes(file.type));
  const hasValidExtension = VALID_RESUME_EXTENSIONS.test(file.name || '');
  if (!hasValidMime && !hasValidExtension) {
    const ext = file.name?.includes('.') ? `.${file.name.split('.').pop()}` : 'unknown format';
    return `Unsupported file format (${ext}). Please upload a PDF, DOCX, DOC, or TXT file.`;
  }
  const maxBytes = maxSizeMb * 1024 * 1024;
  if (file.size > maxBytes) {
    const actualMb = (file.size / (1024 * 1024)).toFixed(2);
    return `File size (${actualMb} MB) exceeds the ${maxSizeMb} MB limit. Please compress or choose a smaller file.`;
  }
  return null;
}

/**
 * Formats an Axios/network/API error from resume upload, replacement, or AI parsing
 * into a clear, actionable user-facing message covering validation errors,
 * background process issues, and request timeouts.
 */
export function formatUploadOrParseError(
  error: any,
  fallback = 'Failed to process the resume file. Please check the file and try again.'
): string {
  if (!error) return fallback;
  if (typeof error === 'string') return error;

  const code = error?.code || '';
  const status: number | undefined = error?.response?.status;
  const rawDetail = error?.response?.data?.detail ?? error?.response?.data?.message;
  const formattedDetail = rawDetail ? formatApiErrorDetail(rawDetail, '') : '';

  // Timeout errors
  if (
    code === 'ECONNABORTED' ||
    code === 'ETIMEDOUT' ||
    status === 408 ||
    status === 504 ||
    /timeout|timed out/i.test(error?.message || '')
  ) {
    return (
      formattedDetail ||
      'Resume processing timed out because the background extraction service took too long to respond. Please try again with a standard text-based PDF, DOCX, or TXT file.'
    );
  }

  // File size / payload too large
  if (status === 413) {
    return (
      formattedDetail ||
      'The selected file exceeds the maximum allowed upload size (5 MB). Please choose a smaller file.'
    );
  }

  // Unsupported media type / validation error
  if (status === 400 || status === 415 || status === 422) {
    return (
      formattedDetail ||
      'The resume could not be validated. Please ensure the file is a readable, non-password-protected PDF, DOCX, DOC, or TXT document under 5 MB.'
    );
  }

  // Rate limiting
  if (status === 429) {
    return (
      formattedDetail ||
      'Too many resume upload requests in a short period. Please wait a moment before replacing or uploading again.'
    );
  }

  // Server / background process failure
  if (status && status >= 500) {
    return (
      formattedDetail ||
      'A background processing error occurred while analyzing your resume. Please try again or use a different file format (PDF, DOCX, or TXT).'
    );
  }

  // Network / connection failure (no response received)
  if (!error?.response && (code === 'ERR_NETWORK' || /network error|failed to fetch/i.test(error?.message || ''))) {
    return 'Unable to reach the resume processing server. Please check your network connection and try again.';
  }

  if (formattedDetail) return formattedDetail;
  if (typeof error?.message === 'string' && error.message.trim()) return error.message;

  return fallback;
}


