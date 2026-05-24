import api from './api';

const notificationService = {
  getNotifications: (role, email) =>
    api.get(`/notifications/?role=${role}&email=${email}`),

  markAllRead: (role, email) =>
    api.put(`/notifications/mark-read?role=${role}&email=${email}`),
};

export default notificationService;
