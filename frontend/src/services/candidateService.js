import api from './api';

const candidateService = {
  parseResume: (file, options = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/candidate/parse-resume', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      ...options
    });
  },

  matchData: (jobId, payload) => {
    const endpoint = jobId
      ? `/matching/match-data/${jobId}`
      : '/matching/match-data';
    return api.post(endpoint, payload);
  },

  submitApplication: (payload) =>
    api.post('/applications/', payload),
};

export default candidateService;
