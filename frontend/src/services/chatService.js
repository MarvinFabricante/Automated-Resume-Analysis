import api from './api';

const chatService = {
  getContacts: (token, search = '') =>
    api.get('/chat/contacts', {
      params: { search },
      headers: { Authorization: `Bearer ${token}` },
    }),

  getMessages: (contactId, token) =>
    api.get(`/chat/messages/${contactId}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),

  sendMessage: (contactId, content, token) =>
    api.post(
      `/chat/messages/${contactId}`,
      { content },
      { headers: { Authorization: `Bearer ${token}` } }
    ),
};

export default chatService;
