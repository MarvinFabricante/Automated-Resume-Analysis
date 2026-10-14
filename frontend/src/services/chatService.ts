import api from './api';

const chatService = {
  getContacts: (token?: string | null, search = '') =>
    api.get('/chat/contacts', {
      params: { search },
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }),

  getMessages: (contactId: string | number, token?: string | null) =>
    api.get(`/chat/messages/${contactId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }),

  sendMessage: (contactId: string | number, content: string, token?: string | null) =>
    api.post(
      `/chat/messages/${contactId}`,
      { content },
      { headers: token ? { Authorization: `Bearer ${token}` } : {} }
    ),

  deleteConversation: (contactId: string | number, token?: string | null) =>
    api.delete(`/chat/messages/${contactId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }),

  deleteMessage: (messageId: string | number, token?: string | null) =>
    api.delete(`/chat/message/${messageId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }),

  archiveConversation: (contactId: string | number, token?: string | null) =>
    api.post(
      `/chat/conversations/${contactId}/archive`,
      {},
      { headers: token ? { Authorization: `Bearer ${token}` } : {} }
    ),

  unarchiveConversation: (contactId: string | number, token?: string | null) =>
    api.post(
      `/chat/conversations/${contactId}/unarchive`,
      {},
      { headers: token ? { Authorization: `Bearer ${token}` } : {} }
    ),

  getArchivedConversations: (token?: string | null) =>
    api.get('/chat/archived-conversations', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }),
};

export default chatService;
