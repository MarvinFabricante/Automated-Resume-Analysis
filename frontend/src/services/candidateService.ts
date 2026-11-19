import api from './api';
import { AxiosRequestConfig } from 'axios';

const candidateService = {
  parseResume: (file: File | Blob, options: AxiosRequestConfig = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/candidate/parse-resume', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
      ...options
    });
  },

  matchData: (jobId?: string | number | null, payload?: any) => {
    const endpoint = jobId
      ? `/matching/match-data/${jobId}`
      : '/matching/match-data';
    return api.post(endpoint, payload, { timeout: 30000 });
  },

  submitApplication: (payload: any) =>
    api.post('/applications/', payload, { timeout: 30000 }),
};

export default candidateService;
