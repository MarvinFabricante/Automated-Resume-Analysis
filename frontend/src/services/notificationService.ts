import api from './api';

const notificationService = {
  getNotifications: (role: string, email: string) =>
    api.get(`/notifications/?role=${role}&email=${email}`),

  markAllRead: (role: string, email: string) =>
    api.put(`/notifications/mark-read?role=${role}&email=${email}`),
};

export default notificationService;
