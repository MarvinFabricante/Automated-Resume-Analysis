import api from './api';

const authService = {
  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  register: (roleOrPayload, payload) => {
    // Registration is strictly for Candidates only
    const actualPayload = payload ? payload : roleOrPayload;
    return api.post('/candidate/register', actualPayload);
  },

  forgotPassword: (email) =>
    api.post('/auth/forgot-password', { email }),

  resetPassword: (token, new_password) =>
    api.post('/auth/reset-password', { token, new_password }),
    
  changePassword: (current_password, new_password) =>
    api.post('/auth/change-password', { current_password, new_password }),

  getSecurityStatus: (userId) =>
    api.get('/auth/security-status', { params: userId ? { user_id: userId } : {} }),

  disconnectGoogle: (userId) =>
    api.post('/auth/google/disconnect', null, { params: userId ? { user_id: userId } : {} }),

  checkRole: (email) =>
    api.get(`/auth/check-role?email=${encodeURIComponent(email)}`),
};

export default authService;
