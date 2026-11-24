import React, { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate, useParams } from '@/utils/navigation';
import { useSelector } from 'react-redux';
import { RootState } from '../../redux/store';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import {
  useGetApplicantProfileQuery,
  useAddApplicantNoteMutation,
  useRecordApplicationViewedMutation,
  useResumeApplicationMutation,
  useWithdrawHiredElsewhereMutation,
  useGetRecruitmentConfigQuery,
} from '../../redux/api/apiSlice';
import { getAssetUrl } from '../../services/api';
import {
  User,
  Mail,
  Phone,
  Briefcase,
  FileText,
  Calendar,
  Clock,
  Sparkles,
  Layers,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  Download,
  ExternalLink,
  MessageSquare,
  ShieldCheck,
  Send,
  Plus,
  Eye,
  Check,
  Building2,
  FileCheck,
  GraduationCap
} from 'lucide-react';
import {
  resolveCriterionStatus,
  getCriterionStatusBadgeStyle,
} from '../../utils/criterionStatus';
import MessageApplicantModal from '../../components/modals/hr/MessageApplicantModal';

interface ApplicantProfileProps {
  emailProp?: string;
  isModal?: boolean;
  onClose?: () => void;
}

const ApplicantProfile: React.FC<ApplicantProfileProps> = ({
  emailProp,
  isModal = false,
  onClose,
}) => {
  const navigate = useNavigate();
  const params = useParams();
  const rawEmailParam = params?.email;
  const emailParam = emailProp || (rawEmailParam ? decodeURIComponent(Array.isArray(rawEmailParam) ? rawEmailParam[0] : rawEmailParam) : '');

  const { role: userRole } = useSelector((state: RootState) => state.auth);
  const normRole = (userRole || '').toUpperCase();
  const isAuthorized = normRole === 'HR' || normRole === 'ADMIN';

  const [interviewMode, setInterviewMode] = useState<boolean>(false);
  const [newNoteContent, setNewNoteContent] = useState<string>('');
  const [noteSuccess, setNoteSuccess] = useState<boolean>(false);
  const [messageModalApp, setMessageModalApp] = useState<{
    id: number | string;
    jobTitle: string;
  } | null>(null);

  // Fetch applicant profile
  const { data: profile, isLoading, isError, refetch } = useGetApplicantProfileQuery(
    emailParam,
    { skip: !emailParam || !isAuthorized }
  );

  const [addNote, { isLoading: isAddingNote }] = useAddApplicantNoteMutation();
  const [recordViewed] = useRecordApplicationViewedMutation();
  const [resumeApp] = useResumeApplicationMutation();
  const [withdrawHiredElsewhere] = useWithdrawHiredElsewhereMutation();
  const { data: recruitmentConfig } = useGetRecruitmentConfigQuery(undefined, { skip: !isAuthorized });
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const secondsElapsedRef = React.useRef<number>(0);
  const hasEngagedRef = React.useRef<boolean>(false);
  const hasTriggeredViewedRef = React.useRef<boolean>(false);

  const primaryAppId = profile?.applications?.[0]?.id;

  // Track engagement on the profile page
  const handleUserEngagement = React.useCallback(() => {
    hasEngagedRef.current = true;
  }, []);

  // 8-second automatic status tracking: Submitted -> Under Review
  React.useEffect(() => {
    if (!primaryAppId) return;

    const interval = setInterval(() => {
      const isVisible = typeof document !== 'undefined' && document.visibilityState === 'visible';
      const isFocused = typeof document !== 'undefined' && (document.hasFocus ? document.hasFocus() : true);

      if (isVisible && isFocused) {
        secondsElapsedRef.current += 1;
        if (secondsElapsedRef.current >= 8 && hasEngagedRef.current && !hasTriggeredViewedRef.current) {
          hasTriggeredViewedRef.current = true;
          recordViewed({
            id: primaryAppId,
            view_duration_seconds: secondsElapsedRef.current,
            visible_focused: true,
            engaged: true,
          }).unwrap().then((res) => {
            if (process.env.NODE_ENV !== 'production') {
              console.log('[AutoStatus] profile viewed response:', res);
            }
            refetch();
          }).catch((err) => {
            if (process.env.NODE_ENV !== 'production') {
              console.warn('[AutoStatus] profile viewed error:', err);
            }
          });
        }
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [primaryAppId, recordViewed, refetch]);

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNoteContent.trim() || !emailParam) return;

    try {
      await addNote({ email: emailParam, content: newNoteContent.trim() }).unwrap();
      setNewNoteContent('');
      setNoteSuccess(true);
      setTimeout(() => setNoteSuccess(false), 2500);
      refetch();
    } catch (err) {
      console.error('Failed to add HR note:', err);
    }
  };

  if (!isAuthorized) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 text-center">
        <div className="bg-white p-8 rounded-2xl shadow-xl max-w-md border border-slate-200">
          <ShieldCheck size={40} className="text-rose-500 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-slate-900">Restricted Access</h2>
          <p className="text-xs text-slate-500 mt-2">
            This applicant profile is restricted to authorized HR personnel in accordance with the Data Privacy Act.
          </p>
          <button
            onClick={() => navigate('/hr/screening')}
            className="mt-6 px-4 py-2 bg-[#D60041] text-white text-xs font-bold rounded-xl"
          >
            Return to HR Screening
          </button>
        </div>
      </div>
    );
  }

  const candidate = profile?.candidate || profile?.contact_details || {};
  const applications = profile?.applications || [];
  const interviews = profile?.interviews || [];
  const callLogs = profile?.call_logs || [];
  const hrNotes = profile?.hr_notes || profile?.notes || [];
  const statusHistory = profile?.status_history || [];
  const summaryStrip = profile?.summary_strip || 'Candidate Profile';

  const content = isLoading ? (
    <div className="w-full max-w-6xl mx-auto py-16 flex flex-col items-center justify-center text-slate-500 space-y-3">
      <div className="w-8 h-8 border-2 border-slate-300 border-t-[#D60041] rounded-full animate-spin" />
      <p className="text-sm font-medium">Loading candidate profile...</p>
    </div>
  ) : isError || !profile ? (
    <div className="w-full max-w-6xl mx-auto py-12">
      <div className="bg-white rounded-2xl border border-rose-200 p-8 text-center max-w-lg mx-auto space-y-4 shadow-xs">
        <AlertTriangle size={36} className="text-rose-500 mx-auto" />
        <div className="space-y-1">
          <h2 className="text-lg font-bold text-slate-900">Unable to Load Candidate Profile</h2>
          <p className="text-xs text-slate-500">
            We couldn&apos;t retrieve the profile details for <span className="font-semibold text-slate-700">{emailParam}</span>.
          </p>
        </div>
        <div className="flex items-center justify-center gap-3 pt-2">
          {!isModal && (
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-bold rounded-xl cursor-pointer"
            >
              Go Back
            </button>
          )}
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 bg-[#D60041] hover:bg-[#b50037] text-white text-xs font-bold rounded-xl cursor-pointer"
          >
            Retry
          </button>
        </div>
      </div>
    </div>
  ) : (
    <div className="w-full max-w-6xl mx-auto space-y-6" onClick={handleUserEngagement} onScroll={handleUserEngagement}>
      {/* Top Navigation & Mode Switch */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {!isModal && (
            <button
              onClick={() => navigate(-1)}
              className="p-2 bg-white hover:bg-slate-100 rounded-xl border border-slate-200 text-slate-600 transition-colors cursor-pointer"
              aria-label="Go back"
            >
              <ArrowLeft size={16} />
            </button>
          )}
          <div>
            <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              <span>{candidate.name || emailParam}</span>
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                {candidate.source || 'Online Application'}
              </span>
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Comprehensive Candidate History • Privacy Act Compliant
            </p>
          </div>
        </div>

        {/* Interview Mode Toggle */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-white border border-slate-200 rounded-2xl p-1 shadow-xs">
            <button
              type="button"
              onClick={() => setInterviewMode(false)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${!interviewMode ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
            >
              Full Profile
            </button>
            <button
              type="button"
              onClick={() => setInterviewMode(true)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${interviewMode ? 'bg-[#D60041] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
            >
              <Sparkles size={12} />
              <span>Interview Mode</span>
            </button>
          </div>

          {candidate.resume_url && (
            <a
              href={getAssetUrl(candidate.resume_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-bold rounded-xl shadow-xs transition-colors"
            >
              <Download size={13} />
              <span>Resume</span>
            </a>
          )}
        </div>
      </div>

      {/* ─── TOP SUMMARY STRIP FOR INTERVIEWS ─── */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white px-5 py-3.5 rounded-2xl shadow-md flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center shrink-0">
            <Calendar size={16} className="text-pink-300" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Interview Brief</p>
            <p className="text-sm font-bold text-white truncate">{summaryStrip}</p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-300 flex-wrap">
          <span className="flex items-center gap-1.5" title="HR Contact Email">
            <Mail size={13} className="text-slate-400" />
            <span>{candidate.contact_email || candidate.email || emailParam}</span>
          </span>
          {candidate.account_email &&
            candidate.account_email.toLowerCase() !== (candidate.contact_email || candidate.email || '').toLowerCase() && (
              <span className="px-2 py-0.5 rounded-md bg-white/10 text-[11px] text-slate-200 border border-white/15">
                Account: {candidate.account_email}
              </span>
            )}
          {candidate.resume_email &&
            candidate.resume_email.toLowerCase() !== (candidate.contact_email || candidate.email || '').toLowerCase() && (
              <span className="px-2 py-0.5 rounded-md bg-white/10 text-[11px] text-slate-200 border border-white/15">
                Resume: {candidate.resume_email}
              </span>
            )}
          {candidate.phone && (
            <span className="flex items-center gap-1.5">
              <Phone size={13} className="text-slate-400" />
              <span>{candidate.phone}</span>
            </span>
          )}
        </div>
      </div>

      {/* Multi-Application & Repeat-Applicant Flags */}
      {(profile?.other_active_flag || profile?.previous_application_flag || actionFeedback) && (
        <div className="space-y-2.5">
          {profile?.other_active_flag && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-2xl px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <p className="text-xs font-bold text-indigo-900">{profile.other_active_flag}</p>
                {Array.isArray(profile.active_applications) && profile.active_applications.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {profile.active_applications.map((a: any) => (
                      <span
                        key={a.id}
                        className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-white border border-indigo-200 text-indigo-800"
                      >
                        <span>{a.job_title}</span>
                        <span className="text-indigo-400">•</span>
                        <span>{a.status}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {profile?.previous_application_flag && (
            <div className="bg-amber-50 border border-amber-200 rounded-2xl px-4 py-3 flex items-center gap-2.5">
              <AlertTriangle size={16} className="text-amber-600 shrink-0" />
              <p className="text-xs font-bold text-amber-900">
                {profile.previous_application_flag}
                <span className="font-normal text-amber-800 ml-1.5">
                  (Matched via salted one-way email hash — no personal data from prior records is exposed.)
                </span>
              </p>
            </div>
          )}

          {actionFeedback && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl px-4 py-2.5 text-xs font-semibold text-emerald-800">
              {actionFeedback}
            </div>
          )}
        </div>
      )}

      {/* ─── INTERVIEW MODE VIEW ─── */}
      {interviewMode ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in duration-200">
          {/* Position Strengths & Gaps for Interviewer */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <FileCheck size={16} className="text-[#D60041]" />
              <span>Applications & Qualifications Summary</span>
            </h2>

            {applications.map((app: any) => (
              <div key={app.id} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">{app.job_title}</h3>
                    <p className="text-xs text-slate-500">{app.department} • Applied {new Date(app.created_at).toLocaleDateString()}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {Math.round(app.match_score || 0)}% Match
                    </span>
                    {(() => {
                      const hasEdu = Boolean(app.education_status || app.education_reason || app.education_score !== null && app.education_score !== undefined);
                      if (!hasEdu) return null;
                      const eduSt = resolveCriterionStatus({
                        explicitStatus: app.education_status,
                        reason: app.education_reason,
                        score: app.education_score,
                      });
                      return (
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold rounded-full border ${getCriterionStatusBadgeStyle(eduSt).badgeClass}`}
                          title={app.education_reason || eduSt}
                        >
                          <GraduationCap size={11} />
                          <span>{eduSt}</span>
                        </span>
                      );
                    })()}
                    <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-slate-100 text-slate-700">
                      {app.status}
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        setMessageModalApp({ id: app.id, jobTitle: app.job_title || 'Position' })
                      }
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-bold rounded-full bg-rose-50 text-[#D60041] hover:bg-[#D60041] hover:text-white border border-rose-200 transition-colors cursor-pointer"
                    >
                      <MessageSquare size={12} />
                      <span>Message applicant</span>
                    </button>
                    {String(app.status || '').toLowerCase() === 'on hold' && (
                      <button
                        type="button"
                        onClick={async () => {
                          try {
                            await resumeApp({ applicationId: app.id }).unwrap();
                            setActionFeedback(`Resumed application for ${app.job_title}.`);
                            refetch();
                          } catch (err: any) {
                            setActionFeedback(err?.data?.detail || 'Could not resume application.');
                          }
                        }}
                        className="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-600 text-white hover:bg-emerald-700 cursor-pointer"
                      >
                        Resume
                      </button>
                    )}
                    {recruitmentConfig?.allow_hired_elsewhere_withdrawal &&
                      !['passed initial interview', 'not selected', 'withdrawn by applicant', 'withdrawn – hired elsewhere in company'].includes(
                        String(app.status || '').toLowerCase()
                      ) && (
                        <button
                          type="button"
                          onClick={async () => {
                            if (!window.confirm(`Mark "${app.job_title}" as "Withdrawn – hired elsewhere in company"?`)) return;
                            try {
                              await withdrawHiredElsewhere({ applicationId: app.id }).unwrap();
                              setActionFeedback(`Marked ${app.job_title} as Withdrawn – hired elsewhere in company.`);
                              refetch();
                            } catch (err: any) {
                              setActionFeedback(err?.data?.detail || 'Action failed.');
                            }
                          }}
                          className="px-2.5 py-1 text-xs font-bold rounded-full bg-slate-700 text-white hover:bg-slate-800 cursor-pointer"
                        >
                          Withdraw – Hired Elsewhere
                        </button>
                      )}
                  </div>
                </div>

                {/* Strengths & Missing Skills */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                  <div className="bg-emerald-50/60 rounded-xl p-3 border border-emerald-100">
                    <p className="text-xs font-bold text-emerald-800 flex items-center gap-1.5 mb-2">
                      <CheckCircle2 size={13} />
                      <span>Key Strengths & Qualifications</span>
                    </p>
                    {Array.isArray(app.strengths) && app.strengths.length > 0 ? (
                      <ul className="text-xs text-emerald-950 space-y-1 list-disc pl-4">
                        {app.strengths.slice(0, 4).map((s: string, idx: number) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-emerald-700 italic">No specific strengths recorded.</p>
                    )}
                  </div>

                  <div className="bg-amber-50/60 rounded-xl p-3 border border-amber-100">
                    <p className="text-xs font-bold text-amber-800 flex items-center gap-1.5 mb-2">
                      <AlertTriangle size={13} />
                      <span>Questions / Areas to Probe</span>
                    </p>
                    {Array.isArray(app.weaknesses) && app.weaknesses.length > 0 ? (
                      <ul className="text-xs text-amber-950 space-y-1 list-disc pl-4">
                        {app.weaknesses.slice(0, 4).map((w: string, idx: number) => (
                          <li key={idx}>{w}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-amber-700 italic">No gaps flagged.</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Quick Note Taking Box */}
          <div className="space-y-4">
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <MessageSquare size={16} className="text-[#D60041]" />
              <span>Live Interview Notes</span>
            </h2>

            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3">
              <form onSubmit={handleAddNote} className="space-y-3">
                <textarea
                  value={newNoteContent}
                  onChange={(e) => setNewNoteContent(e.target.value)}
                  placeholder="Record observations, responses to technical questions, cultural fit notes..."
                  rows={6}
                  className="w-full text-xs sm:text-sm p-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-[#D60041] focus:ring-2 focus:ring-[#D60041]/10 outline-none resize-none"
                />
                <button
                  type="submit"
                  disabled={isAddingNote || !newNoteContent.trim()}
                  className="w-full py-2 px-4 bg-[#D60041] hover:bg-[#b50037] text-white text-xs font-bold rounded-xl shadow-xs transition-colors flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
                >
                  <Send size={13} />
                  <span>{isAddingNote ? 'Saving...' : 'Save Interview Note'}</span>
                </button>
              </form>

              {noteSuccess && (
                <p className="text-xs font-semibold text-emerald-600 text-center">Note saved successfully!</p>
              )}

              {/* Past notes */}
              <div className="pt-3 border-t border-slate-100 space-y-2 max-h-64 overflow-y-auto">
                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Previous Notes ({hrNotes.length})</p>
                {hrNotes.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No notes recorded yet.</p>
                ) : (
                  hrNotes.map((note: any) => (
                    <div key={note.id} className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs space-y-1">
                      <p className="text-slate-800 whitespace-pre-wrap">{note.content}</p>
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span>{note.author_email}</span>
                        <span>{new Date(note.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ─── FULL PROFILE VIEW ─── */
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Section 1: All Applications by this Person */}
          <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900">Application History ({applications.length})</h2>
                <p className="text-xs text-slate-500">Every position this candidate has applied to at Mariwasa.</p>
              </div>
            </div>

            {applications.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-4">No active applications on record.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 text-slate-400 uppercase font-semibold">
                      <th className="pb-3">Position</th>
                      <th className="pb-3">Department</th>
                      <th className="pb-3">Applied Date</th>
                      <th className="pb-3">Match Score</th>
                      <th className="pb-3">Education</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3">Shortlists</th>
                      <th className="pb-3 text-right">Message</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {applications.map((app: any) => (
                      <tr key={app.id} className="hover:bg-slate-50/60">
                        <td className="py-3 font-bold text-slate-900">{app.job_title}</td>
                        <td className="py-3 text-slate-600">{app.department}</td>
                        <td className="py-3 text-slate-500">
                          {app.created_at || app.applied_date
                            ? new Date(app.created_at || app.applied_date).toLocaleDateString()
                            : '-'}
                        </td>
                        <td className="py-3">
                          <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                            {app.match_score !== null && app.match_score !== undefined ? `${Math.round(app.match_score)}%` : '-'}
                          </span>
                        </td>
                        <td className="py-3">
                          {(() => {
                            const hasEdu = Boolean(app.education_status || app.education_reason || app.education_score !== null && app.education_score !== undefined);
                            if (!hasEdu) return <span className="text-slate-400 italic">-</span>;
                            const eduSt = resolveCriterionStatus({
                              explicitStatus: app.education_status,
                              reason: app.education_reason,
                              score: app.education_score,
                            });
                            return (
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-bold ${getCriterionStatusBadgeStyle(eduSt).badgeClass}`}
                                title={app.education_reason || eduSt}
                              >
                                {eduSt}
                              </span>
                            );
                          })()}
                        </td>
                        <td className="py-3">
                          <span className="font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-full">
                            {app.status}
                          </span>
                        </td>
                        <td className="py-3 text-slate-500">
                          {Array.isArray(app.shortlist_rosters) && app.shortlist_rosters.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {app.shortlist_rosters.map((r: any, idx: number) => (
                                <span key={idx} className="px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 text-[10px] font-bold">
                                  {r.name || r}
                                </span>
                              ))}
                            </div>
                          ) : Array.isArray(app.shortlists) && app.shortlists.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {app.shortlists.map((s: string, idx: number) => (
                                <span key={idx} className="px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 text-[10px] font-bold">
                                  {s}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">None</span>
                          )}
                        </td>
                        <td className="py-3 text-right">
                          <button
                            type="button"
                            onClick={() =>
                              setMessageModalApp({ id: app.id, jobTitle: app.job_title || 'Position' })
                            }
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-[#D60041] text-[#D60041] hover:text-white border border-rose-200 text-[11px] font-bold transition-colors cursor-pointer"
                          >
                            <MessageSquare size={12} />
                            <span>Message applicant</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Section 1.5: Consolidated Application Status History & Audit Log */}
          <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Clock size={16} className="text-[#D60041]" />
                  <span>Status History & Audit Trail ({statusHistory.length})</span>
                </h2>
                <p className="text-xs text-slate-500">
                  Real-time record of all status transitions (viewed, shortlisted, interview scheduled, outcomes).
                </p>
              </div>
            </div>

            {statusHistory.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-3">No status changes recorded yet.</p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {statusHistory.map((h: any, idx: number) => (
                  <div
                    key={h.id || idx}
                    className="p-3 bg-slate-50/80 rounded-xl border border-slate-200/80 text-xs flex flex-wrap items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="w-2 h-2 rounded-full bg-[#D60041]" />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-slate-900">{h.job_title || 'Position'}</span>
                          <span className="text-slate-400">·</span>
                          <span className="text-slate-500 line-through text-[11px]">{h.old_status || 'Initial'}</span>
                          <span className="text-slate-400">→</span>
                          <span className="font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md border border-purple-200 text-[11px]">
                            {h.new_status}
                          </span>
                        </div>
                        {h.reason && <p className="text-[11px] text-slate-500 mt-0.5 italic">{h.reason}</p>}
                      </div>
                    </div>
                    <div className="text-right text-[11px] text-slate-400 shrink-0">
                      <p>{h.created_at ? new Date(h.created_at).toLocaleString() : ''}</p>
                      <p className="text-[10px] uppercase font-semibold text-slate-500">{h.changed_by || 'auto'}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Section 2: Interview Schedules & Call History */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Interviews */}
            <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-3">
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Calendar size={15} className="text-[#D60041]" />
                <span>Interview Schedule ({interviews.length})</span>
              </h2>

              {interviews.length === 0 ? (
                <p className="text-xs text-slate-400 italic py-2">No interviews scheduled yet.</p>
              ) : (
                <div className="space-y-2 max-h-56 overflow-y-auto">
                  {interviews.map((iv: any) => (
                    <div key={iv.id} className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs space-y-1">
                      <div className="flex items-center justify-between font-bold text-slate-900">
                        <span>{iv.job_title || 'Initial Interview'}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-700">{iv.status}</span>
                      </div>
                      <p className="text-slate-500">
                        {iv.scheduled_date} • {iv.scheduled_time || 'Time TBD'}
                      </p>
                      {iv.location && <p className="text-slate-400 text-[11px]">{iv.location}</p>}
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* HR Private Notes */}
            <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-3">
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <MessageSquare size={15} className="text-[#D60041]" />
                <span>HR Private Notes ({hrNotes.length})</span>
              </h2>

              <form onSubmit={handleAddNote} className="space-y-2">
                <textarea
                  value={newNoteContent}
                  onChange={(e) => setNewNoteContent(e.target.value)}
                  placeholder="Add confidential interview or screening notes..."
                  rows={2}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-[#D60041] outline-none resize-none"
                />
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={isAddingNote || !newNoteContent.trim()}
                    className="py-1.5 px-3 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    {isAddingNote ? 'Saving...' : 'Add Note'}
                  </button>
                </div>
              </form>

              <div className="space-y-2 max-h-48 overflow-y-auto pt-2 border-t border-slate-100">
                {hrNotes.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No notes added.</p>
                ) : (
                  hrNotes.map((n: any) => (
                    <div key={n.id} className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                      <p className="text-slate-800 whitespace-pre-wrap">{n.content}</p>
                      <p className="text-[10px] text-slate-400 mt-1">
                        By {n.author_email} on {new Date(n.created_at).toLocaleString()}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        </div>
      )}
      {/* Message Applicant Modal (HR-initiated per-application thread) */}
      <MessageApplicantModal
        isOpen={Boolean(messageModalApp)}
        onClose={() => setMessageModalApp(null)}
        applicationId={messageModalApp?.id ?? null}
        candidateName={candidate.name || emailParam}
        jobTitle={messageModalApp?.jobTitle}
      />
    </div>
  );

  if (isModal) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
        <div className="bg-slate-50 rounded-3xl shadow-2xl border border-slate-200 max-w-6xl w-full p-6 max-h-[92vh] overflow-y-auto">
          <div className="flex justify-end mb-2">
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-200 transition-colors"
            >
              ✕
            </button>
          </div>
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#F8FAFC] min-h-screen text-slate-800 antialiased font-sans flex flex-col">
      <Helmet>
        <title>{candidate.name || 'Applicant Profile'} | Mariwasa Recruitment HR Portal</title>
      </Helmet>
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 min-w-0 p-4 sm:p-6 md:p-8">
          {content}
        </main>
      </div>
    </div>
  );
};

export default ApplicantProfile;
