import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { API_BASE_URL } from '../../services/api';
import { broadcastAtsUpdate } from '../../utils/realtimeSync';

const normalizeApplicationItem = (app: any) => ({
  id: app.id,
  job_id: app.job_id ?? app.job?.id ?? undefined,
  applied_job_id: app.job_id ?? app.job?.id ?? undefined,
  applied_job_title: app.job?.job_title || app.job_title || 'Unknown',
  job_title: app.job_title || '',
  job: app.job || undefined,
  user_id: app.user_id ?? app.applicant_id ?? undefined,
  applicant_id: app.user_id ?? app.applicant_id ?? undefined,
  name: app.candidate_name,
  status: app.status,
  preferredJob: app.job?.job_title || app.job_title || 'Unknown',
  skills: app.skills || [],
  profileImage: app.profile_image_url || null,
  resumeUrl: app.resume_url || null,
  date: app.created_at,
  location: app.location || 'N/A',
  jobLocation: app.job?.location || 'N/A',
  jobDepartment: app.job?.department || 'N/A',
  company: app.company || 'N/A',
  degree: app.degree || '',
  college: app.college || '',
  relevance: app.relevance || '',
  match_score: app.match_score ?? null,
  matchScore:
    app.match_score !== null && app.match_score !== undefined
      ? Number(app.match_score)
      : Math.round(
        (app.skills_score || 0) * 0.40 +
        (app.experience_score || 0) * 0.30 +
        (app.education_score || 0) * 0.15 +
        (app.certifications_score || 0) * 0.10 +
        (app.completeness_score ?? 100) * 0.05
      ) || 0,
  skillsScore: app.skills_score || 0,
  skills_score: app.skills_score || 0,
  experienceScore: app.experience_score || 0,
  experience_score: app.experience_score || 0,
  educationScore: app.education_score || 0,
  education_score: app.education_score || 0,
  certificationsScore: app.certifications_score || 0,
  certifications_score: app.certifications_score || 0,
  completenessScore: app.completeness_score ?? null,
  completeness_score: app.completeness_score ?? null,
  completeness_status: app.completeness_status ?? undefined,
  missing_sections: app.missing_sections || [],
  hr_shortlist_notes: app.hr_shortlist_notes ?? undefined,
  applied_weights: app.applied_weights ?? null,
  skills_status: app.skills_status || null,
  experience_status: app.experience_status || null,
  education_status: app.education_status || null,
  certifications_status: app.certifications_status || null,
  education_needs_manual_review: Boolean(app.education_needs_manual_review),
  skills_reason: app.skills_reason,
  experience_reason: app.experience_reason,
  education_reason: app.education_reason,
  certifications_reason: app.certifications_reason,
  matched_skills: app.matched_skills || [],
  missing_skills: app.missing_skills || [],
  requirement_evaluations: app.requirement_evaluations || [],
  clarification_responses: app.clarification_responses || [],
  relevant_experience: app.relevant_experience || null,
  experience_gaps: app.experience_gaps || null,
  work_experiences: app.work_experiences || [],
  total_experience_months: app.total_experience_months || 0,
  highest_educational_attainment: app.highest_educational_attainment || null,
  education_entries: app.education_entries || [],
  required_degree: app.required_degree || null,
  candidate_degree: app.candidate_degree || null,
  required_certifications: app.required_certifications || null,
  certifications: app.certifications || app.candidate_certifications || null,
  candidate_certifications: app.candidate_certifications || app.certifications || null,
  certifications_details: app.certifications_details || null,
  skills_details: app.skills_details || null,
  recommendations: app.recommendations || [],
  recommended_positions: Array.isArray(app.recommended_positions) ? app.recommended_positions : [],
  other_applications: Array.isArray(app.other_applications) ? app.other_applications : [],
  ai_summary: app.ai_summary || '',
  strengths: app.strengths || [],
  weaknesses: app.weaknesses || [],
  ai_powered: Boolean(app.ai_powered),
  email: app.contact_email || app.candidate_email,
  candidate_email: app.contact_email || app.candidate_email,
  contact_email: app.contact_email || app.candidate_email,
  resume_email: app.resume_email || undefined,
  phone: app.phone || 'N/A',
  candidate_name: app.candidate_name,
});

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
  tagTypes: ['Dashboard', 'Jobs', 'Candidates', 'Applications', 'AuditLogs', 'Users', 'SystemConfig', 'Templates', 'NotificationTemplates', 'Interviews', 'CalendarEvents', 'HRInterviewers', 'PhysicalResumes', 'Shortlists', 'StatusHistory', 'ApplicantProfile'],
  endpoints: (builder) => ({
    // --- DASHBOARD STATS ---
    getDashboardStats: builder.query<any, void>({
      query: () => '/hr/application-stats',
      providesTags: ['Dashboard'],
      keepUnusedDataFor: 300,
    }),
    getCandidateCount: builder.query<any, void>({
      query: () => '/hr/candidate-count',
      providesTags: ['Candidates', 'Dashboard'],
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
    getJobs: builder.query<any[], { include_inactive?: boolean; include_archived?: boolean } | void>({
      query: (params) => {
        const p = params as { include_inactive?: boolean; include_archived?: boolean } | undefined;
        const includeInactive = p?.include_inactive ?? false;
        const includeArchived = p?.include_archived ?? false;
        return `/admins/read-jobs?include_inactive=${includeInactive}&include_archived=${includeArchived}`;
      },
      providesTags: ['Jobs'],
      keepUnusedDataFor: 300,
      transformResponse: (response: any) => {
        const rawData = Array.isArray(response) ? response : [];
        return rawData.map((job: any) => {
          const normalizedStatus = (job.status || (job.is_active ? 'ACTIVE' : 'ARCHIVED')).toUpperCase();
          return {
            ...job,
            title: job.job_title || "Untitled Position",
            department: job.department || "General",
            location: job.location || "Remote / Not Specified",
            salary_range: job.salary_range || "Competitive / TBD",
            status: normalizedStatus,
            is_active: normalizedStatus === 'ACTIVE',
          };
        });
      },
    }),

    getJobClosePreview: builder.query<any, number | string>({
      query: (jobId) => `/admins/jobs/${jobId}/close-preview`,
    }),

    changeJobStatus: builder.mutation<any, { jobId: number | string; status: string }>({
      query: ({ jobId, status }) => ({
        url: `/admins/jobs/${jobId}/status`,
        method: 'PATCH',
        body: { status },
      }),
      async onQueryStarted(_arg, { queryFulfilled }) {
        try {
          await queryFulfilled;
          broadcastAtsUpdate('job_update');
        } catch {
          // status transition failed
        }
      },
      invalidatesTags: ['Jobs', 'Applications', 'Dashboard', 'Shortlists'],
    }),

    createJob: builder.mutation<any, any>({
      query: (newJob) => ({
        url: '/admins/createjob',
        method: 'POST',
        body: newJob,
      }),
      async onQueryStarted(_arg, { queryFulfilled }) {
        try {
          await queryFulfilled;
          broadcastAtsUpdate('job_creation');
        } catch {
          // creation failed
        }
      },
      invalidatesTags: ['Jobs', 'Dashboard'],
    }),

    updateJob: builder.mutation<any, { jobId: number | string; body: any }>({
      query: ({ jobId, body }) => ({
        url: `/admins/update-job/${jobId}`,
        method: 'PATCH',
        body,
      }),
      async onQueryStarted(_arg, { queryFulfilled }) {
        try {
          await queryFulfilled;
          broadcastAtsUpdate('job_update');
        } catch {
          // update failed
        }
      },
      invalidatesTags: ['Jobs', 'Applications', 'Dashboard'],
    }),

    recalculateJobScores: builder.mutation<any, number | string>({
      query: (jobId) => ({
        url: `/admins/jobs/${jobId}/recalculate-scores`,
        method: 'POST',
      }),
      invalidatesTags: ['Applications', 'Dashboard', 'Candidates', 'Shortlists'],
    }),

    archiveJob: builder.mutation<any, number | string>({
      query: (jobId) => ({
        url: `/admins/archive-job/${jobId}`,
        method: 'PATCH',
      }),
      async onQueryStarted(_arg, { queryFulfilled }) {
        try {
          await queryFulfilled;
          broadcastAtsUpdate('job_update');
        } catch {
          // archive failed
        }
      },
      invalidatesTags: ['Jobs', 'Dashboard'],
    }),

    unarchiveJob: builder.mutation<any, number | string>({
      query: (jobId) => ({
        url: `/admins/unarchive-job/${jobId}`,
        method: 'PATCH',
      }),
      async onQueryStarted(_arg, { queryFulfilled }) {
        try {
          await queryFulfilled;
          broadcastAtsUpdate('job_update');
        } catch {
          // unarchive failed
        }
      },
      invalidatesTags: ['Jobs', 'Dashboard'],
    }),

    deleteJob: builder.mutation<any, number | string>({
      query: (jobId) => ({
        url: `/admins/delete-job/${jobId}`,
        method: 'DELETE',
      }),
      async onQueryStarted(_arg, { queryFulfilled }) {
        try {
          await queryFulfilled;
          broadcastAtsUpdate('job_update');
        } catch {
          // delete failed
        }
      },
      invalidatesTags: ['Jobs', 'Dashboard', 'Applications'],
    }),

    getApplications: builder.query<any[], void>({
      query: () => '/applications/',
      providesTags: ['Applications'],
      keepUnusedDataFor: 300,
      transformResponse: (response: any[]) => (response || []).map(normalizeApplicationItem),
    }),

    getApplicationsSummary: builder.query<any[], void>({
      query: () => '/applications/?summary=true',
      providesTags: ['Applications'],
      keepUnusedDataFor: 300,
      transformResponse: (response: any[]) => (response || []).map(normalizeApplicationItem),
    }),

    getApplicationById: builder.query<any, number | string>({
      query: (applicationId) => `/applications/${applicationId}`,
      providesTags: (_result, _error, id) => [{ type: 'Applications' as const, id }, 'Applications'],
      keepUnusedDataFor: 300,
      transformResponse: (response: any) => (response ? normalizeApplicationItem(response) : null),
    }),

    getCandidateApplications: builder.query<any[], string>({
      query: (email) => `/applications/candidate/${email}`,
      providesTags: ['Applications'],
      transformResponse: (response: any) => {
        if (!Array.isArray(response)) return [];
        return response.map((app: any) => {
          const uStatus = (app.status || 'SUBMITTED').trim().toUpperCase();
          const isPassed =
            uStatus === 'PASSED INITIAL INTERVIEW' ||
            uStatus === 'PASSED' ||
            uStatus === 'ACCEPTED' ||
            uStatus.includes('ENDORSED');
          const isWithdrawnHired =
            uStatus.includes('HIRED ELSEWHERE') || uStatus === 'WITHDRAWN_HIRED_ELSEWHERE';
          const isWithdrawn = uStatus.startsWith('WITHDRAWN');
          const isNotSelected =
            uStatus === 'NOT SELECTED' ||
            uStatus === 'NOT_SELECTED' ||
            uStatus === 'REJECTED' ||
            uStatus === 'ARCHIVED' ||
            uStatus === 'PASSED_OVER';
          const isOnHold = uStatus === 'ON HOLD' || uStatus === 'ON_HOLD';
          const isInterviewed = uStatus === 'INTERVIEWED';
          const isInterviewScheduled =
            uStatus === 'INTERVIEW SCHEDULED' ||
            uStatus === 'TECHNICAL INTERVIEW' ||
            uStatus === 'INTERVIEW' ||
            uStatus === 'SCHEDULED';
          const isShortlisted = uStatus === 'SHORTLISTED' || uStatus === 'SHORTLIST';
          const isReviewed =
            uStatus === 'UNDER REVIEW' || uStatus === 'REVIEWED' || uStatus === 'SCREENED';

          let formattedStatus = 'Submitted';
          let statusColor = 'text-amber-700 bg-amber-50 border-amber-200';
          let step = 1;
          let group: 'active' | 'completed' | 'withdrawn' = 'active';
          let isReadOnly = false;

          if (isPassed) {
            formattedStatus = 'Passed Initial Interview – Endorsed for next stage';
            statusColor = 'text-emerald-700 bg-emerald-50 border-emerald-200';
            step = 4;
            group = 'completed';
            isReadOnly = true;
          } else if (isNotSelected) {
            formattedStatus = 'Not selected';
            statusColor = 'text-rose-700 bg-rose-50 border-rose-200';
            step = 0;
            group = 'completed';
          } else if (isWithdrawnHired) {
            formattedStatus = 'Withdrawn – hired elsewhere in company';
            statusColor = 'text-slate-600 bg-slate-100 border-slate-200';
            step = 0;
            group = 'withdrawn';
            isReadOnly = true;
          } else if (isWithdrawn) {
            formattedStatus = 'Withdrawn by applicant';
            statusColor = 'text-slate-600 bg-slate-100 border-slate-200';
            step = 0;
            group = 'withdrawn';
            isReadOnly = true;
          } else if (isOnHold) {
            formattedStatus = 'On Hold';
            statusColor = 'text-amber-800 bg-amber-50 border-amber-300';
            step = 3;
            group = 'active';
          } else if (isInterviewed) {
            formattedStatus = 'Interviewed';
            statusColor = 'text-indigo-700 bg-indigo-50 border-indigo-200';
            step = 4;
            group = 'active';
          } else if (isInterviewScheduled) {
            formattedStatus = 'Interview Scheduled';
            statusColor = 'text-purple-700 bg-purple-50 border-purple-200';
            step = 4;
            group = 'active';
          } else if (isShortlisted) {
            formattedStatus = 'Shortlisted';
            statusColor = 'text-emerald-700 bg-emerald-50 border-emerald-200';
            step = 3;
            group = 'active';
          } else if (isReviewed) {
            formattedStatus = 'Under Review';
            statusColor = 'text-blue-700 bg-blue-50 border-blue-200';
            step = 2;
            group = 'active';
          }

          return {
            id: app.id,
            role: app.job?.job_title || app.job_title || "Unknown Position",
            company: app.company || "Mariwasa Siam Ceramics",
            appliedDate: new Date(app.created_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }),
            status: formattedStatus,
            rawStatus: uStatus,
            group,
            isReadOnly,
            statusColor,
            step,
            totalSteps: 4,
            originalData: app
          };
        });
      },
    }),

    withdrawApplication: builder.mutation<any, { applicationId: number | string; reason?: string }>({
      query: ({ applicationId, reason }) => ({
        url: `/applications/${applicationId}/withdraw`,
        method: 'POST',
        body: { reason },
      }),
      invalidatesTags: ['Applications', 'Dashboard', 'Interviews', 'Shortlists', 'ApplicantProfile'],
    }),

    postPassAction: builder.mutation<any, { applicationId: number | string; action: 'on_hold' | 'continue'; target_application_ids: number[]; note?: string }>({
      query: ({ applicationId, ...body }) => ({
        url: `/applications/${applicationId}/post-pass-action`,
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Applications', 'Dashboard', 'Shortlists', 'ApplicantProfile'],
    }),

    resumeApplication: builder.mutation<any, { applicationId: number | string; note?: string }>({
      query: ({ applicationId, note }) => ({
        url: `/applications/${applicationId}/resume`,
        method: 'POST',
        body: { note },
      }),
      invalidatesTags: ['Applications', 'Dashboard', 'Shortlists', 'ApplicantProfile'],
    }),

    withdrawHiredElsewhere: builder.mutation<any, { applicationId: number | string; note?: string }>({
      query: ({ applicationId, note }) => ({
        url: `/applications/${applicationId}/withdraw-hired-elsewhere`,
        method: 'POST',
        body: { note },
      }),
      invalidatesTags: ['Applications', 'Dashboard', 'Interviews', 'Shortlists', 'ApplicantProfile'],
    }),

    getCandidateShortlistedForCombined: builder.query<any, number | string>({
      query: (applicationId) => `/interviews/candidate-shortlisted/${applicationId}`,
      providesTags: ['Applications', 'Interviews'],
    }),

    submitApplication: builder.mutation<any, any>({
      query: (application) => ({
        url: '/applications/',
        method: 'POST',
        body: application,
      }),
      async onQueryStarted(_arg, { queryFulfilled }) {
        try {
          await queryFulfilled;
          broadcastAtsUpdate('applications_updated');
        } catch {
          // submission failed
        }
      },
      invalidatesTags: (_result, _error, arg) => [
        'Applications',
        'Dashboard',
        'Candidates',
        'Shortlists',
        { type: 'StatusHistory', id: typeof arg === 'object' && arg !== null && 'id' in arg ? (arg as any).id : arg },
      ],
    }),

    updateApplicationStatus: builder.mutation<
      any,
      {
        id: number | string;
        status: string;
        notes?: string;
        custom_email_subject?: string;
        custom_email_message?: string;
      }
    >({
      query: ({ id, status, notes, custom_email_subject, custom_email_message }) => ({
        url: `/applications/${id}/status`,
        method: 'PATCH',
        body: {
          status,
          ...(notes !== undefined ? { notes } : {}),
          ...(custom_email_subject !== undefined ? { custom_email_subject } : {}),
          ...(custom_email_message !== undefined ? { custom_email_message } : {}),
        },
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
          broadcastAtsUpdate('applications_updated');
        } catch {
          patchResult.undo();
        }
      },
      invalidatesTags: (_result, _error, arg) => [
        'Applications',
        'Dashboard',
        'Candidates',
        'Shortlists',
        { type: 'StatusHistory', id: arg.id },
      ],
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
          broadcastAtsUpdate('applications_updated');
        } catch {
          patchResult.undo();
        }
      },
      invalidatesTags: (_result, _error, id) => [
        'Applications',
        'Dashboard',
        'Candidates',
        'Shortlists',
        { type: 'StatusHistory', id },
      ],
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

    getGoogleCalendarStatus: builder.query<any, string | number | void>({
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

    updateInterview: builder.mutation<any, { interviewId: number | string;[key: string]: any }>({
      query: ({ interviewId, ...body }) => ({
        url: `/interviews/${interviewId}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Interviews', 'CalendarEvents', 'Applications'],
    }),

    candidateRescheduleInterview: builder.mutation<
      any,
      { interviewId: number | string; start_time: string; end_time: string; reason?: string }
    >({
      query: ({ interviewId, ...body }) => ({
        url: `/interviews/${interviewId}/candidate-reschedule`,
        method: 'POST',
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

    cancelInterview: builder.mutation<
      any,
      {
        interviewId: number | string;
        reason?: string;
        custom_email_subject?: string;
        custom_email_message?: string;
        custom_sms_message?: string;
      }
    >({
      query: ({ interviewId, ...body }) => ({
        url: `/interviews/${interviewId}/cancel`,
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Interviews', 'CalendarEvents', 'Applications'],
    }),

    getApplicationInterviews: builder.query<any[], number | string>({
      query: (applicationId) => `/interviews/application/${applicationId}`,
      providesTags: (_result, _error, id) => [{ type: 'Applications' as const, id }, 'Applications', 'Interviews'],
    }),

    getCandidateInterviews: builder.query<any[], string>({
      query: (email) => `/interviews/candidate/${encodeURIComponent(email)}`,
      providesTags: ['Applications', 'Interviews'],
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
    getInterviewDefaults: builder.query<{ company_address: string }, void>({
      query: () => '/interviews/defaults',
    }),
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
      invalidatesTags: ['Applications', 'Dashboard', 'Candidates', 'Shortlists'],
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

    getNotificationTemplates: builder.query<Record<string, any>, void>({
      query: () => '/system-config/notification-templates',
      transformResponse: (res: any) => res?.templates || res || {},
      providesTags: ['NotificationTemplates'],
    }),

    updateNotificationTemplates: builder.mutation<
      Record<string, any>,
      Record<string, { email_subject?: string; email_message?: string; sms_message?: string }>
    >({
      query: (templates) => ({
        url: '/system-config/notification-templates',
        method: 'PUT',
        body: { templates },
      }),
      transformResponse: (res: any) => res?.templates || res || {},
      invalidatesTags: ['NotificationTemplates', 'AuditLogs'],
    }),

    resetNotificationTemplates: builder.mutation<
      Record<string, any>,
      { template_key?: string } | void
    >({
      query: (body) => ({
        url: '/system-config/notification-templates/reset',
        method: 'POST',
        body: body || {},
      }),
      transformResponse: (res: any) => res?.templates || res || {},
      invalidatesTags: ['NotificationTemplates', 'AuditLogs'],
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

    // --- PHYSICAL RESUMES STORAGE ---
    getPhysicalResumes: builder.query<any, { search?: string; status?: string; job_id?: number; page?: number; limit?: number } | void>({
      query: (params) => {
        const p = params as { search?: string; status?: string; job_id?: number; page?: number; limit?: number } | undefined;
        const queryParams = new URLSearchParams();
        if (p?.search) queryParams.append('search', p.search);
        if (p?.status && p.status !== 'All') queryParams.append('status', p.status);
        if (p?.job_id) queryParams.append('job_id', String(p.job_id));
        if (p?.page) queryParams.append('page', String(p.page));
        if (p?.limit) queryParams.append('limit', String(p.limit));
        const qs = queryParams.toString();
        return `/hr/physical-resumes/${qs ? `?${qs}` : ''}`;
      },
      providesTags: ['PhysicalResumes'],
      keepUnusedDataFor: 60,
    }),

    getPhysicalResumeStats: builder.query<any, void>({
      query: () => '/hr/physical-resumes/stats',
      providesTags: ['PhysicalResumes'],
      keepUnusedDataFor: 60,
    }),

    getPhysicalResumeById: builder.query<any, number | string>({
      query: (id) => `/hr/physical-resumes/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'PhysicalResumes', id }],
    }),

    uploadPhysicalResume: builder.mutation<any, FormData>({
      query: (formData) => ({
        url: '/hr/physical-resumes/upload',
        method: 'POST',
        body: formData,
      }),
      invalidatesTags: ['PhysicalResumes', 'Applications', 'Candidates', 'Dashboard', 'Jobs', 'Shortlists'],
    }),

    checkImportDuplicate: builder.query<any, { email: string; jobId: number | string }>({
      query: ({ email, jobId }) => `/hr/physical-resumes/check-duplicate?email=${encodeURIComponent(email)}&job_id=${jobId}`,
    }),

    updatePhysicalResume: builder.mutation<any, { id: number | string; body: any }>({
      query: ({ id, body }) => ({
        url: `/hr/physical-resumes/${id}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['PhysicalResumes', 'Applications', 'Candidates'],
    }),

    deletePhysicalResume: builder.mutation<any, number | string>({
      query: (id) => ({
        url: `/hr/physical-resumes/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['PhysicalResumes', 'Dashboard', 'Applications', 'Candidates'],
    }),

    // --- STATUS HISTORY & AUTO STATUS ---
    recordApplicationViewed: builder.mutation<any, { id: number | string; view_duration_seconds: number; visible_focused: boolean; engaged: boolean }>({
      query: ({ id, ...body }) => ({
        url: `/applications/${id}/viewed`,
        method: 'POST',
        body,
      }),
      invalidatesTags: (_result, _error, arg) => [
        'Applications',
        'Dashboard',
        'Candidates',
        'Shortlists',
        { type: 'StatusHistory', id: arg.id },
      ],
    }),

    getApplicationHistory: builder.query<any[], number | string>({
      query: (id) => `/applications/${id}/history`,
      providesTags: (_result, _error, id) => [{ type: 'StatusHistory', id }],
    }),

    undoAutoStatus: builder.mutation<any, number | string>({
      query: (id) => ({
        url: `/applications/${id}/undo-auto-status`,
        method: 'POST',
      }),
      invalidatesTags: (_result, _error, id) => [
        'Applications',
        'Dashboard',
        'Candidates',
        'Shortlists',
        { type: 'StatusHistory', id },
      ],
    }),

    // --- SHORTLIST ROSTERS ---
    getShortlistRosters: builder.query<any[], { jobId?: number; archived?: boolean } | void>({
      query: (params) => {
        const p = params as { jobId?: number; archived?: boolean } | undefined;
        const searchParams = new URLSearchParams();
        if (p?.jobId) searchParams.append('job_id', String(p.jobId));
        if (typeof p?.archived === 'boolean') searchParams.append('archived', String(p.archived));
        const qs = searchParams.toString();
        return qs ? `/hr/shortlists?${qs}` : '/hr/shortlists';
      },
      providesTags: ['Shortlists'],
    }),

    getShortlistRosterById: builder.query<any, number | string>({
      query: (id) => `/hr/shortlists/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'Shortlists', id }],
    }),

    createShortlistRoster: builder.mutation<any, { job_id: number; name: string; notes?: string; application_ids?: number[]; non_shortlisted_action?: string; finalize?: boolean; confirm_notify_non_shortlisted?: boolean }>({
      query: (body) => ({
        url: '/hr/shortlists',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Shortlists', 'Applications', 'Dashboard', 'Candidates'],
    }),

    previewShortlistNonShortlisted: builder.mutation<any, { job_id: number; shortlisted_application_ids?: number[]; roster_id?: number }>({
      query: (body) => ({
        url: '/hr/shortlists/preview-non-shortlisted',
        method: 'POST',
        body,
      }),
    }),

    getRosterFinalizePreview: builder.query<any, number | string>({
      query: (rosterId) => `/hr/shortlists/${rosterId}/finalize-preview`,
    }),

    updateRosterNonShortlistedPolicy: builder.mutation<any, { rosterId: number | string; non_shortlisted_action: string }>({
      query: ({ rosterId, non_shortlisted_action }) => ({
        url: `/hr/shortlists/${rosterId}/non-shortlisted-policy`,
        method: 'PATCH',
        body: { non_shortlisted_action },
      }),
      invalidatesTags: ['Shortlists'],
    }),

    finalizeShortlistRoster: builder.mutation<any, { rosterId: number | string; non_shortlisted_action?: string; confirm?: boolean }>({
      query: ({ rosterId, non_shortlisted_action, confirm = true }) => ({
        url: `/hr/shortlists/${rosterId}/finalize`,
        method: 'POST',
        body: { non_shortlisted_action, confirm },
      }),
      invalidatesTags: ['Shortlists', 'Applications', 'Dashboard', 'Candidates'],
    }),

    getRecruitmentConfig: builder.query<any, void>({
      query: () => '/system-config/recruitment',
      providesTags: ['SystemConfig'],
    }),

    updateRecruitmentConfig: builder.mutation<any, Record<string, any>>({
      query: (body) => ({
        url: '/system-config/recruitment',
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['SystemConfig'],
    }),

    runRetentionAnonymization: builder.mutation<any, { dry_run: boolean; retention_months?: number }>({
      query: (body) => ({
        url: '/system-config/retention/run',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['SystemConfig', 'Applications', 'Users'],
    }),

    getRetentionLogs: builder.query<any[], number | void>({
      query: (limit = 25) => `/system-config/retention/logs?limit=${limit}`,
      providesTags: ['SystemConfig'],
    }),

    addCandidateToRoster: builder.mutation<any, { rosterId: number | string; applicationId: number | string }>({
      query: ({ rosterId, applicationId }) => ({
        url: `/hr/shortlists/${rosterId}/items`,
        method: 'POST',
        body: { application_id: Number(applicationId) },
      }),
      invalidatesTags: (_result, _error, { applicationId }) => [
        'Shortlists',
        'Applications',
        'Dashboard',
        'Candidates',
        { type: 'StatusHistory', id: applicationId },
      ],
    }),

    removeCandidateFromRoster: builder.mutation<any, { rosterId: number | string; applicationId: number | string }>({
      query: ({ rosterId, applicationId }) => ({
        url: `/hr/shortlists/${rosterId}/items/${applicationId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_result, _error, { applicationId }) => [
        'Shortlists',
        'Applications',
        'Dashboard',
        'Candidates',
        { type: 'StatusHistory', id: applicationId },
      ],
    }),

    updateRosterStage: builder.mutation<any, { rosterId: number | string; applicationId: number | string; stage: string; notes?: string }>({
      query: ({ rosterId, applicationId, stage, notes }) => ({
        url: `/hr/shortlists/${rosterId}/items/${applicationId}/stage`,
        method: 'PATCH',
        body: { stage, notes },
      }),
      invalidatesTags: (_result, _error, { applicationId }) => [
        'Shortlists',
        'Applications',
        'Dashboard',
        'Candidates',
        { type: 'StatusHistory', id: applicationId },
      ],
    }),

    archiveShortlistRoster: builder.mutation<any, { rosterId: number | string; archived: boolean }>({
      query: ({ rosterId, archived }) => ({
        url: `/hr/shortlists/${rosterId}/archive?archived=${archived}`,
        method: 'PATCH',
      }),
      invalidatesTags: ['Shortlists', 'Dashboard'],
    }),

    deleteShortlistRoster: builder.mutation<any, number | string>({
      query: (rosterId) => ({
        url: `/hr/shortlists/${rosterId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Shortlists', 'Applications', 'Dashboard', 'Candidates'],
    }),

    // --- UNIVERSAL SEARCH (HR) ---
    universalSearchHR: builder.query<any, string>({
      query: (q) => `/hr/universal-search?q=${encodeURIComponent(q)}`,
    }),

    // --- APPLICANT COMPREHENSIVE PROFILE (HR) ---
    getApplicantProfile: builder.query<any, string>({
      query: (email) => `/hr/applicant-profile/${encodeURIComponent(email)}`,
      providesTags: (_result, _error, email) => [{ type: 'ApplicantProfile', id: email }],
    }),

    addApplicantNote: builder.mutation<any, { email: string; content: string }>({
      query: ({ email, content }) => ({
        url: `/hr/applicant-profile/${encodeURIComponent(email)}/notes`,
        method: 'POST',
        body: { content },
      }),
      invalidatesTags: (_result, _error, { email }) => [{ type: 'ApplicantProfile', id: email }],
    }),

    // --- CANDIDATE COMPARISON (HR) ---
    compareCandidates: builder.mutation<any, { application_ids: number[]; reference_job_id?: number | null }>({
      query: (body) => ({
        url: '/hr/compare',
        method: 'POST',
        body,
      }),
    }),
  }),
});

export const {
  useGetDashboardStatsQuery,
  useGetCandidateCountQuery,
  useGetResumeCountQuery,
  useGetDashboardTrendsQuery,
  useGetJobsQuery,
  useLazyGetJobClosePreviewQuery,
  useChangeJobStatusMutation,
  useGetApplicationsQuery,
  useGetApplicationsSummaryQuery,
  useGetApplicationByIdQuery,
  useGetCandidateApplicationsQuery,
  useSubmitApplicationMutation,
  useWithdrawApplicationMutation,
  usePostPassActionMutation,
  useResumeApplicationMutation,
  useWithdrawHiredElsewhereMutation,
  useGetCandidateShortlistedForCombinedQuery,
  useDeleteApplicationMutation,
  useCreateJobMutation,
  useUpdateJobMutation,
  useRecalculateJobScoresMutation,
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
  useCandidateRescheduleInterviewMutation,
  useDeleteInterviewMutation,
  useCancelInterviewMutation,
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
  useGetInterviewDefaultsQuery,
  useGetMatchingConfigQuery,
  useUpdateMatchingWeightsMutation,
  useUpdateMatchingThresholdsMutation,
  useRecalculateMatchingScoresMutation,
  useChangeUserRoleMutation,
  useGetFormTemplatesQuery,
  useCreateFormTemplateMutation,
  useUpdateFormTemplateMutation,
  useDeleteFormTemplateMutation,
  useGetNotificationTemplatesQuery,
  useUpdateNotificationTemplatesMutation,
  useResetNotificationTemplatesMutation,
  useGetSystemPerformanceQuery,
  useCreateDataBackupMutation,
  useRecoverDataMutation,
  useGetRetentionPolicyQuery,
  useUpdateRetentionPolicyMutation,
  useGetCeleryTaskStatusQuery,
  useLazyGetCeleryTaskStatusQuery,
  useTriggerMLRetrainMutation,
  useGetPhysicalResumesQuery,
  useGetPhysicalResumeStatsQuery,
  useGetPhysicalResumeByIdQuery,
  useUploadPhysicalResumeMutation,
  useCheckImportDuplicateQuery,
  useLazyCheckImportDuplicateQuery,
  useUpdatePhysicalResumeMutation,
  useDeletePhysicalResumeMutation,
  useRecordApplicationViewedMutation,
  useGetApplicationHistoryQuery,
  useUndoAutoStatusMutation,
  useGetShortlistRostersQuery,
  useGetShortlistRosterByIdQuery,
  useCreateShortlistRosterMutation,
  usePreviewShortlistNonShortlistedMutation,
  useGetRosterFinalizePreviewQuery,
  useLazyGetRosterFinalizePreviewQuery,
  useUpdateRosterNonShortlistedPolicyMutation,
  useFinalizeShortlistRosterMutation,
  useGetRecruitmentConfigQuery,
  useUpdateRecruitmentConfigMutation,
  useRunRetentionAnonymizationMutation,
  useGetRetentionLogsQuery,
  useAddCandidateToRosterMutation,
  useRemoveCandidateFromRosterMutation,
  useUpdateRosterStageMutation,
  useArchiveShortlistRosterMutation,
  useDeleteShortlistRosterMutation,
  useUniversalSearchHRQuery,
  useLazyUniversalSearchHRQuery,
  useGetApplicantProfileQuery,
  useAddApplicantNoteMutation,
  useCompareCandidatesMutation,
} = apiSlice;
