import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: 'http://localhost:8000',
    prepareHeaders: (headers) => {
      const token = localStorage.getItem('token');
      if (token) {
        headers.set('authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  // Added AuditLogs and Users to tagTypes so they are recognized
  tagTypes: ['Dashboard', 'Jobs', 'Candidates', 'Applications', 'AuditLogs', 'Users'],
  endpoints: (builder) => ({
    // --- DASHBOARD STATS ---
    getDashboardStats: builder.query({
      query: () => '/hr/application-stats',
      providesTags: ['Dashboard'],
      keepUnusedDataFor: 300,
    }),
    getCandidateCount: builder.query({
      query: () => '/hr/candidate-count',
      providesTags: ['Candidates'],
    }),
    getResumeCount: builder.query({
      query: () => '/hr/resume-count',
      providesTags: ['Dashboard'],
    }),

    // --- JOBS ---
    getJobs: builder.query({
      query: () => '/hr/read-jobs',
      providesTags: ['Jobs'],
      transformResponse: (response) => {
        const rawData = Array.isArray(response) ? response : [];
        return rawData.map(job => ({
          ...job,
          title: job.job_title || "Untitled Position",
          department: job.department || "General",
          location: job.location || "Remote / Not Specified",
          salary_range: job.salary_range || "Competitive / TBD",
          is_active: Boolean(job.is_active)
        }));
      },
    }),

    createJob: builder.mutation({
      query: (newJob) => ({
        url: '/hr/createjob',
        method: 'POST',
        body: newJob,
      }),
      invalidatesTags: ['Jobs', 'Dashboard'],
    }),

    updateJob: builder.mutation({
      query: ({ jobId, body }) => ({
        url: `/hr/update-job/${jobId}`,
        method: 'PATCH',
        body,
      }),
      invalidatesTags: ['Jobs', 'Applications', 'Dashboard'],
    }),

    updateJobStatus: builder.mutation({
      query: ({ jobId, status }) => ({
        url: `/hr/set-job-status/${jobId}?active_status=${status}`,
        method: 'PATCH',
      }),
      invalidatesTags: ['Jobs'],
    }),

    getApplications: builder.query({
      query: () => '/applications/',
      providesTags: ['Applications'],
      transformResponse: (response) => {
        return response.map(app => ({
          id: app.id,
          name: app.candidate_name,
          status: app.status,
          preferredJob: app.job_title || app.job?.job_title || "Unknown",
          skills: app.skills || [],
          profileImage: app.profile_image_url || null,
          date: app.created_at,
          location: app.job?.location || "N/A",
          matchScore: app.match_score || 0,
          skills_reason: app.skills_reason,
          experience_reason: app.experience_reason,
          education_reason: app.education_reason
        }));
      },
    }),

    getCandidateApplications: builder.query({
      query: (email) => `/applications/candidate/${email}`,
      providesTags: ['Applications'],
      transformResponse: (response) => {
        return response.map(app => {
          const uStatus = app.status ? app.status.toUpperCase() : 'PENDING';
          return {
            id: app.id,
            role: app.job_title || app.job?.job_title || "Unknown Position",
            company: app.company || "Mariwasa Siam Ceramics",
            appliedDate: new Date(app.created_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }),
            status: uStatus.charAt(0) + uStatus.slice(1).toLowerCase(),
            statusColor: uStatus === 'PENDING' ? "text-amber-600 bg-amber-50 border-amber-100" :
              uStatus === 'REVIEWED' ? "text-blue-600 bg-blue-50 border-blue-100" :
                uStatus === 'ACCEPTED' ? "text-emerald-600 bg-emerald-50 border-emerald-100" :
                  uStatus === 'REJECTED' ? "text-rose-600 bg-rose-50 border-rose-100" :
                    "text-slate-600 bg-slate-50 border-slate-100",
            step: uStatus === 'PENDING' ? 1 : uStatus === 'REVIEWED' ? 2 : uStatus === 'ACCEPTED' ? 4 : 4,
            totalSteps: 4,
            originalData: app
          };
        });
      },
    }),

    submitApplication: builder.mutation({
      query: (application) => ({
        url: '/applications/',
        method: 'POST',
        body: application,
      }),
      invalidatesTags: ['Applications', 'Dashboard'],
    }),

    updateApplicationStatus: builder.mutation({
      query: ({ id, status }) => ({
        url: `/applications/${id}/status`,
        method: 'PATCH',
        body: { status },
      }),
      invalidatesTags: ['Applications'],
    }),

    getActiveUsersCount: builder.query({
      query: () => '/chat/active-count',
      // Poll every 15 seconds to keep it fresh
      pollingInterval: 15000,
    }),

    // --- ADMIN / HR TOOLS ---
    getHRActivities: builder.query({
      query: () => '/admins/hr-activities',
      providesTags: ['AuditLogs'],
      transformResponse: (response) => {
        return response.map(log => ({
          id: log.id,
          user: log.user?.fullname || log.user?.email || "Unknown HR",
          profileImage: log.user?.profile_image_url || null,
          role: log.user?.role || "HR",
          action: log.action.replace('_', ' '),
          time: new Date(log.created_at).toLocaleString(),
          status: "Success",
          details: log.details,
          target: log.target
        }));
      },
    }),

    getUsers: builder.query({
      query: () => '/admins/users',
      providesTags: ['Users'],
    }),

    archiveUser: builder.mutation({
      query: (userId) => ({
        url: `/admins/users/${userId}/archive`,
        method: 'PATCH',
      }),
      invalidatesTags: ['Users'],
    }),

    unarchiveUser: builder.mutation({
      query: (userId) => ({
        url: `/admins/users/${userId}/unarchive`,
        method: 'PATCH',
      }),
      invalidatesTags: ['Users'],
    }),

    getAdminSystemStats: builder.query({
      query: () => '/admins/system-stats',
      providesTags: ['Dashboard'],
    }),

    getAuditLogs: builder.query({
      query: () => '/admins/audit-logs',
      providesTags: ['AuditLogs'],
      transformResponse: (response) => {
        return response.map(log => ({
          id: `LOG-${log.id}`,
          user: log.user?.fullname || log.user?.email || "Unknown",
          role: log.user?.role || "N/A",
          action: log.action.replace('_', ' '),
          target: log.target || "N/A",
          ip: log.ip_address || "Internal",
          time: new Date(log.created_at).toLocaleString(),
          status: "Success",
          details: log.details
        }));
      },
    }),
  }),
});

export const {
  useGetDashboardStatsQuery,
  useGetCandidateCountQuery,
  useGetResumeCountQuery,
  useGetJobsQuery,
  useGetApplicationsQuery,
  useGetCandidateApplicationsQuery,
  useSubmitApplicationMutation,
  useCreateJobMutation,
  useUpdateJobMutation,
  useUpdateJobStatusMutation,
  useUpdateApplicationStatusMutation,
  useGetHRActivitiesQuery,
  useGetUsersQuery,
  useArchiveUserMutation,
  useUnarchiveUserMutation,
  useGetAdminSystemStatsQuery,
  useGetAuditLogsQuery,
  useGetActiveUsersCountQuery,
} = apiSlice;