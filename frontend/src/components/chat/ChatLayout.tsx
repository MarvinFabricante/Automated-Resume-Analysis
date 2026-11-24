import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Search,
  Send,
  ArrowLeft,
  X,
  Lock,
  CheckCheck,
  Check,
  Clock,
  MessageSquare,
  Archive,
  ArchiveRestore,
  Trash2,
  AlertTriangle,
  Paperclip,
  FileText,
  Download,
  Flag,
  Briefcase,
  Users,
  Sparkles,
} from 'lucide-react';
import toast from 'react-hot-toast';
import chatService, {
  ApplicationThreadItem,
  HRMessageTemplate,
  ThreadMessageItem,
} from '../../services/chatService';
import { useSelector, useDispatch } from 'react-redux';
import { WS_BASE_URL } from '../../services/api';
import { RootState } from '../../redux/store';
import { setUnreadMessagesCount } from '../../redux/slices/notificationSlice';
import { ChatContactItem, ChatMessageItem } from '../layout/ChatWidget';
import { decodeToken } from '../../utils/token';

interface ChatLayoutProps {
  isFullPage?: boolean;
}

const MAX_MSG_LEN = 2000;
const MAX_ATT_BYTES = 5 * 1024 * 1024;
const ALLOWED_EXTS = ['pdf', 'png', 'jpg', 'jpeg'];

const formatMessageTime = (dateStr?: string | null) => {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
};

const formatContactDate = (dateStr?: string | null) => {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
    const now = new Date();
    if (d.toDateString() === now.toDateString()) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    }
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
};

const getMessageDateGroup = (dateStr?: string | null) => {
  if (!dateStr) return 'Today';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return 'Today';
    const now = new Date();
    if (d.toDateString() === now.toDateString()) return 'Today';
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
    return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return 'Today';
  }
};

const ChatLayout: React.FC<ChatLayoutProps> = ({ isFullPage = true }) => {
  const dispatch = useDispatch();
  const { profileImageUrl: myProfileImage } = useSelector((state: RootState) => state.auth);

  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const decodedToken = decodeToken(token);
  const currentUserId =
    typeof localStorage !== 'undefined'
      ? parseInt(localStorage.getItem('user_id') || '0', 10) || decodedToken?.id || 0
      : decodedToken?.id || 0;
  const currentUserRole = (
    (typeof localStorage !== 'undefined' ? localStorage.getItem('role') : '') ||
    decodedToken?.role ||
    'Guest'
  ).toUpperCase();
  const isCandidate = currentUserRole === 'CANDIDATE';
  const isStaff = currentUserRole === 'HR' || currentUserRole === 'ADMIN' || currentUserRole === 'SUPERADMIN';

  // Mode: Applicants only ever use 'threads' (HR-started application threads).
  // HR / Admin can switch between 'threads' (Application Threads) and 'team' (Internal HR/Admin chat).
  const [inboxMode, setInboxMode] = useState<'threads' | 'team'>('threads');
  const [view, setView] = useState<'list' | 'chat'>('list');
  const [activeTab, setActiveTab] = useState<'all' | 'archived'>('all');
  const [search, setSearch] = useState('');

  // Application threads state
  const [threads, setThreads] = useState<ApplicationThreadItem[]>([]);
  const [activeThread, setActiveThread] = useState<ApplicationThreadItem | null>(null);
  const [threadMessages, setThreadMessages] = useState<ThreadMessageItem[]>([]);
  const [threadStatus, setThreadStatus] = useState<{
    is_closed: boolean;
    can_reply: boolean;
    reason?: string | null;
    closes_at?: string | null;
  }>({ is_closed: false, can_reply: true, reason: null, closes_at: null });
  const [templates, setTemplates] = useState<HRMessageTemplate[]>([]);

  // Legacy team contacts state (HR / Admin internal chat only)
  const [teamContacts, setTeamContacts] = useState<ChatContactItem[]>([]);
  const [activeContact, setActiveContact] = useState<ChatContactItem | null>(null);
  const [teamMessages, setTeamMessages] = useState<ChatMessageItem[]>([]);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Composer state
  const [inputMessage, setInputMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [loading, setLoading] = useState(false);

  // Report modal (for applicants)
  const [reportTarget, setReportTarget] = useState<ThreadMessageItem | null>(null);
  const [reportReason, setReportReason] = useState('');
  const [isReporting, setIsReporting] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeThreadRef = useRef<ApplicationThreadItem | null>(null);
  const activeContactRef = useRef<ChatContactItem | null>(null);
  const autoOpenedKeyRef = useRef<string | null>(null);

  useEffect(() => {
    activeThreadRef.current = activeThread;
  }, [activeThread]);

  useEffect(() => {
    activeContactRef.current = activeContact;
  }, [activeContact]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [threadMessages.length, teamMessages.length]);

  const fetchThreads = useCallback(async () => {
    if (!token) return;
    try {
      const res = await chatService.getThreads(token, search);
      const list: ApplicationThreadItem[] = res.data?.threads || [];
      setThreads(list);
      const totalUnread = Number(res.data?.total_unread ?? list.reduce((a, t) => a + (t.unread_count || 0), 0));
      dispatch(setUnreadMessagesCount(totalUnread));

      // Auto-open thread if navigated with ?thread=<id> or ?application=<appId>
      if (typeof window !== 'undefined' && !activeThreadRef.current) {
        const params = new URLSearchParams(window.location.search);
        const threadParam = (params.get('thread') || '').trim();
        const appParam = (params.get('application') || '').trim();
        const lookupKey = threadParam ? `t:${threadParam}` : appParam ? `a:${appParam}` : '';
        if (lookupKey && autoOpenedKeyRef.current !== lookupKey) {
          const matched = threadParam
            ? list.find((t) => String(t.id) === threadParam)
            : list.find((t) => String(t.application_id) === appParam);
          if (matched) {
            autoOpenedKeyRef.current = lookupKey;
            openThread(matched);
          } else if (appParam && isStaff) {
            autoOpenedKeyRef.current = lookupKey;
            try {
              const detailRes = await chatService.getApplicationThread(appParam, token, true);
              if (detailRes.data?.thread) {
                openThread(detailRes.data.thread);
              }
            } catch {
              // ignore
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch application threads:', error);
    }
  }, [token, search, dispatch, isStaff]);

  const fetchTeamContacts = useCallback(async () => {
    if (!token || !isStaff) return;
    try {
      const res = await chatService.getContacts(token, search);
      const users: ChatContactItem[] = (res.data?.users || []).filter(
        (u: ChatContactItem) => (u.role || '').toUpperCase() !== 'CANDIDATE'
      );
      setTeamContacts(users);
    } catch (error) {
      console.error('Failed to fetch team contacts:', error);
    }
  }, [token, isStaff, search]);

  useEffect(() => {
    fetchThreads();
    if (isStaff) fetchTeamContacts();
  }, [fetchThreads, fetchTeamContacts, isStaff]);

  // Load templates for HR when active thread changes
  useEffect(() => {
    if (!isStaff || !token || !activeThread) return;
    chatService
      .getTemplates(activeThread.candidate_name, activeThread.job_title, token)
      .then((res) => {
        if (Array.isArray(res.data)) setTemplates(res.data);
      })
      .catch(() => {});
  }, [isStaff, token, activeThread?.id, activeThread?.candidate_name, activeThread?.job_title]);

  // Keep latest fetch helpers in refs so typing in search never tears down & reconnects the WebSocket
  const fetchThreadsRef = useRef(fetchThreads);
  const fetchTeamContactsRef = useRef(fetchTeamContacts);
  useEffect(() => {
    fetchThreadsRef.current = fetchThreads;
  }, [fetchThreads]);
  useEffect(() => {
    fetchTeamContactsRef.current = fetchTeamContacts;
  }, [fetchTeamContacts]);

  // WebSocket live updates
  useEffect(() => {
    if (!token) return;
    let shouldReconnect = true;
    let reconnectTimer: any = null;

    const connectWebSocket = () => {
      if (!shouldReconnect) return;
      const ws = new WebSocket(`${WS_BASE_URL}/chat/ws?token=${encodeURIComponent(token)}`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'new_message') {
            if (data.thread_id || data.application_id) {
              const cur = activeThreadRef.current;
              if (
                cur &&
                (String(cur.id) === String(data.thread_id) ||
                  String(cur.application_id) === String(data.application_id))
              ) {
                setThreadMessages((prev) => {
                  if (prev.some((m) => String(m.id) === String(data.id))) return prev;
                  return [...prev, data];
                });
              }
              fetchThreadsRef.current();
            } else {
              const curContact = activeContactRef.current;
              if (
                curContact &&
                (data.sender_id === curContact.id || data.receiver_id === curContact.id)
              ) {
                setTeamMessages((prev) => {
                  if (prev.some((m) => String(m.id) === String(data.id))) return prev;
                  return [...prev, data];
                });
              }
              if (isStaff) fetchTeamContactsRef.current();
            }
          } else if (data.type === 'messages_seen') {
            const seenIds = new Set((data.message_ids || []).map((id: any) => String(id)));
            setThreadMessages((prev) =>
              prev.map((m) =>
                seenIds.has(String(m.id))
                  ? { ...m, is_read: true, read_at: data.read_at || new Date().toISOString() }
                  : m
              )
            );
          } else if (data.type === 'conversation_closed' || data.type === 'error') {
            if (data.detail) toast.error(data.detail);
          } else if (data.type === 'status') {
            setTeamContacts((prev) =>
              prev.map((c) => (c.id === data.user_id ? { ...c, is_online: data.is_online } : c))
            );
          }
        } catch {
          // ignore
        }
      };

      ws.onclose = () => {
        if (shouldReconnect) {
          reconnectTimer = setTimeout(connectWebSocket, 5000);
        }
      };
    };

    connectWebSocket();

    return () => {
      shouldReconnect = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          // ignore
        }
      }
    };
  }, [token, isStaff]);

  const openThread = async (thread: ApplicationThreadItem) => {
    setInboxMode('threads');
    setActiveContact(null);
    setActiveThread(thread);
    setView('chat');
    setLoading(true);
    setSelectedFile(null);
    try {
      const res = await chatService.getThreadMessages(thread.id, token, true);
      const data = res.data;
      if (data?.thread) setActiveThread(data.thread);
      setThreadMessages(Array.isArray(data?.messages) ? data.messages : []);
      if (data?.thread_status) {
        setThreadStatus(data.thread_status);
      } else {
        setThreadStatus({
          is_closed: thread.is_closed,
          can_reply: thread.can_reply,
          reason: thread.closure_reason,
          closes_at: thread.closes_at,
        });
      }
      setThreads((prev) => {
        const updated = prev.map((t) => (t.id === thread.id ? { ...t, unread_count: 0 } : t));
        const total = updated.reduce((a, t) => a + (t.unread_count || 0), 0);
        dispatch(setUnreadMessagesCount(total));
        return updated;
      });
    } catch (error) {
      console.error('Failed to load thread messages:', error);
      toast.error('Could not load conversation.');
    } finally {
      setLoading(false);
    }
  };

  const openTeamChat = async (contact: ChatContactItem) => {
    setActiveThread(null);
    setActiveContact(contact);
    setView('chat');
    setLoading(true);
    try {
      const res = await chatService.getMessages(contact.id, token);
      setTeamMessages(res.data || []);
      setTeamContacts((prev) =>
        prev.map((c) => (c.id === contact.id ? { ...c, unread_count: 0 } : c))
      );
    } catch (error) {
      console.error('Failed to fetch team messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleArchiveThread = async (thread: ApplicationThreadItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const nextArchived = !thread.is_archived;
    setThreads((prev) =>
      prev.map((t) => (t.id === thread.id ? { ...t, is_archived: nextArchived } : t))
    );
    if (activeThread?.id === thread.id) {
      setActiveThread((prev) => (prev ? { ...prev, is_archived: nextArchived } : null));
    }
    try {
      if (nextArchived) {
        await chatService.archiveThread(thread.id, token);
        toast.success('Conversation archived');
      } else {
        await chatService.unarchiveThread(thread.id, token);
        toast.success('Conversation moved to Inbox');
      }
    } catch {
      toast.error('Could not update archive status');
      fetchThreads();
    }
  };

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
      toast.error('Attachment exceeds the 5 MB limit.');
      e.target.value = '';
      return;
    }
    setSelectedFile(file);
  };

  const handleSend = async () => {
    const trimmed = inputMessage.trim();
    if (isSending) return;

    if (inboxMode === 'threads' && activeThread) {
      if (!trimmed && !selectedFile) return;
      if (trimmed.length > MAX_MSG_LEN) {
        toast.error(`Message must be ${MAX_MSG_LEN.toLocaleString()} characters or fewer.`);
        return;
      }
      setIsSending(true);
      try {
        const res = await chatService.sendThreadMessage(
          activeThread.id,
          trimmed,
          selectedFile,
          'general',
          token
        );
        const created: ThreadMessageItem = res.data;
        setThreadMessages((prev) =>
          prev.some((m) => String(m.id) === String(created.id)) ? prev : [...prev, created]
        );
        setInputMessage('');
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
        fetchThreads();
      } catch (err: any) {
        const detail = err?.response?.data?.detail || 'Could not send message.';
        toast.error(detail);
        if (err?.response?.status === 403 && detail.toLowerCase().includes('closed')) {
          setThreadStatus({ is_closed: true, can_reply: false, reason: detail, closes_at: null });
        }
      } finally {
        setIsSending(false);
      }
    } else if (inboxMode === 'team' && activeContact) {
      if (!trimmed) return;
      setIsSending(true);
      try {
        const res = await chatService.sendMessage(activeContact.id, trimmed, token);
        setTeamMessages((prev) =>
          prev.some((m) => String(m.id) === String(res.data?.id)) ? prev : [...prev, res.data]
        );
        setInputMessage('');
        fetchTeamContacts();
      } catch (err: any) {
        toast.error(err?.response?.data?.detail || 'Could not send message.');
      } finally {
        setIsSending(false);
      }
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
      toast.error('Please enter a short reason.');
      return;
    }
    setIsReporting(true);
    try {
      const res = await chatService.reportMessage(reportTarget.id, reportReason.trim(), token);
      setThreadMessages((prev) =>
        prev.map((m) => (String(m.id) === String(reportTarget.id) ? { ...m, is_reported: true } : m))
      );
      toast.success(res.data?.detail || 'Message reported.');
      setReportTarget(null);
      setReportReason('');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Could not report message.');
    } finally {
      setIsReporting(false);
    }
  };

  const handleDeleteTeamConversation = async () => {
    if (!activeContact) return;
    setIsDeleting(true);
    try {
      await chatService.deleteConversation(activeContact.id, token);
      setTeamMessages([]);
      setShowDeleteModal(false);
      toast.success('Conversation deleted');
      fetchTeamContacts();
    } catch {
      toast.error('Failed to delete conversation');
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredThreads = threads.filter((t) =>
    activeTab === 'archived' ? t.is_archived : !t.is_archived
  );
  const activeThreadCount = threads.filter((t) => !t.is_archived).length;
  const archivedThreadCount = threads.filter((t) => t.is_archived).length;
  const totalUnread = threads.reduce((sum, t) => sum + (t.unread_count || 0), 0);

  return (
    <div
      className={`flex bg-white rounded-2xl sm:rounded-3xl md:rounded-[32px] border border-gray-100 shadow-xs overflow-hidden font-['Inter'] w-full relative ${
        isFullPage
          ? 'h-[calc(100dvh-175px)] sm:h-[calc(100dvh-200px)] md:h-[calc(100vh-210px)] min-h-[460px] max-h-full'
          : 'h-[600px]'
      }`}
    >
      {/* Left Sidebar: Combined Inbox */}
      <div
        className={`w-full md:w-[350px] lg:w-[390px] flex flex-col border-r border-gray-100 shrink-0 bg-white ${
          view === 'chat' ? 'hidden md:flex' : 'flex'
        }`}
      >
        <div className="p-3.5 sm:p-5 border-b border-gray-100 bg-white space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h3 className="text-lg sm:text-xl font-black text-gray-900 tracking-tight">
                Messages
              </h3>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                {inboxMode === 'threads' ? threads.length : teamContacts.length}
              </span>
            </div>
            {totalUnread > 0 && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-50 text-[#D60041] border border-rose-100">
                {totalUnread} unread
              </span>
            )}
          </div>

          {/* Staff mode switcher: Applicant Threads vs Team Chat */}
          {isStaff && (
            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl">
              <button
                type="button"
                onClick={() => {
                  setInboxMode('threads');
                  setActiveContact(null);
                  setView('list');
                }}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  inboxMode === 'threads'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Briefcase size={12} />
                <span>Applicants</span>
                {totalUnread > 0 && (
                  <span className="px-1.5 rounded-full bg-[#D60041] text-white text-[10px]">
                    {totalUnread}
                  </span>
                )}
              </button>
              <button
                type="button"
                onClick={() => {
                  setInboxMode('team');
                  setActiveThread(null);
                  setView('list');
                }}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  inboxMode === 'team'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Users size={12} />
                <span>Team</span>
              </button>
            </div>
          )}

          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 h-4 w-4 pointer-events-none" />
            <input
              type="text"
              placeholder={
                inboxMode === 'threads'
                  ? isCandidate
                    ? 'Search by position or message...'
                    : 'Search applicant or position...'
                  : 'Search team member...'
              }
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-gray-50 border border-gray-100 rounded-xl py-2 pl-10 pr-9 text-xs sm:text-sm focus:bg-white focus:border-[#D60041] focus:ring-2 focus:ring-pink-100 outline-none font-medium text-gray-800"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 cursor-pointer"
                aria-label="Clear search"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Inbox vs Archived (for application threads) */}
          {inboxMode === 'threads' && (
            <div className="flex items-center gap-1 p-1 bg-gray-100/80 rounded-xl">
              <button
                type="button"
                onClick={() => setActiveTab('all')}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  activeTab === 'all'
                    ? 'bg-white text-gray-900 shadow-2xs'
                    : 'text-gray-500 hover:text-gray-800'
                }`}
              >
                <span>Inbox</span>
                <span className="text-[10px] px-1.5 rounded-full bg-gray-200/70 text-gray-600">
                  {activeThreadCount}
                </span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('archived')}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  activeTab === 'archived'
                    ? 'bg-white text-gray-900 shadow-2xs'
                    : 'text-gray-500 hover:text-gray-800'
                }`}
              >
                <Archive size={12} />
                <span>Archived</span>
                {archivedThreadCount > 0 && (
                  <span className="text-[10px] px-1.5 rounded-full bg-amber-100 text-amber-800 font-bold">
                    {archivedThreadCount}
                  </span>
                )}
              </button>
            </div>
          )}
        </div>

        {/* List Body */}
        <div className="flex-1 overflow-y-auto divide-y divide-gray-50 bg-white">
          {inboxMode === 'threads' ? (
            filteredThreads.length > 0 ? (
              filteredThreads.map((thr) => (
                <div
                  key={thr.id}
                  onClick={() => openThread(thr)}
                  className={`p-3.5 sm:p-4 flex items-start gap-3 cursor-pointer transition-all relative group ${
                    activeThread?.id === thr.id
                      ? 'bg-pink-50/50'
                      : 'hover:bg-gray-50/80 active:bg-gray-100/60'
                  }`}
                >
                  <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-pink-50 to-rose-100/60 border border-rose-100 flex items-center justify-center text-[#D60041] font-black text-sm shrink-0">
                    {isCandidate ? (
                      <Briefcase size={18} />
                    ) : (
                      (thr.candidate_name || 'A').charAt(0).toUpperCase()
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <h4 className="text-xs sm:text-sm font-black text-gray-900 truncate">
                        {isCandidate ? thr.job_title : thr.candidate_name}
                      </h4>
                      {thr.last_message_time && (
                        <span className="text-[10px] text-gray-400 font-semibold shrink-0">
                          {formatContactDate(thr.last_message_time)}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-slate-100 text-slate-700 truncate max-w-[180px]">
                        {isCandidate ? 'Message from HR' : thr.job_title}
                      </span>
                      {thr.is_closed && (
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-200 text-slate-600 uppercase">
                          Closed
                        </span>
                      )}
                    </div>

                    <div className="flex items-center justify-between gap-2">
                      <p
                        className={`text-xs truncate ${
                          thr.unread_count > 0
                            ? 'text-gray-900 font-bold'
                            : 'text-gray-500 font-normal'
                        }`}
                      >
                        {thr.last_sender_name ? `${thr.last_sender_name}: ` : ''}
                        {thr.last_message || 'Conversation started'}
                      </p>

                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          type="button"
                          onClick={(e) => handleToggleArchiveThread(thr, e)}
                          className="opacity-0 group-hover:opacity-100 focus:opacity-100 p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-200/60 transition-all cursor-pointer"
                          title={thr.is_archived ? 'Unarchive' : 'Archive'}
                        >
                          {thr.is_archived ? <ArchiveRestore size={13} /> : <Archive size={13} />}
                        </button>
                        {thr.unread_count > 0 && (
                          <span className="min-w-[18px] h-[18px] bg-[#D60041] rounded-full flex items-center justify-center text-[10px] text-white font-black px-1.5">
                            {thr.unread_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {activeThread?.id === thr.id && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-[#D60041] rounded-r-full hidden md:block" />
                  )}
                </div>
              ))
            ) : (
              <div className="p-8 text-center space-y-2">
                <div className="w-12 h-12 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto text-gray-300">
                  {activeTab === 'archived' ? <Archive size={22} /> : <MessageSquare size={22} />}
                </div>
                <p className="text-xs sm:text-sm font-bold text-gray-700">
                  {activeTab === 'archived'
                    ? 'No archived conversations'
                    : isCandidate
                    ? 'No messages from HR yet'
                    : 'No applicant conversations yet'}
                </p>
                <p className="text-xs text-gray-500 leading-relaxed max-w-[260px] mx-auto">
                  {activeTab === 'archived'
                    ? 'Conversations you archive will appear here.'
                    : isCandidate
                    ? 'HR will message you here if they need anything. You will get a notification.'
                    : 'Start a conversation from any applicant profile, application details, shortlist roster, or interview view using "Message applicant".'}
                </p>
              </div>
            )
          ) : teamContacts.length > 0 ? (
            teamContacts.map((contact) => (
              <div
                key={contact.id}
                onClick={() => openTeamChat(contact)}
                className={`p-3.5 sm:p-4 flex items-center gap-3 cursor-pointer transition-all ${
                  activeContact?.id === contact.id ? 'bg-pink-50/50' : 'hover:bg-gray-50/80'
                }`}
              >
                <div className="w-10 h-10 rounded-xl bg-rose-50 text-[#D60041] font-black flex items-center justify-center shrink-0">
                  {contact.fullname?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="text-xs sm:text-sm font-bold text-gray-900 truncate">
                      {contact.fullname}
                    </h4>
                    <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                      {contact.role}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 truncate mt-0.5">
                    {contact.last_message || 'Team chat'}
                  </p>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center text-xs text-gray-500">No team members found.</div>
          )}
        </div>
      </div>

      {/* Right Main Chat Area */}
      <div
        className={`flex-1 flex flex-col bg-[#FDFDFD] min-w-0 ${
          view === 'list' ? 'hidden md:flex' : 'flex'
        }`}
      >
        {inboxMode === 'threads' && activeThread ? (
          <>
            {/* Thread Header */}
            <div className="p-3.5 sm:p-4 md:p-5 border-b border-gray-100 bg-white flex justify-between items-center gap-3 shadow-2xs z-10">
              <div className="flex items-center gap-3 min-w-0">
                <button
                  type="button"
                  onClick={() => setView('list')}
                  className="md:hidden p-2 -ml-1 hover:bg-gray-100 rounded-xl text-gray-600 cursor-pointer"
                  aria-label="Back to inbox"
                >
                  <ArrowLeft className="h-5 w-5" />
                </button>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="text-sm sm:text-base font-black text-gray-900 truncate">
                      {isCandidate ? activeThread.job_title : activeThread.candidate_name}
                    </h4>
                    <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-50 text-[#D60041] border border-rose-200/80">
                      {isCandidate ? 'Message from HR' : activeThread.job_title}
                    </span>
                    {threadStatus.is_closed && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                        Closed
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Application #{activeThread.application_id} • {activeThread.application_status}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={(e) => handleToggleArchiveThread(activeThread, e)}
                className="p-2 rounded-xl text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-colors cursor-pointer flex items-center gap-1.5 text-xs font-semibold shrink-0"
              >
                {activeThread.is_archived ? (
                  <>
                    <ArchiveRestore size={16} />
                    <span className="hidden sm:inline">Unarchive</span>
                  </>
                ) : (
                  <>
                    <Archive size={16} />
                    <span className="hidden sm:inline">Archive</span>
                  </>
                )}
              </button>
            </div>

            {/* Thread Messages */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-3 bg-gray-50/50">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#D60041] mb-2" />
                  <p className="text-xs text-gray-500 font-semibold">Loading messages...</p>
                </div>
              ) : (
                threadMessages.map((msg, idx) => {
                  const isMe = msg.sender_id === currentUserId;
                  const senderRole = (msg.sender_role || '').toUpperCase();
                  const isFromHR = senderRole === 'HR' || senderRole === 'ADMIN' || senderRole === 'SUPERADMIN';
                  const prev = idx > 0 ? threadMessages[idx - 1] : null;
                  const currentGroup = getMessageDateGroup(msg.timestamp);
                  const prevGroup = prev ? getMessageDateGroup(prev.timestamp) : null;
                  const showDateDivider = !prev || currentGroup !== prevGroup;

                  return (
                    <React.Fragment key={msg.id || msg.client_id || idx}>
                      {showDateDivider && (
                        <div className="flex justify-center my-3">
                          <span className="px-3 py-1 bg-white border border-gray-200 rounded-full text-[11px] font-semibold text-gray-500">
                            {currentGroup}
                          </span>
                        </div>
                      )}
                      <div className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                        {(isFromHR || !isMe) && msg.sender_name && (
                          <span className="text-[11px] font-bold text-slate-600 mb-1 px-1">
                            {msg.sender_name}
                            {isFromHR ? ' • HR' : ''}
                          </span>
                        )}
                        <div
                          className={`max-w-[85%] sm:max-w-[72%] px-4 py-2.5 rounded-2xl text-xs sm:text-sm leading-relaxed whitespace-pre-wrap break-words shadow-2xs ${
                            isMe
                              ? 'bg-[#D60041] text-white rounded-br-sm'
                              : 'bg-white text-gray-800 border border-gray-200/80 rounded-bl-sm'
                          }`}
                        >
                          {msg.content && <div>{msg.content}</div>}
                          {msg.attachment_name && (
                            <button
                              type="button"
                              onClick={() => handleDownloadAttachment(msg)}
                              className={`mt-2 flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border cursor-pointer ${
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
                        <div className="flex items-center gap-2 mt-1 px-1 text-[10px] text-gray-400 font-medium">
                          <span>{formatMessageTime(msg.timestamp)}</span>
                          {isMe && (
                            msg.is_read ? (
                              <span className="inline-flex items-center gap-0.5 text-emerald-600 font-semibold">
                                <CheckCheck size={12} /> Seen
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-0.5">
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
                                className="inline-flex items-center gap-1 text-slate-400 hover:text-rose-600 cursor-pointer"
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
              <div ref={messagesEndRef} />
            </div>

            {/* Thread Composer or Closed Notice */}
            {!threadStatus.is_closed && threadStatus.can_reply ? (
              <div className="p-3 sm:p-4 bg-white border-t border-gray-100 space-y-2.5">
                {isStaff && templates.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1 mr-1">
                      <Sparkles size={11} /> Templates:
                    </span>
                    {templates.map((tpl) => (
                      <button
                        key={tpl.key}
                        type="button"
                        onClick={() => setInputMessage(tpl.body)}
                        className="text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-rose-50 text-slate-700 hover:text-[#D60041] border border-slate-200 transition-colors cursor-pointer"
                      >
                        {tpl.label}
                      </button>
                    ))}
                  </div>
                )}

                {threadStatus.closes_at && (
                  <p className="text-[11px] text-slate-400">
                    Messaging stays open until {new Date(threadStatus.closes_at).toLocaleDateString()}.
                  </p>
                )}

                {selectedFile && (
                  <div className="flex items-center justify-between gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700">
                    <span className="flex items-center gap-1.5 truncate">
                      <FileText size={13} className="text-[#D60041]" />
                      <span className="truncate font-semibold">{selectedFile.name}</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                      className="text-slate-400 hover:text-slate-700 cursor-pointer"
                    >
                      <X size={13} />
                    </button>
                  </div>
                )}

                <div className="flex items-center gap-2 bg-gray-50 rounded-2xl p-1.5 border border-gray-200/80 focus-within:bg-white focus-within:border-[#D60041] focus-within:ring-2 focus-within:ring-pink-100/50 transition-all">
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
                    className="p-2 text-slate-500 hover:text-slate-800 rounded-xl hover:bg-slate-100 cursor-pointer shrink-0"
                  >
                    <Paperclip size={16} />
                  </button>
                  <input
                    type="text"
                    value={inputMessage}
                    maxLength={MAX_MSG_LEN}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                    placeholder="Write a reply..."
                    className="flex-1 bg-transparent py-2 px-2 text-xs sm:text-sm outline-none font-medium text-gray-900 placeholder:text-gray-400 min-w-0"
                  />
                  <button
                    type="button"
                    onClick={handleSend}
                    disabled={isSending || (!inputMessage.trim() && !selectedFile)}
                    className="p-2.5 bg-[#D60041] hover:bg-[#b50037] text-white rounded-xl transition-all shadow-sm disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0"
                  >
                    <Send size={16} />
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-gray-50/80 border-t border-gray-100 flex items-center justify-center">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-2xl bg-white border border-gray-200 text-gray-600">
                  <Lock size={14} className="text-[#D60041] shrink-0" />
                  <span className="text-xs sm:text-sm font-semibold">
                    {threadStatus.reason || 'This conversation is closed'}
                  </span>
                </div>
              </div>
            )}
          </>
        ) : inboxMode === 'team' && activeContact ? (
          <>
            <div className="p-4 border-b border-gray-100 bg-white flex justify-between items-center">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setView('list')}
                  className="md:hidden p-2 -ml-1 hover:bg-gray-100 rounded-xl text-gray-600 cursor-pointer"
                >
                  <ArrowLeft className="h-5 w-5" />
                </button>
                <div>
                  <h4 className="text-sm sm:text-base font-black text-gray-900">
                    {activeContact.fullname}
                  </h4>
                  <p className="text-xs text-slate-400">{activeContact.role}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowDeleteModal(true)}
                className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl cursor-pointer"
                title="Delete team conversation"
              >
                <Trash2 size={16} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-3 bg-gray-50/50">
              {teamMessages.map((msg, idx) => {
                const isMe = msg.sender_id === currentUserId;
                return (
                  <div key={msg.id || idx} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                    <div
                      className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-xs sm:text-sm ${
                        isMe
                          ? 'bg-[#D60041] text-white rounded-br-sm'
                          : 'bg-white text-gray-800 border border-gray-200 rounded-bl-sm'
                      }`}
                    >
                      {msg.content}
                    </div>
                    <span className="text-[10px] text-gray-400 mt-1 px-1">
                      {formatMessageTime(msg.timestamp)}
                    </span>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-3.5 bg-white border-t border-gray-100">
              <div className="flex items-center gap-2 bg-gray-50 rounded-2xl p-1.5 border border-gray-200">
                <input
                  type="text"
                  value={inputMessage}
                  maxLength={MAX_MSG_LEN}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="Write a team message..."
                  className="flex-1 bg-transparent py-2 px-3 text-xs sm:text-sm outline-none"
                />
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={!inputMessage.trim() || isSending}
                  className="p-2.5 bg-[#D60041] text-white rounded-xl disabled:opacity-40 cursor-pointer"
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div className="w-16 h-16 bg-pink-50 rounded-3xl flex items-center justify-center border border-pink-100 mb-4 text-[#D60041]">
              <MessageSquare size={28} />
            </div>
            <h3 className="text-lg sm:text-xl font-black text-gray-900 mb-2 tracking-tight">
              {isCandidate
                ? threads.length > 0
                  ? 'Select a conversation'
                  : 'No messages from HR yet'
                : 'Select a conversation'}
            </h3>
            <p className="text-xs sm:text-sm text-gray-500 max-w-sm leading-relaxed">
              {isCandidate
                ? threads.length > 0
                  ? 'Choose an application thread on the left to read messages from HR and reply.'
                  : 'HR will message you here if they need anything. You will get a notification.'
                : 'Choose an applicant thread on the left, or click "Message applicant" from any applicant profile, application, shortlist roster, or interview view.'}
            </p>
          </div>
        )}
      </div>

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
              Tell our administrators why you are reporting this message.
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
                className="px-3.5 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 cursor-pointer"
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

      {/* Delete Team Conversation Modal */}
      {showDeleteModal && activeContact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-gray-100 text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-red-50 flex items-center justify-center text-red-600 mx-auto">
              <AlertTriangle size={24} />
            </div>
            <div>
              <h3 className="text-base font-black text-gray-900">Delete Team Conversation?</h3>
              <p className="text-xs text-gray-500 mt-1">
                This will remove all team messages with {activeContact.fullname}.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="flex-1 py-2 rounded-xl border border-gray-200 text-xs font-bold text-gray-700 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={handleDeleteTeamConversation}
                className="flex-1 py-2 rounded-xl bg-red-600 text-white text-xs font-bold cursor-pointer"
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatLayout;
