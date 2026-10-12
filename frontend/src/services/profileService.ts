import api from './api';

const getProfileEndpoint = (role: string, userId: string | number) => {
  if (role === 'HR') return `/hr/profile/${userId}`;
  if (role === 'ADMIN') return `/admins/profile/${userId}`;
  return `/candidate/profile/${userId}`;
};

const getImageUploadEndpoint = (role: string, userId: string | number) => {
  if (role === 'HR') return `/hr/upload-profile-image/${userId}`;
  if (role === 'ADMIN') return `/admins/upload-profile-image/${userId}`;
  return `/candidate/upload-profile-image/${userId}`;
};

const profileService = {
  getProfile: (role: string, userId: string | number) =>
    api.get(getProfileEndpoint(role, userId)),

  updateProfile: (role: string, userId: string | number, data: any) =>
    api.put(getProfileEndpoint(role, userId), data),

  uploadProfileImage: (role: string, userId: string | number, file: File | Blob) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(getImageUploadEndpoint(role, userId), formData);
  },
};

export default profileService;
