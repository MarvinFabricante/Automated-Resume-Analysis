import api from './api';

export interface ApplicationThreadItem {
  id: number;
  application_id: number;
  job_id?: number | null;
  job_title: string;
  application_status: string;
  candidate_id?: number | null;
  candidate_name: string;
  candidate_email?: string | null;
  candidate_profile_image_url?: string | null;
  started_by_id?: number | null;
  started_by_name?: string | null;
  last_message?: string | null;
  last_message_time?: string | null;
  last_sender_name?: string | null;
  last_sender_role?: string | null;
  unread_count: number;
  is_closed: boolean;
  can_reply: boolean;
  closure_reason?: string | null;
  closes_at?: string | null;
  is_archived: boolean;
  created_at?: string | null;
}

export interface ThreadMessageItem {
  id?: number | string;
  thread_id?: number | null;
  sender_id?: number;
  sender_name?: string | null;
  sender_role?: string | null;
  receiver_id?: number;
  application_id?: number | null;
  message_type?: string | null;
  content: string;
  attachment_url?: string | null;
  attachment_name?: string | null;
  attachment_type?: string | null;
  attachment_size?: number | null;
  is_reported?: boolean;
  timestamp: string;
  is_read?: boolean;
  read_at?: string | null;
  is_optimistic?: boolean;
  client_id?: string;
}

export interface HRMessageTemplate {
  key: string;
  label: string;
  body: string;
}

const authHeader = (token?: string | null) =>
  token ? { Authorization: `Bearer ${token}` } : {};

const chatService = {
  // ── Application-scoped two-way threads ──────────────────────────────────
  getThreads: (token?: string | null, search = '') =>
    api.get<{ threads: ApplicationThreadItem[]; total_unread: number }>('/chat/threads', {
      params: search ? { search } : {},
      headers: authHeader(token),
    }),

  startThread: (
    applicationId: number | string,
    content?: string,
    messageType = 'general',
    token?: string | null
  ) =>
    api.post(
      '/chat/threads',
      {
        application_id: Number(applicationId),
        content: content || undefined,
        message_type: messageType,
      },
      { headers: authHeader(token) }
    ),

  getApplicationThread: (
    applicationId: number | string,
    token?: string | null,
    markRead = true
  ) =>
    api.get(`/chat/applications/${applicationId}/thread`, {
      params: { mark_read: markRead },
      headers: authHeader(token),
    }),

  sendApplicationMessage: (
    applicationId: number | string,
    content: string,
    file?: File | null,
    messageType = 'general',
    token?: string | null
  ) => {
    if (file) {
      const formData = new FormData();
      formData.append('content', content);
      formData.append('message_type', messageType);
      formData.append('file', file);
      return api.post(`/chat/applications/${applicationId}/messages`, formData, {
        headers: {
          ...authHeader(token),
          'Content-Type': 'multipart/form-data',
        },
      });
    }
    return api.post(
      `/chat/applications/${applicationId}/messages`,
      { content, message_type: messageType },
      { headers: authHeader(token) }
    );
  },

  getThreadMessages: (
    threadId: number | string,
    token?: string | null,
    markRead = true
  ) =>
    api.get(`/chat/threads/${threadId}/messages`, {
      params: { mark_read: markRead },
      headers: authHeader(token),
    }),

  sendThreadMessage: (
    threadId: number | string,
    content: string,
    file?: File | null,
    messageType = 'general',
    token?: string | null
  ) => {
    if (file) {
      const formData = new FormData();
      formData.append('content', content);
      formData.append('message_type', messageType);
      formData.append('file', file);
      return api.post(`/chat/threads/${threadId}/messages`, formData, {
        headers: {
          ...authHeader(token),
          'Content-Type': 'multipart/form-data',
        },
      });
    }
    return api.post(
      `/chat/threads/${threadId}/messages`,
      { content, message_type: messageType },
      { headers: authHeader(token) }
    );
  },

  archiveThread: (threadId: number | string, token?: string | null) =>
    api.post(`/chat/threads/${threadId}/archive`, {}, { headers: authHeader(token) }),

  unarchiveThread: (threadId: number | string, token?: string | null) =>
    api.post(`/chat/threads/${threadId}/unarchive`, {}, { headers: authHeader(token) }),

  reportMessage: (messageId: number | string, reason: string, token?: string | null) =>
    api.post(
      `/chat/messages/${messageId}/report`,
      { reason },
      { headers: authHeader(token) }
    ),

  getTemplates: (
    candidateName?: string,
    jobTitle?: string,
    token?: string | null
  ) =>
    api.get<HRMessageTemplate[]>('/chat/templates', {
      params: {
        candidate_name: candidateName || undefined,
        job_title: jobTitle || undefined,
      },
      headers: authHeader(token),
    }),

  downloadAttachment: (messageId: number | string, token?: string | null) =>
    api.get(`/chat/attachments/${messageId}`, {
      responseType: 'blob',
      headers: authHeader(token),
    }),

  // ── Legacy / Team Chat endpoints ────────────────────────────────────────
  getContacts: (token?: string | null, search = '') =>
    api.get('/chat/contacts', {
      params: { search },
      headers: authHeader(token),
    }),

  getMessages: (contactId: string | number, token?: string | null) =>
    api.get(`/chat/messages/${contactId}`, {
      headers: authHeader(token),
    }),

  sendMessage: (
    contactId: string | number,
    content: string,
    token?: string | null,
    applicationId?: number | null
  ) =>
    api.post(
      `/chat/messages/${contactId}`,
      { content, application_id: applicationId ?? undefined },
      { headers: authHeader(token) }
    ),

  deleteConversation: (contactId: string | number, token?: string | null) =>
    api.delete(`/chat/messages/${contactId}`, {
      headers: authHeader(token),
    }),

  deleteMessage: (messageId: string | number, token?: string | null) =>
    api.delete(`/chat/message/${messageId}`, {
      headers: authHeader(token),
    }),

  archiveConversation: (contactId: string | number, token?: string | null) =>
    api.post(
      `/chat/conversations/${contactId}/archive`,
      {},
      { headers: authHeader(token) }
    ),

  unarchiveConversation: (contactId: string | number, token?: string | null) =>
    api.post(
      `/chat/conversations/${contactId}/unarchive`,
      {},
      { headers: authHeader(token) }
    ),

  getArchivedConversations: (token?: string | null) =>
    api.get('/chat/archived-conversations', {
      headers: authHeader(token),
    }),
};

export default chatService;
