import api from './api';

const getProfileEndpoint = (role, userId) => {
  if (role === 'HR') return `/hr/profile/${userId}`;
  if (role === 'ADMIN') return `/admins/profile/${userId}`;
  return `/candidate/profile/${userId}`;
};

const getImageUploadEndpoint = (role, userId) => {
  if (role === 'HR') return `/hr/upload-profile-image/${userId}`;
  if (role === 'ADMIN') return `/admins/upload-profile-image/${userId}`;
  return `/candidate/upload-profile-image/${userId}`;
};

const profileService = {
  getProfile: (role, userId) =>
    api.get(getProfileEndpoint(role, userId)),

  updateProfile: (role, userId, data) =>
    api.put(getProfileEndpoint(role, userId), data),

  uploadProfileImage: (role, userId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(getImageUploadEndpoint(role, userId), formData);
  },
};

export default profileService;
