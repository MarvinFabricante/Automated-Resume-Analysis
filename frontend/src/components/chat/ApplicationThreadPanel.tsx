import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  MessageSquare,
  Send,
  Lock,
  CheckCheck,
  Check,
  Clock,
  Paperclip,
  X,
  Flag,
  FileText,
  Download,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import toast from 'react-hot-toast';
import chatService, {
  ApplicationThreadItem,
  HRMessageTemplate,
  ThreadMessageItem,
} from '../../services/chatService';
import { WS_BASE_URL } from '../../services/api';
import { decodeToken } from '../../utils/token';

const MAX_MSG_LEN = 2000;
const MAX_ATT_BYTES = 5 * 1024 * 1024;
const ALLOWED_EXTS = ['pdf', 'png', 'jpg', 'jpeg'];

interface ApplicationThreadPanelProps {
  applicationId: number | string;
  jobTitle?: string;
  candidateName?: string;
  viewerRole?: 'CANDIDATE' | 'HR' | 'ADMIN';
  compact?: boolean;
  onThreadUpdated?: (thread: ApplicationThreadItem | null) => void;
  onOpenFullInbox?: (threadId?: number, applicationId?: number | string) => void;
}

const formatTime = (dateStr?: string | null) => {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
};

const formatDateLabel = (dateStr?: string | null) => {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
    const now = new Date();
    if (d.toDateString() === now.toDateString()) return 'Today';
    const yest = new Date(now);
    yest.setDate(now.getDate() - 1);
    if (d.toDateString() === yest.toDateString()) return 'Yesterday';
    return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return '';
  }
};

const ApplicationThreadPanel: React.FC<ApplicationThreadPanelProps> = ({
  applicationId,
  jobTitle,
  candidateName,
  viewerRole,
  compact = false,
  onThreadUpdated,
  onOpenFullInbox,
}) => {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const decoded = decodeToken(token);
  const currentUserId =
    typeof localStorage !== 'undefined'
      ? parseInt(localStorage.getItem('user_id') || '0', 10) || decoded?.id || 0
      : decoded?.id || 0;
  const resolvedRole = (
    viewerRole ||
    (typeof localStorage !== 'undefined' ? localStorage.getItem('role') : 'CANDIDATE') ||
    'CANDIDATE'
  ).toUpperCase();
  const isCandidate = resolvedRole === 'CANDIDATE';
  const isHR = resolvedRole === 'HR' || resolvedRole === 'ADMIN';

  const [loading, setLoading] = useState(true);
  const [exists, setExists] = useState(false);
  const [thread, setThread] = useState<ApplicationThreadItem | null>(null);
  const [messages, setMessages] = useState<ThreadMessageItem[]>([]);
  const [threadStatus, setThreadStatus] = useState<{
    is_closed: boolean;
    can_reply: boolean;
    reason?: string | null;
    closes_at?: string | null;
  }>({ is_closed: false, can_reply: !isCandidate, reason: null, closes_at: null });

  const [templates, setTemplates] = useState<HRMessageTemplate[]>([]);
  const [inputText, setInputText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSending, setIsSending] = useState(false);

  const [reportTarget, setReportTarget] = useState<ThreadMessageItem | null>(null);
  const [reportReason, setReportReason] = useState('');
  const [isReporting, setIsReporting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const loadThread = useCallback(async () => {
    if (!applicationId || !token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await chatService.getApplicationThread(applicationId, token, true);
      const data = res.data;
      setExists(Boolean(data.exists));
      setThread(data.thread || null);
      setMessages(Array.isArray(data.messages) ? data.messages : []);
      if (data.thread_status) {
        setThreadStatus(data.thread_status);
      }
      if (onThreadUpdated) {
        onThreadUpdated(data.thread || null);
      }
    } catch (err) {
      console.error('Failed to load application thread:', err);
    } finally {
      setLoading(false);
    }
  }, [applicationId, token, onThreadUpdated]);

  useEffect(() => {
    loadThread();
  }, [loadThread]);

  // Load optional plain-text HR templates
  useEffect(() => {
    if (!isHR || !token) return;
    chatService
      .getTemplates(candidateName || thread?.candidate_name, jobTitle || thread?.job_title, token)
      .then((res) => {
        if (Array.isArray(res.data)) setTemplates(res.data);
      })
      .catch(() => {});
  }, [isHR, token, candidateName, jobTitle, thread?.candidate_name, thread?.job_title]);

  // Real-time WebSocket updates for this application thread
  useEffect(() => {
    if (!token || !applicationId) return;
    let active = true;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${WS_BASE_URL}/chat/ws?token=${encodeURIComponent(token)}`);
      ws.onmessage = (event) => {
        if (!active) return;
        try {
          const data = JSON.parse(event.data);
          if (
            data.type === 'new_message' &&
            String(data.application_id) === String(applicationId)
          ) {
            setExists(true);
            setMessages((prev) => {
              if (prev.some((m) => String(m.id) === String(data.id))) return prev;
              return [...prev, data];
            });
            // If HR just started the conversation, allow applicant to reply now
            if (isCandidate && (data.sender_role || '').toUpperCase() !== 'CANDIDATE') {
              setThreadStatus((prev) => ({
                ...prev,
                can_reply: !prev.is_closed,
                reason: prev.is_closed ? prev.reason : null,
              }));
            }
          } else if (
            data.type === 'messages_seen' &&
            String(data.application_id) === String(applicationId)
          ) {
            const seenIds = new Set((data.message_ids || []).map((id: any) => String(id)));
            setMessages((prev) =>
              prev.map((m) =>
                seenIds.has(String(m.id))
                  ? { ...m, is_read: true, read_at: data.read_at || new Date().toISOString() }
                  : m
              )
            );
          }
        } catch {
          // ignore malformed WS frames
        }
      };
    } catch {
      // ignore WS failure; HTTP polling/send still works
    }
    return () => {
      active = false;
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
    };
  }, [token, applicationId, isCandidate]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      toast.error('Only PDF, PNG, and JPG attachments are allowed.');
      e.target.value = '';
      return;
    }
    if (file.size > MAX_ATT_BYTES) {
      toast.error('Attachment exceeds the 5 MB size limit.');
      e.target.value = '';
      return;
    }
    setSelectedFile(file);
  };

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = inputText.trim();
    if ((!trimmed && !selectedFile) || isSending) return;
    if (trimmed.length > MAX_MSG_LEN) {
      toast.error(`Message must be ${MAX_MSG_LEN.toLocaleString()} characters or fewer.`);
      return;
    }

    setIsSending(true);
    try {
      const res = thread?.id
        ? await chatService.sendThreadMessage(thread.id, trimmed, selectedFile, 'general', token)
        : await chatService.sendApplicationMessage(applicationId, trimmed, selectedFile, 'general', token);

      const created: ThreadMessageItem = res.data;
      setExists(true);
      setMessages((prev) =>
        prev.some((m) => String(m.id) === String(created.id)) ? prev : [...prev, created]
      );
      setInputText('');
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';

      // Refresh thread metadata if it was just started
      if (!thread) {
        await loadThread();
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Could not send message. Please try again.';
      toast.error(detail);
    } finally {
      setIsSending(false);
    }
  };

  const handleDownloadAttachment = async (msg: ThreadMessageItem) => {
    if (!msg.id) return;
    try {
      const res = await chatService.downloadAttachment(msg.id, token);
      const blob = new Blob([res.data], { type: msg.attachment_type || 'application/octet-stream' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = msg.attachment_name || 'attachment';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error('Could not download attachment.');
    }
  };

  const handleSubmitReport = async () => {
    if (!reportTarget?.id || reportReason.trim().length < 3) {
      toast.error('Please enter a short reason for reporting this message.');
      return;
    }
    setIsReporting(true);
    try {
      const res = await chatService.reportMessage(reportTarget.id, reportReason.trim(), token);
      setMessages((prev) =>
        prev.map((m) => (String(m.id) === String(reportTarget.id) ? { ...m, is_reported: true } : m))
      );
      toast.success(res.data?.detail || 'Message reported to administrators.');
      setReportTarget(null);
      setReportReason('');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Could not report message.');
    } finally {
      setIsReporting(false);
    }
  };

  const displayPosition = thread?.job_title || jobTitle || 'Position';

  // Applicant view BEFORE HR starts the conversation:
  // No compose box, no empty chat, no "Message HR" button.
  if (isCandidate && !loading && !exists) {
    return (
      <div
        id="application-messages-section"
        className="bg-white border border-slate-200/80 rounded-3xl p-5 sm:p-6 shadow-xs"
      >
        <div className="flex items-start gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center shrink-0">
            <MessageSquare size={18} />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-black text-slate-900 tracking-tight">
              Messages for {displayPosition}
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              HR will message you here if they need anything. You will get a notification.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      id="application-messages-section"
      className={`bg-white border border-slate-200/80 rounded-3xl shadow-xs flex flex-col overflow-hidden ${
        compact ? 'max-h-[540px]' : ''
      }`}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50/60">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-rose-50 text-[#D60041] border border-rose-100 flex items-center justify-center shrink-0">
            <MessageSquare size={17} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm sm:text-base font-black text-slate-900 tracking-tight truncate">
                {isCandidate ? 'Message from HR' : (candidateName || thread?.candidate_name || 'Applicant')}
              </h3>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 truncate max-w-[220px]">
                {displayPosition}
              </span>
              {threadStatus.is_closed && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                  Closed
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-500 font-medium mt-0.5">
              {isCandidate
                ? 'Replies here stay tied to this application only.'
                : 'Messages in this thread stay tied to this application only.'}
            </p>
          </div>
        </div>

        {onOpenFullInbox && (
          <button
            type="button"
            onClick={() => onOpenFullInbox(thread?.id, applicationId)}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-[#D60041] hover:text-slate-900 px-3 py-1.5 rounded-xl bg-white border border-slate-200 hover:border-slate-300 transition-colors cursor-pointer"
          >
            <span>Open in Messages</span>
            <ExternalLink size={12} />
          </button>
        )}
      </div>

      {/* Messages List */}
      <div
        className={`flex-1 overflow-y-auto p-4 sm:p-5 space-y-3 bg-slate-50/40 ${
          compact ? 'min-h-[220px] max-h-[300px]' : 'min-h-[240px] max-h-[420px]'
        }`}
      >
        {loading ? (
          <div className="flex flex-col items-center justify-center py-10 text-slate-400 text-xs">
            <div className="w-6 h-6 border-2 border-slate-200 border-t-[#D60041] rounded-full animate-spin mb-2" />
            <span>Loading conversation...</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-8 px-4 space-y-1">
            <p className="text-xs sm:text-sm font-bold text-slate-700">
              Start the conversation for {displayPosition}
            </p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Once you send the first message, the applicant will receive a notification and will be able to reply in this thread.
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const isMe = msg.sender_id === currentUserId;
            const senderRole = (msg.sender_role || '').toUpperCase();
            const isFromHR = senderRole === 'HR' || senderRole === 'ADMIN' || senderRole === 'SUPERADMIN';
            const prev = idx > 0 ? messages[idx - 1] : null;
            const dateGroup = formatDateLabel(msg.timestamp);
            const prevDateGroup = prev ? formatDateLabel(prev.timestamp) : null;
            const showDate = !prev || dateGroup !== prevDateGroup;

            return (
              <React.Fragment key={msg.id || msg.client_id || idx}>
                {showDate && (
                  <div className="flex justify-center my-2">
                    <span className="px-2.5 py-0.5 bg-white border border-slate-200 rounded-full text-[10px] font-semibold text-slate-500">
                      {dateGroup}
                    </span>
                  </div>
                )}
                <div className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                  {/* Always show which HR user wrote each HR message */}
                  {(isFromHR || !isMe) && msg.sender_name && (
                    <span className="text-[11px] font-bold text-slate-600 mb-1 px-1">
                      {msg.sender_name}
                      {isFromHR ? ' • HR' : ''}
                    </span>
                  )}

                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs sm:text-sm leading-relaxed whitespace-pre-wrap break-words shadow-2xs ${
                      isMe
                        ? 'bg-[#D60041] text-white rounded-br-sm'
                        : 'bg-white text-slate-800 border border-slate-200/80 rounded-bl-sm'
                    }`}
                  >
                    {msg.content && <div>{msg.content}</div>}

                    {msg.attachment_name && (
                      <button
                        type="button"
                        onClick={() => handleDownloadAttachment(msg)}
                        className={`mt-2 flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors cursor-pointer ${
                          isMe
                            ? 'bg-white/15 border-white/25 text-white hover:bg-white/25'
                            : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                        }`}
                      >
                        <FileText size={13} />
                        <span className="truncate max-w-[200px]">{msg.attachment_name}</span>
                        <Download size={12} />
                      </button>
                    )}
                  </div>

                  <div className="flex items-center gap-2 mt-1 px-1 text-[10px] text-slate-400 font-medium">
                    <span>{formatTime(msg.timestamp)}</span>
                    {isMe && (
                      msg.is_optimistic ? (
                        <span className="inline-flex items-center gap-0.5 text-pink-600">
                          <Clock size={10} className="animate-spin" /> Sending
                        </span>
                      ) : msg.is_read ? (
                        <span className="inline-flex items-center gap-0.5 text-emerald-600 font-semibold" title={msg.read_at ? `Seen ${formatTime(msg.read_at)}` : 'Seen'}>
                          <CheckCheck size={12} /> Seen
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-0.5 text-slate-400">
                          <Check size={11} /> Sent
                        </span>
                      )
                    )}
                    {isCandidate && !isMe && msg.id && (
                      msg.is_reported ? (
                        <span className="text-amber-600 font-semibold">Reported</span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            setReportTarget(msg);
                            setReportReason('');
                          }}
                          className="inline-flex items-center gap-1 text-slate-400 hover:text-rose-600 transition-colors cursor-pointer"
                          title="Report this message"
                        >
                          <Flag size={10} />
                          <span>Report</span>
                        </button>
                      )
                    )}
                  </div>
                </div>
              </React.Fragment>
            );
          })
        )}
        <div ref={endRef} />
      </div>

      {/* Compose Area or Read-only Closure Banner */}
      {!threadStatus.is_closed && (isHR || threadStatus.can_reply) ? (
        <form onSubmit={handleSend} className="p-3.5 sm:p-4 bg-white border-t border-slate-100 space-y-2.5">
          {/* Optional editable plain-text templates for HR */}
          {isHR && templates.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1 mr-1">
                <Sparkles size={11} /> Templates:
              </span>
              {templates.map((tpl) => (
                <button
                  key={tpl.key}
                  type="button"
                  onClick={() => setInputText(tpl.body)}
                  className="text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-rose-50 text-slate-700 hover:text-[#D60041] border border-slate-200 hover:border-rose-200 transition-colors cursor-pointer"
                >
                  {tpl.label}
                </button>
              ))}
            </div>
          )}

          {threadStatus.closes_at && (
            <p className="text-[11px] text-slate-400">
              This conversation stays open until {new Date(threadStatus.closes_at).toLocaleDateString()}.
            </p>
          )}

          {selectedFile && (
            <div className="flex items-center justify-between gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700">
              <span className="flex items-center gap-1.5 truncate">
                <FileText size={13} className="text-[#D60041] shrink-0" />
                <span className="truncate font-semibold">{selectedFile.name}</span>
              </span>
              <button
                type="button"
                onClick={() => {
                  setSelectedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                className="p-0.5 text-slate-400 hover:text-slate-700 cursor-pointer"
                aria-label="Remove attachment"
              >
                <X size={13} />
              </button>
            </div>
          )}

          <div className="flex items-end gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              className="hidden"
              onChange={handleFileSelect}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              title="Attach PDF, PNG, or JPG (max 5 MB)"
              aria-label="Attach file"
              className="p-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-500 hover:text-slate-800 transition-colors cursor-pointer shrink-0"
            >
              <Paperclip size={16} />
            </button>

            <div className="flex-1 min-w-0">
              <textarea
                rows={2}
                value={inputText}
                maxLength={MAX_MSG_LEN}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder={
                  isHR && !exists
                    ? 'Write your first message to start the conversation...'
                    : 'Write a plain-text reply...'
                }
                className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-3.5 py-2 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-[#D60041] focus:ring-2 focus:ring-pink-100 outline-none resize-none"
              />
              {inputText.length > MAX_MSG_LEN - 250 && (
                <p className="text-[10px] text-slate-400 text-right mt-0.5">
                  {inputText.length} / {MAX_MSG_LEN}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSending || (!inputText.trim() && !selectedFile)}
              className="p-2.5 sm:px-4 sm:py-2.5 bg-[#D60041] hover:bg-[#b50037] text-white rounded-xl font-bold text-xs flex items-center gap-1.5 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0"
            >
              <Send size={15} />
              <span className="hidden sm:inline">{isSending ? 'Sending...' : 'Send'}</span>
            </button>
          </div>
        </form>
      ) : (
        <div className="p-3.5 bg-slate-50 border-t border-slate-100 flex items-center justify-center">
          <div className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-600">
            <Lock size={13} className="text-[#D60041] shrink-0" />
            <span>{threadStatus.reason || 'This conversation is closed'}</span>
          </div>
        </div>
      )}

      {/* Report Message Modal (Applicants) */}
      {reportTarget && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-5 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-black text-slate-900 flex items-center gap-2">
                <Flag size={15} className="text-rose-600" />
                Report Message
              </h4>
              <button
                type="button"
                onClick={() => setReportTarget(null)}
                className="p-1 text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
            <p className="text-xs text-slate-600">
              Let our administrators know why you are reporting this message.
            </p>
            <textarea
              rows={3}
              maxLength={500}
              value={reportReason}
              onChange={(e) => setReportReason(e.target.value)}
              placeholder="Briefly describe the issue..."
              className="w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-900 focus:bg-white focus:border-[#D60041] outline-none"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setReportTarget(null)}
                className="px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isReporting || reportReason.trim().length < 3}
                onClick={handleSubmitReport}
                className="px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold disabled:opacity-50 cursor-pointer"
              >
                {isReporting ? 'Submitting...' : 'Submit Report'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApplicationThreadPanel;
