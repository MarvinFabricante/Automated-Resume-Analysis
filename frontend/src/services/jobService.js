import api from './api';

const jobService = {
  getAllJobs: () =>
    api.get('/admins/read-jobs'),

  getJobById: (jobId) =>
    api.get(`/admins/read-job/${jobId}`),
};

export default jobService;
