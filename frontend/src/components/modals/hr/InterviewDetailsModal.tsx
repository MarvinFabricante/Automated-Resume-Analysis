import InterviewVenueFields, { emptyInterviewVenue, validInterviewVenue, venuePayload } from './InterviewVenueFields';
import { useGetInterviewDefaultsQuery } from '../../../redux/api/apiSlice';
import React, { useState, useEffect } from 'react';
import {
  X,
  Calendar,
  Clock,
  User,
  Mail,
  Phone,
  Briefcase,
  AlertCircle,
  CheckCircle2,
  Edit3,
  RefreshCw,
  Lock,
  MessageSquare,
  Check,
  MapPin,
  Video
} from 'lucide-react';
import { useSelector } from 'react-redux';
import { RootState } from '../../../redux/store';
import {
  useUpdateInterviewMutation,
  useCancelInterviewMutation,
  useGetAvailableSlotsMutation,
  useGetHRInterviewersQuery,
  useGetApplicationByIdQuery,
} from '../../../redux/api/apiSlice';
import { formatUtcLogTimestamp, extractMessageLogs } from '../../../utils/interviewUtils';
import CustomMessagePreviewSection, { CustomMessageValues } from '../../notifications/CustomMessagePreviewSection';
import MessageApplicantModal from './MessageApplicantModal';
import RequirementEvidence from '../../common/RequirementEvidence';

interface InterviewDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  interview: any;
  onStatusChanged?: () => void;
}

interface FormDataState {
  title: string;
  description: string;
  date: string;
  startTime: string;
  endTime: string;
  status: string;
  interviewerId: number | null;
  location: string;
  meetingLink: string;
}

const InterviewDetailsModal: React.FC<InterviewDetailsModalProps> = ({ isOpen, onClose, interview, onStatusChanged }) => {
  const reduxUserRole = useSelector((state: RootState) => state.auth?.role);
  const { data: interviewDefaults } = useGetInterviewDefaultsQuery();
  const [venue, setVenue] = useState({ ...emptyInterviewVenue });
  const [updateInterview, { isLoading: isUpdating }] = useUpdateInterviewMutation();
  const [cancelInterview, { isLoading: isCanceling }] = useCancelInterviewMutation();
  const [getSlots, { isLoading: isFetchingSlots }] = useGetAvailableSlotsMutation();
  const { data: interviewers = [] } = useGetHRInterviewersQuery();
  const linkedApplicationId = interview?.job_application_id || interview?.application_id;
  const { data: applicationDetails } = useGetApplicationByIdQuery(linkedApplicationId, {
    skip: !isOpen || !interview || Boolean(interview.isGoogleEvent) || !linkedApplicationId,
  });

  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [isCancelConfirmOpen, setIsCancelConfirmOpen] = useState<boolean>(false);
  const [cancelReason, setCancelReason] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [showMessageModal, setShowMessageModal] = useState<boolean>(false);
  const [customMsg, setCustomMsg] = useState<CustomMessageValues>({
    customEmailSubject: '',
    customEmailMessage: '',
    customSmsMessage: '',
    isCustomized: false,
  });

  const handleCustomMsgChange = React.useCallback((vals: CustomMessageValues) => {
    setCustomMsg(vals);
  }, []);

  const [formData, setFormData] = useState<FormDataState>({
    title: '',
    description: '',
    date: '',
    startTime: '',
    endTime: '',
    status: 'SCHEDULED',
    interviewerId: null,
    location: '',
    meetingLink: '',
  });

  const [availableSlots, setAvailableSlots] = useState<any[]>([]);

  const actualInterviewId = interview?.rawId || (typeof interview?.id === 'string' && interview.id.startsWith('iv-') ? parseInt(interview.id.replace('iv-', ''), 10) : interview?.id);

  const toLocalDateString = (d?: Date | null) => {
    if (!d) return '';
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  useEffect(() => {
    if (interview) {
      setIsEditing(false);
      setIsCancelConfirmOpen(false);
      setCancelReason('');
      setErrorMsg('');
      setCustomMsg({
        customEmailSubject: '',
        customEmailMessage: '',
        customSmsMessage: '',
        isCustomized: false,
      });

      const rawStart = interview.start_time || interview.start || interview.start_datetime;
      const rawEnd = interview.end_time || interview.end || interview.end_datetime;
      const start = rawStart ? new Date(rawStart) : null;
      const end = rawEnd ? new Date(rawEnd) : null;

      const dateStr = start ? toLocalDateString(start) : '';
      const startStr = start ? `${String(start.getHours()).padStart(2, '0')}:${String(start.getMinutes()).padStart(2, '0')}` : '09:00';
      const endStr = end ? `${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}` : '10:00';

      setVenue({
        interviewType: ['Onsite', 'Online'].includes(interview.interview_type) ? interview.interview_type : '',
        location: interview.location || '', meetingLink: interview.meeting_link || '',
        instructions: interview.instructions || '', platform: interview.platform || '',
      });
      setFormData({
        title: interview.title || '',
        description: interview.description || '',
        date: dateStr,
        startTime: startStr,
        endTime: endStr,
        status: interview.status || 'SCHEDULED',
        interviewerId: interview.interviewer_id || null,
        location: interview.location || '',
        meetingLink: interview.meeting_link || '',
      });
    }
  }, [interview, isOpen]);

  const isWeekday = (dateStr?: string) => {
    if (!dateStr) return false;
    const d = new Date(dateStr + 'T00:00:00');
    const day = d.getDay();
    return day !== 0 && day !== 6;
  };

  useEffect(() => {
    if (isEditing && formData.date && isWeekday(formData.date)) {
      const timer = setTimeout(async () => {
        try {
          const res = await getSlots({
            start_date: `${formData.date}T09:00:00`,
            end_date: `${formData.date}T17:00:00`,
            hr_id: formData.interviewerId || undefined
          }).unwrap();
          setAvailableSlots(Array.isArray(res) ? (res || []) : (res?.slots || []));
        } catch {
          setAvailableSlots([]);
        }
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [formData.date, formData.interviewerId, isEditing, getSlots]);

  if (!isOpen || !interview) return null;

  const rawUserId = localStorage.getItem('user_id');
  const loggedInUserId = rawUserId ? parseInt(rawUserId, 10) : null;
  const userRole = reduxUserRole || localStorage.getItem('role');
  const isOwner = !interview.interviewer_id || interview.interviewer_id === loggedInUserId;
  const isAdmin = userRole === 'ADMIN' || userRole === 'SUPERADMIN';
  const canModify = !interview.isGoogleEvent && (isOwner || isAdmin);
  const isGoogleOnlyEvent = interview.isGoogleEvent;

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validInterviewVenue(venue)) {
      setErrorMsg('Choose an interview type and complete the required location or meeting link.');
      return;
    }

    if (!canModify) return;
    setErrorMsg('');

    if (!isWeekday(formData.date)) {
      setErrorMsg('Interviews can only be scheduled on weekdays (Monday – Friday).');
      return;
    }

    const startHour = parseInt(formData.startTime.split(':')[0], 10);
    const startMin = parseInt(formData.startTime.split(':')[1], 10) || 0;
    const endHour = parseInt(formData.endTime.split(':')[0], 10);
    const endMin = parseInt(formData.endTime.split(':')[1], 10) || 0;

    const todayStr = toLocalDateString(new Date());
    if (formData.date < todayStr) {
      setErrorMsg('Cannot reschedule interview to a past date. This date is unavailable.');
      return;
    }

    if (startHour < 9 || endHour > 17 || (endHour === 17 && endMin > 0)) {
      setErrorMsg('Interviews must fall within working hours (9:00 AM – 5:00 PM).');
      return;
    }

    const startMinutes = startHour * 60 + startMin;
    const endMinutes = endHour * 60 + endMin;
    // Lunch break: 12:00 PM (720 min) to 1:00 PM (780 min)
    if (startMinutes < 780 && endMinutes > 720) {
      setErrorMsg('Interviews cannot be scheduled during lunch break (12:00 PM – 1:00 PM).');
      return;
    }

    const startDateTime = `${formData.date}T${formData.startTime}:00`;
    const endDateTime = `${formData.date}T${formData.endTime}:00`;

    if (new Date(startDateTime) >= new Date(endDateTime)) {
      setErrorMsg('End time must be after start time.');
      return;
    }

    try {
      await updateInterview({
        interviewId: actualInterviewId,
        title: formData.title,
        description: formData.description,
        start_time: startDateTime,
        end_time: endDateTime,
        status: formData.status,
        interviewer_id: formData.interviewerId || undefined,
        ...venuePayload(venue),
        ...(customMsg.isCustomized
          ? {
              custom_email_subject: customMsg.customEmailSubject || undefined,
              custom_email_message: customMsg.customEmailMessage || undefined,
              custom_sms_message: customMsg.customSmsMessage || undefined,
            }
          : {}),
      }).unwrap();

      setIsEditing(false);
      if (onStatusChanged) onStatusChanged();
    } catch (err: any) {
      setErrorMsg(err?.data?.detail || 'Failed to update interview. Please check slot availability.');
    }
  };

  const handleConfirmCancelSession = async () => {
    if (!canModify) return;
    setErrorMsg('');
    try {
      await cancelInterview({
        interviewId: actualInterviewId,
        reason: cancelReason.trim() || undefined,
        ...(customMsg.isCustomized
          ? {
              custom_email_subject: customMsg.customEmailSubject || undefined,
              custom_email_message: customMsg.customEmailMessage || undefined,
              custom_sms_message: customMsg.customSmsMessage || undefined,
            }
          : {}),
      }).unwrap();
      setIsCancelConfirmOpen(false);
      if (onStatusChanged) onStatusChanged();
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.data?.detail || 'Failed to cancel interview session.');
    }
  };

  const handleQuickStatusChange = async (newStatus: string) => {
    if (!canModify) return;
    try {
      await updateInterview({
        interviewId: actualInterviewId,
        status: newStatus
      }).unwrap();
      if (onStatusChanged) onStatusChanged();
    } catch (err: any) {
      alert(err?.data?.detail || 'Failed to update interview status.');
    }
  };


  const formatDateTime = (dateVal?: string | Date) => {
    if (!dateVal) return 'N/A';
    const d = new Date(dateVal);
    return d.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  const getStatusBadge = (status?: string) => {
    switch (status?.toUpperCase()) {
      case 'CONFIRMED':
        return <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase">Confirmed</span>;
      case 'RESCHEDULE_REQUESTED':
        return <span className="bg-amber-50 text-amber-700 border border-amber-200 px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase">Reschedule Requested</span>;
      case 'ESCALATED_TO_HR':
        return <span className="bg-blue-50 text-blue-700 border border-blue-200 px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase">Escalated to HR</span>;
      case 'COMPLETED':
        return <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase">Completed</span>;
      case 'CANCELED':
        return <span className="bg-rose-50 text-rose-700 border border-rose-200 px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase">Canceled</span>;
      case 'NO_SHOW':
        return <span className="bg-amber-50 text-amber-700 border border-amber-200 px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase">No Show</span>;
      default:
        return <span className="bg-pink-50 text-[#D60041] border border-pink-200 px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase">Scheduled</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-gray-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-2xl max-h-[96vh] sm:max-h-[90vh] rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-4 sm:px-8 py-3.5 sm:py-5 border-b border-gray-100 flex justify-between items-center bg-white sticky top-0 z-10 shrink-0">
          <div className="flex items-center gap-2.5 sm:gap-3">
            <div className={`h-2.5 w-2.5 rounded-full ${isGoogleOnlyEvent ? 'bg-blue-500' : 'bg-[#D60041]'} animate-pulse shrink-0`} />
            <span className="text-[11px] sm:text-xs font-black text-gray-500 uppercase tracking-wider truncate">
              {isGoogleOnlyEvent ? 'Google Calendar Event' : (isEditing ? 'Reschedule / Edit Interview' : 'Interview Session Details')}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 sm:p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400 hover:text-gray-700"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-8 overflow-y-auto flex-1 space-y-5 sm:space-y-6">
          {errorMsg && (
            <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-2xl flex items-center gap-3 text-xs font-semibold">
              <AlertCircle size={18} className="shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Read-Only Notice Banner for Other HR Users */}
          {!canModify && !isGoogleOnlyEvent && (
            <div className="bg-slate-50 border border-slate-200 text-slate-700 px-4 py-3.5 rounded-2xl flex items-center gap-3 text-xs font-semibold shadow-sm">
              <Lock size={18} className="text-slate-500 shrink-0" />
              <span>
                🔒 Assigned to <span className="font-bold text-slate-900">{interview.interviewer_name || interview.interviewer?.fullname || 'another HR'}</span>. Read-only view: you cannot edit, reschedule, or cancel this interview.
              </span>
            </div>
          )}

          {/* VIEW MODE */}
          {!isEditing || !canModify ? (
            <>
              {/* Event Title & Status */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-gray-100">
                <div>
                  <h3 className="text-2xl font-black text-gray-900 tracking-tight">
                    {interview.title || interview.summary || 'Interview Session'}
                  </h3>
                  <div className="flex items-center gap-2 mt-2">
                    <Calendar size={14} className="text-[#D60041]" />
                    <span className="text-sm font-semibold text-gray-600">
                      {formatDateTime(interview.start_time || interview.start || interview.start_datetime)}
                      {(interview.end_time || interview.end || interview.end_datetime) && (
                        <span>
                          {' '}–{' '}
                          {new Date(interview.end_time || interview.end || interview.end_datetime).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })}
                        </span>
                      )}
                    </span>
                  </div>
                </div>
                <div>
                  {isGoogleOnlyEvent ? (
                    <span className="bg-blue-50 text-blue-700 border border-blue-200 px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase">
                      Google Event
                    </span>
                  ) : (
                    getStatusBadge(interview.status)
                  )}
                </div>
              </div>

              {/* Candidate Card (For System Interviews) */}
              {!isGoogleOnlyEvent && (
                <div className="bg-gray-50/80 border border-gray-100 rounded-2xl p-5">
                  <p className="text-[10px] font-black uppercase text-gray-400 tracking-wider mb-3">
                    Candidate Profile
                  </p>
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-pink-100 text-[#D60041] flex items-center justify-center font-black text-lg shadow-sm">
                      {interview.candidate_name ? interview.candidate_name.charAt(0) : <User size={20} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-base font-black text-gray-900 truncate">
                        {interview.candidate_name || 'Assigned Candidate'}
                      </h4>
                      <p className="text-xs text-gray-500 font-semibold flex items-center gap-1.5 mt-0.5">
                        <Briefcase size={12} className="text-gray-400" />
                        {interview.job_title || 'Application Position'}
                      </p>
                    </div>
                    {(interview.job_application_id || interview.application_id) && (
                      <button
                        type="button"
                        onClick={() => setShowMessageModal(true)}
                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 hover:bg-[#D60041] text-white text-xs font-bold transition-colors cursor-pointer shrink-0"
                      >
                        <MessageSquare size={13} />
                        <span>Message applicant</span>
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4 pt-4 border-t border-gray-200/60">
                    <div className="flex items-center gap-2 text-xs text-gray-600 font-medium">
                      <Mail size={14} className="text-gray-400 shrink-0" />
                      <span className="truncate">{interview.candidate_email || 'No email provided'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-600 font-medium">
                      <Phone size={14} className="text-gray-400 shrink-0" />
                      <span>{interview.candidate_phone || 'No phone provided'}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Applicant Clarification Answers for Interview Reference */}
              {!isGoogleOnlyEvent && applicationDetails && (
                <RequirementEvidence
                  items={applicationDetails.requirement_evaluations}
                  clarificationResponses={applicationDetails.clarification_responses}
                  confirmedAt={applicationDetails.created_at || applicationDetails.date}
                  title="Applicant Clarification Answers (Interview Reference)"
                  interviewHint="Review these applicant-confirmed answers to ask follow-up questions during the interview."
                />
              )}

              {/* Assigned HR Interviewer / Panelist Card */}
              {!isGoogleOnlyEvent && (
                <div className="bg-rose-50/40 border border-rose-100 rounded-2xl p-5">
                  <p className="text-[10px] font-black uppercase text-rose-600 tracking-wider mb-3">
                    Assigned HR Interviewer / Panelist
                  </p>
                  <div className="flex items-center gap-4">
                    <div className="w-11 h-11 rounded-xl bg-rose-100 text-[#D60041] flex items-center justify-center font-black text-base shadow-sm">
                      {(interview.interviewer_name || interview.interviewer?.fullname || 'H').charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-bold text-gray-900 truncate">
                        {interview.interviewer_name || interview.interviewer?.fullname || 'Mariwasa Siam Ceramics HR'}
                      </h4>
                      <p className="text-xs text-gray-500 font-medium truncate mt-0.5">
                        {interview.interviewer_email || interview.interviewer?.email || 'HR Department'}
                      </p>
                    </div>
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-black bg-rose-100 text-[#D60041] uppercase tracking-wider">
                      HR Panelist
                    </span>
                  </div>
                </div>
              )}

              {/* Candidate Email Notification Box */}
              <div className="bg-rose-50/60 border border-rose-100 rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#D60041] text-white flex items-center justify-center shadow-md shadow-[#D60041]/20 shrink-0">
                    <Mail size={20} />
                  </div>
                  <div>
                    <p className="text-[10px] font-black uppercase text-[#D60041] tracking-wider">
                      Candidate Gmail Notification
                    </p>
                    <p className="text-xs font-semibold text-slate-800">
                      {interview.candidate_email
                        ? `Interview schedule details sent to ${interview.candidate_email}`
                        : 'Scheduled interview notification sent to candidate\'s registered email'}
                    </p>
                  </div>
                </div>
                <span className="px-3 py-1 bg-white border border-rose-200 text-[#D60041] rounded-xl text-[11px] font-bold shadow-sm self-start sm:self-auto">
                  Emailed via SMTP
                </span>
              </div>

              {/* SMS & Email Message Logs (IPROG SMS & Notification Delivery Status) */}
              {!isGoogleOnlyEvent && (
                <div className="bg-gradient-to-br from-white via-rose-50/30 to-pink-50/40 border border-rose-200/80 rounded-3xl p-5 sm:p-6 shadow-sm space-y-4">
                  {/* Card Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-rose-100">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-[#D60041] to-rose-500 text-white flex items-center justify-center shadow-md shadow-[#D60041]/20 shrink-0">
                        <MessageSquare size={20} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-black text-gray-900 tracking-tight">
                            SMS & Email Notification Logs
                          </h4>
                          <span className="px-2 py-0.5 bg-rose-100 text-[#D60041] rounded-full text-[10px] font-black uppercase tracking-wider">
                            IPROG SMS + Email
                          </span>
                        </div>
                        <p className="text-[11px] font-semibold text-gray-500">
                          Automated interview SMS & email delivery tracking
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Candidate Phone */}
                  <div className="bg-white/80 p-3 rounded-2xl border border-rose-100/70">
                    <span className="text-[10px] font-black text-gray-400 uppercase tracking-wider block">
                      Candidate Phone (SMS Recipient)
                    </span>
                    <span className="text-xs font-bold text-gray-900 flex items-center gap-1.5 mt-0.5">
                      <Phone size={13} className="text-[#D60041]" />
                      {interview.candidate_phone || 'No phone provided'}
                    </span>
                  </div>

                  {/* Message Logs (SMS & Notification Delivery Status) */}
                  {(() => {
                    const interviewMsgLogs = extractMessageLogs(
                      [interview],
                      [],
                      interview?.candidate_phone,
                      interview?.candidate_email
                    );
                    const queuedSmsCount = interviewMsgLogs.filter(
                      (m) => m.channel === 'SMS' && m.status !== 'FAILED'
                    ).length;
                    const failedSmsCount = interviewMsgLogs.filter(
                      (m) => m.channel === 'SMS' && m.status === 'FAILED'
                    ).length;
                    return (
                      <div className="pt-2 border-t border-rose-100/60">
                        <div className="flex items-center justify-between gap-2 flex-wrap text-xs font-bold text-gray-600 py-1">
                          <span className="flex items-center gap-1.5">
                            <MessageSquare size={14} className="text-emerald-600" />
                            Message Logs ({interviewMsgLogs.length})
                          </span>
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {queuedSmsCount > 0 && (
                              <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-emerald-100 text-emerald-800 border border-emerald-200 inline-flex items-center gap-1">
                                <Check size={10} />
                                <span>SMS Queued{queuedSmsCount > 1 ? ` (${queuedSmsCount})` : ''}</span>
                              </span>
                            )}
                            {failedSmsCount > 0 && (
                              <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-rose-100 text-rose-800 border border-rose-200 inline-flex items-center gap-1">
                                <AlertCircle size={10} />
                                <span>SMS Failed{failedSmsCount > 1 ? ` (${failedSmsCount})` : ''}</span>
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="mt-2 space-y-2 max-h-48 overflow-y-auto pr-1">
                          {interviewMsgLogs.length > 0 ? (
                            interviewMsgLogs.map((msg, idx) => {
                              const isFailed = msg.status === 'FAILED';
                              return (
                                <div
                                  key={msg.id || idx}
                                  className={`p-3 rounded-xl border flex flex-col sm:flex-row sm:items-start justify-between gap-2 text-xs ${
                                    isFailed
                                      ? 'bg-rose-50/60 border-rose-200'
                                      : 'bg-white/90 border-gray-100'
                                  }`}
                                >
                                  <div className="space-y-0.5 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                      <span className="font-black text-gray-900">{msg.label}</span>
                                      <span
                                        className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase border ${
                                          msg.channel === 'SMS'
                                            ? 'bg-indigo-100 text-indigo-800 border-indigo-200'
                                            : 'bg-sky-100 text-sky-800 border-sky-200'
                                        }`}
                                      >
                                        {msg.channel}
                                      </span>
                                      <span
                                        className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase border inline-flex items-center gap-1 ${
                                          isFailed
                                            ? 'bg-rose-100 text-rose-800 border-rose-200'
                                            : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                                        }`}
                                      >
                                        {isFailed ? <AlertCircle size={9} /> : <Check size={9} />}
                                        <span>{msg.status || (msg.channel === 'SMS' ? 'QUEUED' : 'DELIVERED')}</span>
                                      </span>
                                    </div>
                                    <p className="text-[11px] text-gray-500 font-medium">To {msg.recipient}</p>
                                    {msg.details && (
                                      <p className={`text-[11px] leading-relaxed ${isFailed ? 'text-rose-700 font-medium' : 'text-gray-600'}`}>
                                        {msg.details}
                                      </p>
                                    )}
                                  </div>
                                  <span className="text-[10px] text-gray-400 font-mono shrink-0">
                                    {formatUtcLogTimestamp(msg.created_at)}
                                  </span>
                                </div>
                              );
                            })
                          ) : (
                            <p className="text-xs text-gray-400 font-medium py-2 text-center">
                              No SMS or message logs recorded yet.
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* Description / Notes & Venue / Meeting Link */}
              <div className="text-sm text-gray-700 space-y-1">
                <p>Interview type: {interview.interview_type || 'Not specified'}</p>
                {interview.platform && <p>Platform: {interview.platform}</p>}
                {interview.instructions && <p>Instructions: {interview.instructions}</p>}
                {interview.interview_type === 'Online' && <p>Please join a few minutes early and test your camera and microphone.</p>}
              </div>
              {(interview.location || interview.meeting_link || interview.description || interview.notes) && (
                <div className="space-y-3">
                  {(interview.location || interview.meeting_link) && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {interview.location && (
                        <div className="bg-gray-50/80 border border-gray-100 rounded-2xl p-3.5">
                          <p className="text-[10px] font-black uppercase text-gray-400 tracking-wider mb-1 flex items-center gap-1">
                            <MapPin size={11} className="text-[#D60041]" /> Venue / Format
                          </p>
                          <p className="text-xs font-bold text-gray-800">{interview.location}</p>
                        </div>
                      )}
                      {interview.meeting_link && (
                        <div className="bg-gray-50/80 border border-gray-100 rounded-2xl p-3.5">
                          <p className="text-[10px] font-black uppercase text-gray-400 tracking-wider mb-1 flex items-center gap-1">
                            <Video size={11} className="text-[#D60041]" /> Meeting Link
                          </p>
                          <a
                            href={interview.meeting_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs font-bold text-[#D60041] hover:underline break-all"
                          >
                            {interview.meeting_link}
                          </a>
                        </div>
                      )}
                    </div>
                  )}

                  {(interview.description || interview.notes) && (
                    <div>
                      <p className="text-[10px] font-black uppercase text-gray-400 tracking-wider mb-2">
                        Agenda & Notes
                      </p>
                      <p className="text-xs text-gray-700 font-medium bg-gray-50/60 p-4 rounded-2xl border border-gray-100 leading-relaxed">
                        {interview.description || interview.notes}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Google Sync Status Indicator */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className={`w-2.5 h-2.5 rounded-full ${interview.google_event_id ? 'bg-emerald-500' : 'bg-gray-400'}`} />
                  <span className="font-semibold text-gray-700">
                    {interview.google_event_id ? 'Synchronized with Google Calendar' : 'Local System Schedule'}
                  </span>
                </div>
                {interview.google_event_id && (
                  <span className="text-[10px] font-mono text-gray-400 truncate max-w-[140px]">
                    ID: {interview.google_event_id}
                  </span>
                )}
              </div>

              {/* Action Buttons */}
              {!isGoogleOnlyEvent && canModify && (
                <div className="pt-4 border-t border-gray-100 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        onClick={() => setIsEditing(true)}
                        className="px-3.5 sm:px-4 py-2 sm:py-2.5 bg-gray-900 hover:bg-[#D60041] text-white rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 sm:gap-2 shadow-sm"
                      >
                        <Edit3 size={14} />
                        Reschedule / Edit
                      </button>

                      {interview.status !== 'COMPLETED' && (
                        <button
                          onClick={() => handleQuickStatusChange('COMPLETED')}
                          className="px-3.5 py-2.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
                        >
                          <CheckCircle2 size={14} />
                          Mark Completed
                        </button>
                      )}

                      {interview.status !== 'CANCELED' && !isCancelConfirmOpen && (
                        <button
                          onClick={() => {
                            setCustomMsg({
                              customEmailSubject: '',
                              customEmailMessage: '',
                              customSmsMessage: '',
                              isCustomized: false,
                            });
                            setIsCancelConfirmOpen(true);
                          }}
                          className="px-3.5 py-2.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
                        >
                          Cancel Session
                        </button>
                      )}
                    </div>
                  </div>

                  {isCancelConfirmOpen && (
                    <div className="p-4 bg-rose-50/60 border border-rose-200 rounded-2xl space-y-3">
                      <p className="text-xs font-black text-rose-900">
                        Cancel Interview & Notify Candidate
                      </p>
                      <div>
                        <label className="block text-[10px] font-bold uppercase text-rose-800 mb-1">
                          Cancellation Reason (Included in Email & SMS)
                        </label>
                        <input
                          type="text"
                          value={cancelReason}
                          onChange={(e) => setCancelReason(e.target.value)}
                          placeholder="e.g., Panelist unavailable; HR will reach out with new dates"
                          className="w-full px-3 py-2 bg-white border border-rose-200 rounded-xl text-xs font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-rose-500/20"
                        />
                      </div>
                      <CustomMessagePreviewSection
                        templateKey="interview_canceled"
                        candidateName={interview.candidate_name}
                        candidateEmail={interview.candidate_email}
                        jobTitle={interview.job_title}
                        interviewTitle={interview.title}
                        startTime={interview.start_time || interview.start}
                        endTime={interview.end_time || interview.end}
                        interviewerName={interview.interviewer_name}
                        interviewerEmail={interview.interviewer_email}
                        location={interview.location}
                        reason={cancelReason}
                        onChange={handleCustomMsgChange}
                      />
                      <div className="flex justify-end gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setIsCancelConfirmOpen(false)}
                          className="px-3.5 py-2 bg-white border border-gray-200 text-gray-700 rounded-xl text-xs font-bold hover:bg-gray-50"
                        >
                          Keep Schedule
                        </button>
                        <button
                          type="button"
                          disabled={isCanceling}
                          onClick={handleConfirmCancelSession}
                          className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold disabled:opacity-50"
                        >
                          {isCanceling ? 'Canceling & Notifying...' : 'Confirm Cancellation'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            /* RESCHEDULE / EDIT FORM */
            <form onSubmit={handleSaveEdit} className="space-y-5">
              <div>
                <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                  Interview Title
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                  Assigned HR Interviewer / Panelist
                </label>
                <select
                  value={formData.interviewerId || ''}
                  onChange={(e) => setFormData({ ...formData, interviewerId: e.target.value ? parseInt(e.target.value, 10) : null })}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                >
                  <option value="">Default (Current HR)</option>
                  {interviewers.map((hr: any) => (
                    <option key={hr.id} value={hr.id}>
                      {hr.fullname} ({hr.position || 'HR Specialist'}) {hr.has_google_calendar ? '• Google Calendar Linked' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                    Date (Mon - Fri)
                  </label>
                  <input
                    type="date"
                    min={toLocalDateString(new Date())}
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                    required
                  />
                  {formData.date && formData.date < toLocalDateString(new Date()) && (
                    <p className="text-[11px] text-rose-600 font-semibold mt-1 flex items-center gap-1">
                      <AlertCircle size={12} /> This date is unavailable because it is in the past.
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                    Start Time
                  </label>
                  <input
                    type="time"
                    value={formData.startTime}
                    onChange={(e) => setFormData({ ...formData, startTime: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                    End Time
                  </label>
                  <input
                    type="time"
                    value={formData.endTime}
                    onChange={(e) => setFormData({ ...formData, endTime: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                    required
                  />
                </div>
              </div>

              {/* Available Slots Helper */}
              {formData.date && isWeekday(formData.date) && (
                <div className="p-4 bg-gray-50/80 rounded-2xl border border-gray-200">
                  <p className="text-[10px] font-black uppercase text-gray-500 tracking-wider mb-2 flex items-center gap-1.5">
                    <Clock size={12} className="text-[#D60041]" />
                    Available Conflict-Free Slots for {formData.date}:
                  </p>
                  {isFetchingSlots ? (
                    <div className="flex items-center gap-2 text-xs text-gray-500 py-1">
                      <RefreshCw size={12} className="animate-spin text-[#D60041]" />
                      Checking schedule availability...
                    </div>
                  ) : availableSlots.length > 0 ? (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {availableSlots.slice(0, 8).map((slot, i) => {
                        const formatTimeToHHMM = (dtStr: string | Date) => {
                          const d = new Date(dtStr);
                          return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
                        };
                        const sTime = formatTimeToHHMM(slot.start_time);
                        const eTime = formatTimeToHHMM(slot.end_time);
                        return (
                          <button
                            type="button"
                            key={i}
                            onClick={() => setFormData({ ...formData, startTime: sTime, endTime: eTime })}
                            className="px-2.5 py-1 bg-white hover:bg-pink-50 hover:border-[#D60041] hover:text-[#D60041] border border-gray-200 rounded-lg text-xs font-bold text-gray-700 transition-colors"
                          >
                            {sTime} - {eTime}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-xs text-amber-600 font-medium">No system recommendations found for this date. Ensure hours are between 9:00 AM - 5:00 PM.</p>
                  )}
                </div>
              )}

              <div>
                <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                  Session Status
                </label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                >
                  <option value="SCHEDULED">SCHEDULED</option>
                  <option value="COMPLETED">COMPLETED</option>
                  <option value="CANCELED">CANCELED</option>
                  <option value="NO_SHOW">NO SHOW</option>
                </select>
              </div>

              <InterviewVenueFields value={venue} onChange={setVenue} companyAddress={interviewDefaults?.company_address} />

              <div>
                <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                  Description / Notes
                </label>
                <textarea
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Add interview agenda or notes for HR panel..."
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] resize-none"
                />
              </div>

              {(() => {
                const selectedHr = interviewers.find((i: any) => i.id === formData.interviewerId);
                return (
                  <CustomMessagePreviewSection
                    templateKey={formData.status === 'CANCELED' ? 'interview_canceled' : 'interview_rescheduled'}
                    candidateName={interview.candidate_name}
                    candidateEmail={interview.candidate_email}
                    jobTitle={interview.job_title}
                    interviewTitle={formData.title}
                    startTime={formData.date && formData.startTime ? `${formData.date}T${formData.startTime}:00` : undefined}
                    endTime={formData.date && formData.endTime ? `${formData.date}T${formData.endTime}:00` : undefined}
                    interviewerName={selectedHr?.fullname || interview.interviewer_name}
                    interviewerEmail={selectedHr?.email || interview.interviewer_email}
                    location={venue.interviewType === 'Onsite' ? venue.location : ''}
                    meetingLink={venue.interviewType === 'Online' ? venue.meetingLink : ''}
                    notes={formData.description}
                    reason={formData.status === 'CANCELED' ? formData.description : undefined}
                    onChange={handleCustomMsgChange}
                  />
                );
              })()}

              <div className="flex flex-wrap sm:flex-nowrap items-center justify-end gap-2.5 sm:gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="w-full sm:w-auto px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-xs font-bold transition-colors text-center"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUpdating || !validInterviewVenue(venue)}
                  className="w-full sm:w-auto px-6 py-2.5 bg-[#D60041] hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-[#D60041]/20 disabled:opacity-50 text-center"
                >
                  {isUpdating ? 'Saving to System & Google Calendar...' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      <MessageApplicantModal
        isOpen={showMessageModal}
        onClose={() => setShowMessageModal(false)}
        applicationId={interview.job_application_id || interview.application_id || null}
        candidateName={interview.candidate_name}
        jobTitle={interview.job_title}
      />
    </div>
  );
};

export default InterviewDetailsModal;
