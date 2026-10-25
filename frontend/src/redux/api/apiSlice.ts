import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { API_BASE_URL } from '../../services/api';

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: API_BASE_URL,
    prepareHeaders: (headers) => {
      const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
      if (token) {
        headers.set('authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  // Added AuditLogs, Users, SystemConfig, Templates, Interviews, CalendarEvents, HRInterviewers to tagTypes
  tagTypes: ['Dashboard', 'Jobs', 'Candidates', 'Applications', 'AuditLogs', 'Users', 'SystemConfig', 'Templates', 'Interviews', 'CalendarEvents', 'HRInterviewers'],
  endpoints: (builder) => ({
    // --- DASHBOARD STATS ---
    getDashboardStats: builder.query<any, void>({
      query: () => '/hr/application-stats',
      providesTags: ['Dashboard'],
      keepUnusedDataFor: 300,
    }),
    getCandidateCount: builder.query<any, void>({
      query: () => '/hr/candidate-count',
      providesTags: ['Candidates'],
    }),
    getResumeCount: builder.query<any, void>({
      query: () => '/hr/resume-count',
      providesTags: ['Dashboard'],
    }),
    getDashboardTrends: builder.query<any, void>({
      query: () => '/hr/dashboard-trends',
      providesTags: ['Dashboard'],
      keepUnusedDataFor: 60,
    }),

    // --- JOBS ---
    getJobs: builder.query<any[], { include_inactive?: boolean } | void>({
      query: (params) => {
        const includeInactive = (params as { include_inactive?: boolean } | undefined)?.include_inactive ?? false;
        return `/admins/read-jobs?include_inactive=${includeInactive}`;
      },
      providesTags: ['Jobs'],
      keepUnusedDataFor: 300,
      transformResponse: (response: any) => {
        const rawData = Array.isArray(response) ? response : [];
        return rawData.map((job: any) => ({
          ...job,
          title: job.job_title || "Untitled Position",
          department: job.department || "General",
          location: job.location || "Remote / Not Specified",
          salary_range: job.salary_range || "Competitive / TBD",
          is_active: Boolean(job.is_active)
        }));
      },
    }),

    createJob: builder.mutation<any, any>({
      query: (newJob) => ({
        url: '/admins/createjob',
        method: 'POST',
        body: newJob,
      }),
      invalidatesTags: ['Jobs', 'Dashboard'],
    }),

    updateJob: builder.mutation<any, { jobId: number | string; body: any }>({
      query: ({ jobId, body }) => ({
        url: `/admins/update-job/${jobId}`,
        method: 'PATCH',
        body,
      }),
      invalidatesTags: ['Jobs', 'Applications', 'Dashboard'],
    }),

    archiveJob: builder.mutation<any, number | string>({
      query: (jobId) => ({
        url: `/admins/archive-job/${jobId}`,
        method: 'PATCH',
      }),
      invalidatesTags: ['Jobs', 'Dashboard'],
    }),

    unarchiveJob: builder.mutation<any, number | string>({
      query: (jobId) => ({
        url: `/admins/unarchive-job/${jobId}`,
        method: 'PATCH',
      }),
      invalidatesTags: ['Jobs', 'Dashboard'],
    }),

    deleteJob: builder.mutation<any, number | string>({
      query: (jobId) => ({
        url: `/admins/delete-job/${jobId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Jobs', 'Dashboard', 'Applications'],
    }),

    getApplications: builder.query<any[], void>({
      query: () => '/applications/',
      providesTags: ['Applications'],
      keepUnusedDataFor: 300,
      transformResponse: (response: any[]) => {
        return (response || []).map((app: any) => ({
          id: app.id,
          name: app.candidate_name,
          status: app.status,
          preferredJob: app.job?.job_title || "Unknown",
          skills: app.skills || [],
          profileImage: app.profile_image_url || null,
          resumeUrl: app.resume_url || null,
          date: app.created_at,
          location: app.location || "N/A",
          jobLocation: app.job?.location || "N/A",
          jobDepartment: app.job?.department || "N/A",
          company: app.company || "N/A",
          degree: app.degree || "",
          college: app.college || "",
          relevance: app.relevance || "",
          matchScore: (app.match_score && app.match_score > 0) ? app.match_score : Math.round(((app.skills_score || 0) * 0.4) + ((app.experience_score || 0) * 0.4) + ((app.certifications_score || app.education_score || 0) * 0.2)) || 0,
          skillsScore: app.skills_score || 0,
          experienceScore: app.experience_score || 0,
          educationScore: app.education_score || 0,
          certificationsScore: app.certifications_score || 0,
          certifications_score: app.certifications_score || 0,
          skills_reason: app.skills_reason,
          experience_reason: app.experience_reason,
          education_reason: app.education_reason,
          certifications_reason: app.certifications_reason,
          matched_skills: app.matched_skills || [],
          missing_skills: app.missing_skills || [],
          relevant_experience: app.relevant_experience || null,
          experience_gaps: app.experience_gaps || null,
          work_experiences: app.work_experiences || [],
          total_experience_months: app.total_experience_months || 0,
          highest_educational_attainment: app.highest_educational_attainment || null,
          education_entries: app.education_entries || [],
          required_degree: app.required_degree || null,
          candidate_degree: app.candidate_degree || null,
          certifications: app.certifications || app.candidate_certifications || null,
          candidate_certifications: app.candidate_certifications || app.certifications || null,
          certifications_details: app.certifications_details || null,
          skills_details: app.skills_details || null,
          recommendations: app.recommendations || [],
          ai_summary: app.ai_summary || "",
          strengths: app.strengths || [],
          weaknesses: app.weaknesses || [],
          ai_powered: Boolean(app.ai_powered),
          email: app.candidate_email,
          candidate_email: app.candidate_email,
          phone: app.phone || "N/A",
          candidate_name: app.candidate_name
        }));
      },
    }),

    getCandidateApplications: builder.query<any[], string>({
      query: (email) => `/applications/candidate/${email}`,
      providesTags: ['Applications'],
      transformResponse: (response: any) => {
        if (!Array.isArray(response)) return [];
        return response.map((app: any) => {
          const uStatus = app.status ? app.status.toUpperCase() : 'PENDING';
          const formattedStatus = uStatus.split(' ').map((word: string) => word.charAt(0) + word.slice(1).toLowerCase()).join(' ');
          return {
            id: app.id,
            role: app.job?.job_title || "Unknown Position",
            company: app.company || "Mariwasa Siam Ceramics",
            appliedDate: new Date(app.created_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }),
            status: formattedStatus,
            statusColor: uStatus === 'PENDING' ? "text-amber-600 bg-amber-50 border-amber-100" :
              (uStatus === 'REVIEWED' || uStatus === 'SCHEDULED') ? "text-blue-600 bg-blue-50 border-blue-100" :
                uStatus === 'TECHNICAL INTERVIEW' ? "text-purple-600 bg-purple-50 border-purple-100" :
                  uStatus === 'FINAL INTERVIEW' ? "text-indigo-600 bg-indigo-50 border-indigo-100" :
                    uStatus === 'ACCEPTED' ? "text-emerald-600 bg-emerald-50 border-emerald-100" :
                      uStatus === 'REJECTED' ? "text-rose-600 bg-rose-50 border-rose-100" :
                        "text-slate-600 bg-slate-50 border-slate-100",
            step: uStatus === 'PENDING' ? 1 : 
                  (uStatus === 'REVIEWED' || uStatus === 'SCHEDULED') ? 2 : 
                  uStatus === 'TECHNICAL INTERVIEW' ? 3 : 
                  uStatus === 'FINAL INTERVIEW' ? 4 : 
                  (uStatus === 'ACCEPTED' || uStatus === 'REJECTED') ? 5 : 1,
            totalSteps: 5,
            originalData: app
          };
        });
      },
    }),

    submitApplication: builder.mutation<any, any>({
      query: (application) => ({
        url: '/applications/',
        method: 'POST',
        body: application,
      }),
      invalidatesTags: ['Applications', 'Dashboard'],
    }),

    updateApplicationStatus: builder.mutation<any, { id: number | string; status: string }>({
      query: ({ id, status }) => ({
        url: `/applications/${id}/status`,
        method: 'PATCH',
        body: { status },
      }),
      async onQueryStarted({ id, status }, { dispatch, queryFulfilled }) {
        const patchResult = dispatch(
          apiSlice.util.updateQueryData('getApplications', undefined, (draft) => {
            const app = draft.find((a: any) => String(a.id) === String(id));
            if (app) {
              app.status = status.toUpperCase();
            }
          })
        );
        try {
          await queryFulfilled;
        } catch {
          patchResult.undo();
        }
      },
      invalidatesTags: ['Applications'],
    }),

    deleteApplication: builder.mutation<any, number | string>({
      query: (id) => ({
        url: `/applications/${id}`,
        method: 'DELETE',
      }),
      async onQueryStarted(id, { dispatch, queryFulfilled }) {
        const patchResult = dispatch(
          apiSlice.util.updateQueryData('getApplications', undefined, (draft) => {
            const index = draft.findIndex((a: any) => String(a.id) === String(id));
            if (index !== -1) {
              draft.splice(index, 1);
            }
          })
        );
        try {
          await queryFulfilled;
        } catch {
          patchResult.undo();
        }
      },
      invalidatesTags: ['Applications'],
    }),

    getActiveUsersCount: builder.query<any, void>({
      query: () => '/chat/active-count',
    }),

    // --- INTERVIEWS ---
    getAllInterviews: builder.query<any[], void>({
      query: () => '/interviews',
      providesTags: ['Interviews'],
    }),

    getCalendarFeed: builder.query<any, Record<string, any> | void>({
      query: (params = {}) => ({
        url: '/interviews/calendar-feed',
        params: params || {},
      }),
      providesTags: ['Interviews', 'CalendarEvents'],
    }),

    syncGoogleCalendar: builder.mutation<any, void>({
      query: () => ({
        url: '/interviews/sync',
        method: 'POST',
      }),
      invalidatesTags: ['Interviews', 'CalendarEvents'],
    }),

    getGoogleCalendarStatus: builder.query<any, void>({
      query: () => '/interviews/google-status',
      providesTags: ['CalendarEvents'],
    }),

    getAvailableSlots: builder.mutation<any, any>({
      query: (body) => ({
        url: '/interviews/available-slots',
        method: 'POST',
        body,
      }),
    }),

    getHRInterviewers: builder.query<any[], void>({
      query: () => '/hr/interviewers',
      providesTags: ['HRInterviewers'],
      keepUnusedDataFor: 300,
    }),

    scheduleInterview: builder.mutation<any, any>({
      query: (body) => ({
        url: '/interviews/schedule',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Applications', 'Dashboard', 'Interviews', 'CalendarEvents'],
    }),

    updateInterview: builder.mutation<any, { interviewId: number | string; [key: string]: any }>({
      query: ({ interviewId, ...body }) => ({
        url: `/interviews/${interviewId}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Interviews', 'CalendarEvents', 'Applications'],
    }),

    deleteInterview: builder.mutation<any, number | string>({
      query: (interviewId) => ({
        url: `/interviews/${interviewId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Interviews', 'CalendarEvents', 'Applications'],
    }),

    getApplicationInterviews: builder.query<any[], number | string>({
      query: (applicationId) => `/interviews/application/${applicationId}`,
      providesTags: (_result, _error, id) => [{ type: 'Applications' as const, id }],
    }),

    getCandidateInterviews: builder.query<any[], string>({
      query: (email) => `/interviews/candidate/${email}`,
      providesTags: ['Applications'],
    }),

    // --- ADMIN / HR TOOLS ---
    getUsers: builder.query<any[], void>({
      query: () => '/admins/users',
      providesTags: ['Users'],
      keepUnusedDataFor: 300,
    }),

    createUser: builder.mutation<any, any>({
      query: (body) => ({
        url: '/admins/users',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Users'],
    }),

    updateUser: builder.mutation<any, { userId: number | string; body: any }>({
      query: ({ userId, body }) => ({
        url: `/admins/users/${userId}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Users'],
    }),

    deleteUser: builder.mutation<any, number | string>({
      query: (userId) => ({
        url: `/admins/users/${userId}`,
        method: 'DELETE',
      }),
      async onQueryStarted(userId, { dispatch, queryFulfilled }) {
        const patchResult = dispatch(
          apiSlice.util.updateQueryData('getUsers', undefined, (draft) => {
            const index = draft.findIndex((u: any) => String(u.id) === String(userId));
            if (index !== -1) {
              draft.splice(index, 1);
            }
          })
        );
        try {
          await queryFulfilled;
        } catch {
          patchResult.undo();
        }
      },
      invalidatesTags: ['Users'],
    }),

    archiveUser: builder.mutation<any, number | string>({
      query: (userId) => ({
        url: `/admins/users/${userId}/archive`,
        method: 'PATCH',
      }),
      async onQueryStarted(userId, { dispatch, queryFulfilled }) {
        const patchResult = dispatch(
          apiSlice.util.updateQueryData('getUsers', undefined, (draft) => {
            const user = draft.find((u: any) => String(u.id) === String(userId));
            if (user) {
              user.is_archived = true;
            }
          })
        );
        try {
          await queryFulfilled;
        } catch {
          patchResult.undo();
        }
      },
      invalidatesTags: ['Users'],
    }),

    unarchiveUser: builder.mutation<any, number | string>({
      query: (userId) => ({
        url: `/admins/users/${userId}/unarchive`,
        method: 'PATCH',
      }),
      async onQueryStarted(userId, { dispatch, queryFulfilled }) {
        const patchResult = dispatch(
          apiSlice.util.updateQueryData('getUsers', undefined, (draft) => {
            const user = draft.find((u: any) => String(u.id) === String(userId));
            if (user) {
              user.is_archived = false;
            }
          })
        );
        try {
          await queryFulfilled;
        } catch {
          patchResult.undo();
        }
      },
      invalidatesTags: ['Users'],
    }),

    getAdminSystemStats: builder.query<any, void>({
      query: () => '/admins/system-stats',
      providesTags: ['Dashboard'],
      keepUnusedDataFor: 300,
    }),

    // --- SYSTEM CONFIGURATION ---
    getMatchingConfig: builder.query<any, void>({
      query: () => '/system-config/matching',
      providesTags: ['SystemConfig'],
    }),

    updateMatchingWeights: builder.mutation<any, any>({
      query: (body) => ({
        url: '/system-config/matching/weights',
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['SystemConfig', 'AuditLogs'],
    }),

    updateMatchingThresholds: builder.mutation<any, any>({
      query: (body) => ({
        url: '/system-config/matching/thresholds',
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['SystemConfig', 'AuditLogs'],
    }),

    recalculateMatchingScores: builder.mutation<any, void>({
      query: () => ({
        url: '/system-config/matching/recalculate',
        method: 'POST',
      }),
      invalidatesTags: ['Applications', 'Dashboard', 'Candidates'],
    }),

    changeUserRole: builder.mutation<any, { userId: number | string; role: string }>({
      query: ({ userId, role }) => ({
        url: `/system-config/users/${userId}/role`,
        method: 'PATCH',
        body: { role },
      }),
      invalidatesTags: ['Users', 'AuditLogs'],
    }),

    getFormTemplates: builder.query<any[], void>({
      query: () => '/system-config/templates',
      providesTags: ['Templates'],
    }),

    createFormTemplate: builder.mutation<any, any>({
      query: (body) => ({
        url: '/system-config/templates',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Templates', 'AuditLogs'],
    }),

    updateFormTemplate: builder.mutation<any, { templateId: number | string; body: any }>({
      query: ({ templateId, body }) => ({
        url: `/system-config/templates/${templateId}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Templates', 'AuditLogs'],
    }),

    deleteFormTemplate: builder.mutation<any, number | string>({
      query: (templateId) => ({
        url: `/system-config/templates/${templateId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Templates', 'AuditLogs'],
    }),

    getSystemPerformance: builder.query<any, void>({
      query: () => '/system-config/performance',
      providesTags: ['Dashboard'],
    }),

    // --- DATA MANAGEMENT & SECURITY ---
    createDataBackup: builder.mutation<any, void>({
      query: () => ({
        url: '/admins/data-backup',
        method: 'POST',
      }),
      invalidatesTags: ['AuditLogs'],
    }),

    recoverData: builder.mutation<any, void>({
      query: () => ({
        url: '/admins/data-recovery',
        method: 'POST',
      }),
      invalidatesTags: ['AuditLogs'],
    }),

    getRetentionPolicy: builder.query<any, void>({
      query: () => '/admins/retention-policy',
      providesTags: ['SystemConfig'],
    }),

    updateRetentionPolicy: builder.mutation<any, any>({
      query: (body) => ({
        url: '/admins/retention-policy',
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['SystemConfig', 'AuditLogs'],
    }),

    // --- CELERY BACKGROUND WORKER MONITORING ---
    getCeleryTaskStatus: builder.query<any, string>({
      query: (taskId) => `/admins/tasks/${taskId}`,
    }),

    triggerMLRetrain: builder.mutation<any, void>({
      query: () => ({
        url: '/admins/ml/retrain',
        method: 'POST',
      }),
      invalidatesTags: ['Dashboard'],
    }),

  }),
});

export const {
  useGetDashboardStatsQuery,
  useGetCandidateCountQuery,
  useGetResumeCountQuery,
  useGetDashboardTrendsQuery,
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
  useGetAvailableSlotsMutation,
  useGetHRInterviewersQuery,
  useScheduleInterviewMutation,
  useGetAllInterviewsQuery,
  useGetCalendarFeedQuery,
  useSyncGoogleCalendarMutation,
  useGetGoogleCalendarStatusQuery,
  useUpdateInterviewMutation,
  useDeleteInterviewMutation,
  useGetApplicationInterviewsQuery,
  useGetCandidateInterviewsQuery,
  useGetUsersQuery,
  useCreateUserMutation,
  useUpdateUserMutation,
  useDeleteUserMutation,
  useArchiveUserMutation,
  useUnarchiveUserMutation,
  useGetAdminSystemStatsQuery,
  useGetActiveUsersCountQuery,
  useGetMatchingConfigQuery,
  useUpdateMatchingWeightsMutation,
  useUpdateMatchingThresholdsMutation,
  useRecalculateMatchingScoresMutation,
  useChangeUserRoleMutation,
  useGetFormTemplatesQuery,
  useCreateFormTemplateMutation,
  useUpdateFormTemplateMutation,
  useDeleteFormTemplateMutation,
  useGetSystemPerformanceQuery,
  useCreateDataBackupMutation,
  useRecoverDataMutation,
  useGetRetentionPolicyQuery,
  useUpdateRetentionPolicyMutation,
  useGetCeleryTaskStatusQuery,
  useLazyGetCeleryTaskStatusQuery,
  useTriggerMLRetrainMutation,
} = apiSlice;
