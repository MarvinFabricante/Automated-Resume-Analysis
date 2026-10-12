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
};

export default chatService;
