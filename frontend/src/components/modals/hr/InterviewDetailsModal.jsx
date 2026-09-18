import React, { useState, useEffect } from 'react';
import {
  X,
  Calendar,
  Clock,
  Video,
  User,
  Mail,
  Phone,
  Briefcase,
  AlertCircle,
  CheckCircle2,
  Edit3,
  Trash2,
  ExternalLink,
  Copy,
  Check,
  RefreshCw
} from 'lucide-react';
import {
  useUpdateInterviewMutation,
  useDeleteInterviewMutation,
  useGetAvailableSlotsMutation,
  useGetHRInterviewersQuery
} from '../../../redux/api/apiSlice';

const InterviewDetailsModal = ({ isOpen, onClose, interview, onStatusChanged }) => {
  const [updateInterview, { isLoading: isUpdating }] = useUpdateInterviewMutation();
  const [deleteInterview, { isLoading: isDeleting }] = useDeleteInterviewMutation();
  const [getSlots, { isLoading: isFetchingSlots }] = useGetAvailableSlotsMutation();
  const { data: interviewers = [] } = useGetHRInterviewersQuery();

  const [isEditing, setIsEditing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    date: '',
    startTime: '',
    endTime: '',
    status: 'SCHEDULED',
    interviewerId: null
  });

  const [availableSlots, setAvailableSlots] = useState([]);

  const actualInterviewId = interview?.rawId || (typeof interview?.id === 'string' && interview.id.startsWith('iv-') ? parseInt(interview.id.replace('iv-', ''), 10) : interview?.id);

  const toLocalDateString = (d) => {
    if (!d) return '';
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  useEffect(() => {
    if (interview) {
      setIsEditing(false);
      setConfirmDelete(false);
      setErrorMsg('');

      const rawStart = interview.start_time || interview.start || interview.start_datetime;
      const rawEnd = interview.end_time || interview.end || interview.end_datetime;
      const start = rawStart ? new Date(rawStart) : null;
      const end = rawEnd ? new Date(rawEnd) : null;

      const dateStr = start ? toLocalDateString(start) : '';
      const startStr = start ? `${String(start.getHours()).padStart(2, '0')}:${String(start.getMinutes()).padStart(2, '0')}` : '09:00';
      const endStr = end ? `${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}` : '10:00';

      setFormData({
        title: interview.title || '',
        description: interview.description || '',
        date: dateStr,
        startTime: startStr,
        endTime: endStr,
        status: interview.status || 'SCHEDULED',
        interviewerId: interview.interviewer_id || null
      });
    }
  }, [interview, isOpen]);

  const isWeekday = (dateStr) => {
    if (!dateStr) return false;
    const d = new Date(dateStr + 'T00:00:00');
    const day = d.getDay();
    return day !== 0 && day !== 6;
  };

  useEffect(() => {
    if (isEditing && formData.date && isWeekday(formData.date)) {
      const timer = setTimeout(async () => {
        try {
          const slots = await getSlots({
            start_date: `${formData.date}T08:00:00`,
            end_date: `${formData.date}T17:00:00`,
            hr_id: formData.interviewerId || undefined
          }).unwrap();
          setAvailableSlots(slots || []);
        } catch {
          setAvailableSlots([]);
        }
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [formData.date, formData.interviewerId, isEditing, getSlots]);

  if (!isOpen || !interview) return null;

  const isGoogleOnlyEvent = interview.isGoogleEvent;

  const handleCopyLink = () => {
    if (interview.meeting_link || interview.meet_link) {
      navigator.clipboard.writeText(interview.meeting_link || interview.meet_link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!isWeekday(formData.date)) {
      setErrorMsg('Interviews can only be scheduled on weekdays (Monday – Friday).');
      return;
    }

    const startHour = parseInt(formData.startTime.split(':')[0], 10);
    const endHour = parseInt(formData.endTime.split(':')[0], 10);
    const endMin = parseInt(formData.endTime.split(':')[1], 10);

    if (startHour < 8 || endHour > 17 || (endHour === 17 && endMin > 0)) {
      setErrorMsg('Interviews must fall within working hours (8:00 AM – 5:00 PM).');
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
        interviewer_id: formData.interviewerId || undefined
      }).unwrap();

      setIsEditing(false);
      if (onStatusChanged) onStatusChanged();
    } catch (err) {
      setErrorMsg(err?.data?.detail || 'Failed to update interview. Please check slot availability.');
    }
  };

  const handleQuickStatusChange = async (newStatus) => {
    try {
      await updateInterview({
        interviewId: actualInterviewId,
        status: newStatus
      }).unwrap();
      if (onStatusChanged) onStatusChanged();
    } catch (err) {
      alert(err?.data?.detail || 'Failed to update interview status.');
    }
  };

  const handleDelete = async () => {
    try {
      await deleteInterview(actualInterviewId).unwrap();
      onClose();
      if (onStatusChanged) onStatusChanged();
    } catch (err) {
      alert(err?.data?.detail || 'Failed to delete interview.');
    }
  };

  const formatDateTime = (dateVal) => {
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

  const getStatusBadge = (status) => {
    switch (status?.toUpperCase()) {
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-2xl max-h-[90vh] rounded-3xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 sm:px-8 py-5 border-b border-gray-100 flex justify-between items-center bg-white sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className={`h-2.5 w-2.5 rounded-full ${isGoogleOnlyEvent ? 'bg-blue-500' : 'bg-[#D60041]'} animate-pulse`} />
            <span className="text-xs font-black text-gray-500 uppercase tracking-wider">
              {isGoogleOnlyEvent ? 'Google Calendar Event' : (isEditing ? 'Reschedule / Edit Interview' : 'Interview Session Details')}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400 hover:text-gray-700"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 sm:p-8 overflow-y-auto flex-1 space-y-6">
          {errorMsg && (
            <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-2xl flex items-center gap-3 text-xs font-semibold">
              <AlertCircle size={18} className="shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* VIEW MODE */}
          {!isEditing ? (
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

              {/* Meeting Link Box */}
              {(interview.meeting_link || interview.meet_link) && (
                <div className="bg-emerald-50/60 border border-emerald-100 rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500 text-white flex items-center justify-center shadow-md shadow-emerald-500/20">
                      <Video size={20} />
                    </div>
                    <div>
                      <p className="text-[10px] font-black uppercase text-emerald-800 tracking-wider">
                        Google Meet Link
                      </p>
                      <p className="text-xs font-semibold text-emerald-900 truncate max-w-xs sm:max-w-sm">
                        {interview.meeting_link || interview.meet_link}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <button
                      onClick={handleCopyLink}
                      className="flex-1 sm:flex-initial px-3 py-2 bg-white hover:bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-bold transition-colors flex items-center justify-center gap-1.5 shadow-sm"
                    >
                      {copied ? <Check size={14} /> : <Copy size={14} />}
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                    <a
                      href={interview.meeting_link || interview.meet_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 sm:flex-initial px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-emerald-600/20 flex items-center justify-center gap-1.5"
                    >
                      <ExternalLink size={14} />
                      Join Call
                    </a>
                  </div>
                </div>
              )}

              {/* Description / Notes */}
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
              {!isGoogleOnlyEvent && (
                <div className="pt-4 border-t border-gray-100 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setIsEditing(true)}
                        className="px-4 py-2.5 bg-gray-900 hover:bg-[#D60041] text-white rounded-xl text-xs font-bold transition-all flex items-center gap-2 shadow-sm"
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

                      {interview.status !== 'CANCELED' && (
                        <button
                          onClick={() => handleQuickStatusChange('CANCELED')}
                          className="px-3.5 py-2.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
                        >
                          Cancel Session
                        </button>
                      )}
                    </div>

                    {!confirmDelete ? (
                      <button
                        onClick={() => setConfirmDelete(true)}
                        className="px-3 py-2 text-gray-400 hover:text-rose-600 rounded-xl text-xs font-semibold transition-colors flex items-center gap-1"
                      >
                        <Trash2 size={14} />
                        Delete
                      </button>
                    ) : (
                      <div className="flex items-center gap-2 bg-rose-50 p-1.5 rounded-xl border border-rose-100">
                        <span className="text-[10px] text-rose-700 font-bold px-1">Confirm delete?</span>
                        <button
                          onClick={handleDelete}
                          disabled={isDeleting}
                          className="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold"
                        >
                          {isDeleting ? 'Deleting...' : 'Yes, Delete'}
                        </button>
                        <button
                          onClick={() => setConfirmDelete(false)}
                          className="px-2.5 py-1 bg-white hover:bg-gray-100 text-gray-700 rounded-lg text-xs font-semibold border border-gray-200"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
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
                  {interviewers.map((hr) => (
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
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                    required
                  />
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
                        const sTime = new Date(slot.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
                        const eTime = new Date(slot.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
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
                    <p className="text-xs text-amber-600 font-medium">No system recommendations found for this date. Ensure hours are between 8:00 AM - 5:00 PM.</p>
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

              <div>
                <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                  Description / Notes
                </label>
                <textarea
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Add meeting agenda or notes for HR panel..."
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-xs font-bold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUpdating}
                  className="px-6 py-2.5 bg-[#D60041] hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-[#D60041]/20 disabled:opacity-50"
                >
                  {isUpdating ? 'Saving to System & Google Calendar...' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default InterviewDetailsModal;
