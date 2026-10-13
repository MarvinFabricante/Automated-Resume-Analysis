import api from './api';

const authService = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),

  register: (roleOrPayload: any, payload?: any) => {
    // Registration is strictly for Candidates only
    const actualPayload = payload ? payload : roleOrPayload;
    return api.post('/candidate/register', actualPayload);
  },

  forgotPassword: (email: string) =>
    api.post('/auth/forgot-password', { email }),

  resetPassword: (token: string, new_password: string) =>
    api.post('/auth/reset-password', { token, new_password }),
    
  changePassword: (current_password: string, new_password: string) =>
    api.post('/auth/change-password', { current_password, new_password }),

  setPassword: (new_password: string) =>
    api.post('/auth/set-password', { new_password }),

  getSecurityStatus: (userId?: string | number | null) =>
    api.get('/auth/security-status', { params: userId ? { user_id: userId } : {} }),

  disconnectGoogle: (userId?: string | number | null) =>
    api.post('/auth/google/disconnect', null, { params: userId ? { user_id: userId } : {} }),

  checkRole: (email: string) =>
    api.get(`/auth/check-role?email=${encodeURIComponent(email)}`),
};

export default authService;
