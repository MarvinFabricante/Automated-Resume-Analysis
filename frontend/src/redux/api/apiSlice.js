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
      query: (params) => {
        const includeInactive = params?.include_inactive ?? false;
        return `/hr/read-jobs?include_inactive=${includeInactive}`;
      },
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

    archiveJob: builder.mutation({
      query: (jobId) => ({
        url: `/hr/archive-job/${jobId}`,
        method: 'PATCH',
      }),
      invalidatesTags: ['Jobs', 'Dashboard'],
    }),

    unarchiveJob: builder.mutation({
      query: (jobId) => ({
        url: `/hr/unarchive-job/${jobId}`,
        method: 'PATCH',
      }),
      invalidatesTags: ['Jobs', 'Dashboard'],
    }),

    deleteJob: builder.mutation({
      query: (jobId) => ({
        url: `/hr/delete-job/${jobId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Jobs', 'Dashboard', 'Applications'],
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
          location: app.location || "N/A",
          jobLocation: app.job?.location || "N/A",
          jobDepartment: app.job?.department || "N/A",
          company: app.company || "N/A",
          degree: app.degree || "",
          college: app.college || "",
          relevance: app.relevance || "",
          matchScore: app.match_score || 0,
          skillsScore: app.skills_score || 0,
          experienceScore: app.experience_score || 0,
          educationScore: app.education_score || 0,
          skills_reason: app.skills_reason,
          experience_reason: app.experience_reason,
          education_reason: app.education_reason,
          matched_skills: app.matched_skills || [],
          missing_skills: app.missing_skills || [],
          relevant_experience: app.relevant_experience || null,
          experience_gaps: app.experience_gaps || null,
          required_degree: app.required_degree || null,
          candidate_degree: app.candidate_degree || null,
          recommendations: app.recommendations || [],
          ai_summary: app.ai_summary || "",
          strengths: app.strengths || [],
          weaknesses: app.weaknesses || [],
          ai_powered: Boolean(app.ai_powered),
          email: app.candidate_email,
          phone: app.phone || "N/A"
        }));
      },
    }),

    getCandidateApplications: builder.query({
      query: (email) => `/applications/candidate/${email}`,
      providesTags: ['Applications'],
      transformResponse: (response) => {
        return response.map(app => {
          const uStatus = app.status ? app.status.toUpperCase() : 'PENDING';
          const formattedStatus = uStatus.split(' ').map(word => word.charAt(0) + word.slice(1).toLowerCase()).join(' ');
          return {
            id: app.id,
            role: app.job_title || app.job?.job_title || "Unknown Position",
            company: app.company || "Mariwasa Siam Ceramics",
            appliedDate: new Date(app.created_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }),
            status: formattedStatus,
            statusColor: uStatus === 'PENDING' ? "text-amber-600 bg-amber-50 border-amber-100" :
              uStatus === 'REVIEWED' ? "text-blue-600 bg-blue-50 border-blue-100" :
                uStatus === 'TECHNICAL INTERVIEW' ? "text-purple-600 bg-purple-50 border-purple-100" :
                  uStatus === 'FINAL INTERVIEW' ? "text-indigo-600 bg-indigo-50 border-indigo-100" :
                    uStatus === 'ACCEPTED' ? "text-emerald-600 bg-emerald-50 border-emerald-100" :
                      uStatus === 'REJECTED' ? "text-rose-600 bg-rose-50 border-rose-100" :
                        "text-slate-600 bg-slate-50 border-slate-100",
            step: uStatus === 'PENDING' ? 1 : 
                  uStatus === 'REVIEWED' ? 2 : 
                  uStatus === 'TECHNICAL INTERVIEW' ? 3 : 
                  uStatus === 'FINAL INTERVIEW' ? 4 : 
                  (uStatus === 'ACCEPTED' || uStatus === 'REJECTED') ? 5 : 1,
            totalSteps: 5,
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

    deleteApplication: builder.mutation({
      query: (id) => ({
        url: `/applications/${id}`,
        method: 'DELETE',
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
  useDeleteApplicationMutation,
  useCreateJobMutation,
  useUpdateJobMutation,
  useArchiveJobMutation,
  useUnarchiveJobMutation,
  useDeleteJobMutation,
  useUpdateApplicationStatusMutation,
  useGetHRActivitiesQuery,
  useGetUsersQuery,
  useArchiveUserMutation,
  useUnarchiveUserMutation,
  useGetAdminSystemStatsQuery,
  useGetAuditLogsQuery,
  useGetActiveUsersCountQuery,
} = apiSlice;
