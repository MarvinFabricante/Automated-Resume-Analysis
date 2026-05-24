import api from './api';

const jobService = {
  getAllJobs: () =>
    api.get('/hr/read-jobs'),

  getJobById: (jobId) =>
    api.get(`/hr/read-job/${jobId}`),
};

export default jobService;
