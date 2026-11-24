import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  MessageSquare,
  Send,
  Search,
  ArrowLeft,
  X,
  Lock,
  CheckCheck,
  Check,
  Briefcase,
} from 'lucide-react';
import toast from 'react-hot-toast';
import chatService, {
  ApplicationThreadItem,
  ThreadMessageItem,
} from '../../services/chatService';
import { useDispatch } from 'react-redux';
import { WS_BASE_URL } from '../../services/api';
import { setUnreadMessagesCount } from '../../redux/slices/notificationSlice';
import { decodeToken } from '../../utils/token';

export interface ChatContactItem {
  id: number;
  fullname: string;
  role?: string;
  is_online?: boolean;
  profile_image_url?: string | null;
  last_message?: string;
  last_message_time?: string;
  unread_count?: number;
  is_archived?: boolean;
}

export interface ChatMessageItem {
  id?: number | string;
  sender_id?: number;
  receiver_id?: number;
  content: string;
  timestamp: string;
  is_optimistic?: boolean;
  client_id?: string;
}

const ChatWidget: React.FC = () => {
  const dispatch = useDispatch();
  const [isOpen, setIsOpen] = useState(false);
  const [view, setView] = useState<'threads' | 'chat'>('threads');
  const [threads, setThreads] = useState<ApplicationThreadItem[]>([]);
  const [search, setSearch] = useState('');
  const [activeThread, setActiveThread] = useState<ApplicationThreadItem | null>(null);
  const [messages, setMessages] = useState<ThreadMessageItem[]>([]);
  const [threadStatus, setThreadStatus] = useState<{
    is_closed: boolean;
    can_reply: boolean;
    reason?: string | null;
  }>({ is_closed: false, can_reply: true, reason: null });
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isMobileScrolling, setIsMobileScrolling] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeThreadRef = useRef<ApplicationThreadItem | null>(null);

  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
  const decoded = decodeToken(token);
  const currentUserRole = (
    (typeof localStorage !== 'undefined' ? localStorage.getItem('role') : '') ||
    decoded?.role ||
    'Guest'
  ).toUpperCase();
  const currentUserId =
    typeof localStorage !== 'undefined'
      ? parseInt(localStorage.getItem('user_id') || '0', 10) || decoded?.id || 0
      : decoded?.id || 0;
  const isCandidate = currentUserRole === 'CANDIDATE';

  useEffect(() => {
    activeThreadRef.current = activeThread;
  }, [activeThread]);

  useEffect(() => {
    let scrollTimeout: any = null;
    let lastScrollY = window.scrollY || window.pageYOffset || 0;
    const handleScroll = () => {
      const currentScrollY = window.scrollY || window.pageYOffset || 0;
      const diff = Math.abs(currentScrollY - lastScrollY);
      if (window.innerWidth < 768) {
        if (isOpen && diff > 5) setIsOpen(false);
        if (diff > 8) {
          setIsMobileScrolling(true);
          clearTimeout(scrollTimeout);
          scrollTimeout = setTimeout(() => setIsMobileScrolling(false), 800);
        }
      }
      lastScrollY = currentScrollY;
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (scrollTimeout) clearTimeout(scrollTimeout);
    };
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const fetchThreads = useCallback(async () => {
    if (!token) return;
    try {
      const res = await chatService.getThreads(token, search);
      const list: ApplicationThreadItem[] = res.data?.threads || [];
      setThreads(list);
      const totalUnread = Number(
        res.data?.total_unread ?? list.reduce((acc, t) => acc + (t.unread_count || 0), 0)
      );
      dispatch(setUnreadMessagesCount(totalUnread));
    } catch (error) {
      console.error('Failed to fetch threads:', error);
    }
  }, [token, search, dispatch]);

  useEffect(() => {
    if (token) fetchThreads();
  }, [token, isOpen, search, fetchThreads]);

  useEffect(() => {
    if (!token) return;
    let shouldReconnect = true;

    const connectWebSocket = () => {
      if (!shouldReconnect) return;
      const ws = new WebSocket(`${WS_BASE_URL}/chat/ws?token=${encodeURIComponent(token)}`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'new_message') {
            const cur = activeThreadRef.current;
            if (cur && String(cur.id) === String(data.thread_id)) {
              setMessages((prev) =>
                prev.some((m) => String(m.id) === String(data.id)) ? prev : [...prev, data]
              );
            }
            fetchThreads();
          } else if (data.type === 'messages_seen') {
            const seenIds = new Set((data.message_ids || []).map((id: any) => String(id)));
            setMessages((prev) =>
              prev.map((m) =>
                seenIds.has(String(m.id)) ? { ...m, is_read: true, read_at: data.read_at } : m
              )
            );
          }
        } catch {
          // ignore
        }
      };

      ws.onclose = () => {
        if (shouldReconnect) {
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
        }
      };
    };

    connectWebSocket();

    return () => {
      shouldReconnect = false;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          // ignore
        }
      }
    };
  }, [token, fetchThreads]);

  const openThread = async (thread: ApplicationThreadItem) => {
    setActiveThread(thread);
    setView('chat');
    setLoading(true);
    try {
      const res = await chatService.getThreadMessages(thread.id, token, true);
      setMessages(res.data?.messages || []);
      if (res.data?.thread_status) {
        setThreadStatus(res.data.thread_status);
      } else {
        setThreadStatus({
          is_closed: thread.is_closed,
          can_reply: thread.can_reply,
          reason: thread.closure_reason,
        });
      }
      setThreads((prev) => {
        const updated = prev.map((t) => (t.id === thread.id ? { ...t, unread_count: 0 } : t));
        dispatch(
          setUnreadMessagesCount(updated.reduce((acc, t) => acc + (t.unread_count || 0), 0))
        );
        return updated;
      });
    } catch {
      toast.error('Failed to load messages.');
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    const trimmed = inputMessage.trim();
    if (!trimmed || !activeThread || isSending) return;
    setIsSending(true);
    try {
      const res = await chatService.sendThreadMessage(activeThread.id, trimmed, null, 'general', token);
      setMessages((prev) =>
        prev.some((m) => String(m.id) === String(res.data?.id)) ? prev : [...prev, res.data]
      );
      setInputMessage('');
      fetchThreads();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Could not send reply.');
    } finally {
      setIsSending(false);
    }
  };

  if (!token || currentUserRole === 'GUEST') {
    return null;
  }

  const visibleThreads = threads.filter((t) => !t.is_archived);
  const totalUnread = visibleThreads.reduce((sum, t) => sum + (t.unread_count || 0), 0);

  return (
    <>
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/40 backdrop-blur-[2px] z-[998]"
          onClick={() => setIsOpen(false)}
          aria-label="Close messaging overlay"
        />
      )}

      <div className="fixed bottom-3 right-3 sm:bottom-6 sm:right-6 z-[999] font-['Inter'] pointer-events-auto">
        {isOpen && (
          <div className="chat-window-container bg-white w-[calc(100vw-1.5rem)] sm:w-[360px] h-[75vh] sm:h-[520px] max-h-[560px] rounded-[24px] shadow-2xl border border-gray-100 flex flex-col overflow-hidden mb-3 sm:mb-4">
            {view === 'threads' ? (
              <>
                <div className="bg-gradient-to-r from-[#B50037] to-[#D60041] p-3.5 sm:p-4 flex justify-between items-center text-white">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center">
                      <MessageSquare className="h-4 w-4 text-white" />
                    </div>
                    <div>
                      <h3 className="text-white font-bold text-sm leading-none">Messages</h3>
                      <span className="text-[10px] text-pink-100 font-medium">
                        {isCandidate ? 'Messages from HR' : 'Applicant Threads'}
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsOpen(false)}
                    className="p-1.5 hover:bg-white/20 rounded-xl text-white cursor-pointer"
                    aria-label="Close messages"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                {visibleThreads.length > 0 && (
                  <div className="p-3 bg-gray-50 border-b border-gray-100">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 h-4 w-4" />
                      <input
                        type="text"
                        placeholder={isCandidate ? 'Search position...' : 'Search applicant or position...'}
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full bg-white border border-gray-200 rounded-full py-1.5 pl-9 pr-4 text-xs focus:outline-none focus:border-[#D60041]"
                      />
                    </div>
                  </div>
                )}

                <div className="flex-1 overflow-y-auto">
                  {visibleThreads.length > 0 ? (
                    visibleThreads.map((thr) => (
                      <div
                        key={thr.id}
                        onClick={() => openThread(thr)}
                        className="p-3 border-b border-gray-50 flex items-center gap-3 hover:bg-gray-50 cursor-pointer"
                      >
                        <div className="w-10 h-10 bg-pink-50 rounded-xl flex items-center justify-center text-[#D60041] font-bold text-sm shrink-0">
                          {isCandidate ? (
                            <Briefcase size={16} />
                          ) : (
                            (thr.candidate_name || 'A').charAt(0).toUpperCase()
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-1">
                            <h4 className="text-xs font-bold text-gray-900 truncate">
                              {isCandidate ? thr.job_title : thr.candidate_name}
                            </h4>
                            {thr.last_message_time && (
                              <span className="text-[10px] text-gray-400 shrink-0">
                                {new Date(thr.last_message_time).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                              </span>
                            )}
                          </div>
                          {!isCandidate && (
                            <p className="text-[10px] font-semibold text-[#D60041] truncate">
                              {thr.job_title}
                            </p>
                          )}
                          <p className="text-xs text-gray-500 truncate mt-0.5">
                            {thr.last_message || 'Conversation started'}
                          </p>
                        </div>
                        {thr.unread_count > 0 && (
                          <span className="min-w-[20px] h-5 bg-[#D60041] rounded-full flex items-center justify-center text-[10px] text-white font-bold px-1.5">
                            {thr.unread_count}
                          </span>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="p-8 text-center text-gray-500 text-xs space-y-2">
                      <MessageSquare className="w-8 h-8 mx-auto text-gray-300" />
                      <p className="font-bold text-gray-700">
                        {isCandidate ? 'No messages from HR yet' : 'No active threads'}
                      </p>
                      <p className="leading-relaxed">
                        {isCandidate
                          ? 'HR will message you here if they need anything. You will get a notification.'
                          : 'Use "Message applicant" on any applicant profile, application, shortlist, or interview to start a thread.'}
                      </p>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                <div className="bg-white border-b border-gray-100 p-3.5 flex justify-between items-center">
                  <div className="flex items-center gap-2 min-w-0">
                    <button
                      type="button"
                      onClick={() => setView('threads')}
                      className="p-1.5 hover:bg-gray-100 rounded-xl text-gray-500 cursor-pointer shrink-0"
                    >
                      <ArrowLeft className="h-4 w-4" />
                    </button>
                    <div className="min-w-0">
                      <h4 className="text-xs font-black text-gray-900 truncate">
                        {isCandidate ? activeThread?.job_title : activeThread?.candidate_name}
                      </h4>
                      <p className="text-[10px] text-gray-500 truncate">
                        {isCandidate ? 'Message from HR' : activeThread?.job_title}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsOpen(false)}
                    className="p-1.5 hover:bg-gray-100 rounded-xl text-gray-400 cursor-pointer"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto p-3.5 space-y-3 bg-[#F8F9FA]">
                  {loading ? (
                    <div className="text-center text-gray-400 text-xs mt-4">Loading...</div>
                  ) : (
                    messages.map((msg, idx) => {
                      const isMe = msg.sender_id === currentUserId;
                      const isFromHR = ['HR', 'ADMIN', 'SUPERADMIN'].includes(
                        (msg.sender_role || '').toUpperCase()
                      );
                      return (
                        <div
                          key={msg.id || idx}
                          className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}
                        >
                          {(isFromHR || !isMe) && msg.sender_name && (
                            <span className="text-[10px] font-bold text-slate-500 mb-0.5 px-1">
                              {msg.sender_name}
                              {isFromHR ? ' • HR' : ''}
                            </span>
                          )}
                          <div
                            className={`max-w-[85%] px-3.5 py-2 rounded-2xl text-xs whitespace-pre-wrap break-words ${
                              isMe
                                ? 'bg-[#D60041] text-white rounded-br-sm'
                                : 'bg-white text-gray-800 border border-gray-200 rounded-bl-sm'
                            }`}
                          >
                            {msg.content || (msg.attachment_name ? `Attachment: ${msg.attachment_name}` : '')}
                          </div>
                          <div className="flex items-center gap-1 mt-0.5 px-1 text-[10px] text-gray-400">
                            <span>
                              {new Date(msg.timestamp).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                            {isMe && (
                              msg.is_read ? (
                                <span className="inline-flex items-center gap-0.5 text-emerald-600 font-semibold">
                                  <CheckCheck size={10} /> Seen
                                </span>
                              ) : (
                                <Check size={10} />
                              )
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {!threadStatus.is_closed && threadStatus.can_reply ? (
                  <div className="p-3 bg-white border-t border-gray-100 flex items-center gap-2">
                    <input
                      type="text"
                      value={inputMessage}
                      maxLength={2000}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          sendMessage();
                        }
                      }}
                      placeholder="Write a reply..."
                      className="flex-1 bg-gray-50 border border-gray-200 rounded-xl py-2 px-3 text-xs outline-none focus:bg-white focus:border-[#D60041]"
                    />
                    <button
                      type="button"
                      onClick={sendMessage}
                      disabled={!inputMessage.trim() || isSending}
                      className="p-2 bg-[#D60041] text-white rounded-xl disabled:opacity-40 cursor-pointer"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <div className="p-3 bg-gray-50 border-t border-gray-100 flex items-center justify-center">
                    <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-gray-200 text-gray-600 text-xs font-semibold">
                      <Lock className="w-3.5 h-3.5 text-[#D60041]" />
                      <span>{threadStatus.reason || 'This conversation is closed'}</span>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Open messaging"
          className={`${isOpen ? 'scale-0 opacity-0 pointer-events-none' : 'scale-100 opacity-100'} ${
            isMobileScrolling ? 'translate-y-24 opacity-0 pointer-events-none' : 'translate-y-0'
          } fixed bottom-5 right-5 sm:bottom-6 sm:right-6 transition-all duration-300 bg-gradient-to-tr from-[#B50037] via-[#D60041] to-[#FF2E63] text-white p-3.5 sm:p-4 rounded-2xl shadow-xl shadow-[#D60041]/25 flex items-center justify-center z-[999] cursor-pointer`}
        >
          <MessageSquare className="h-6 w-6" />
          {totalUnread > 0 && (
            <span className="absolute -top-1.5 -right-1.5 min-w-[20px] h-5 px-1 bg-slate-900 border-2 border-white rounded-full text-[10px] font-black flex items-center justify-center">
              {totalUnread}
            </span>
          )}
        </button>
      </div>
    </>
  );
};

export default ChatWidget;
