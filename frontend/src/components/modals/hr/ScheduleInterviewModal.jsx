import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Check,
  Clock,
  ShieldCheck,
  AlertCircle,
  X,
  Users,
  Mail,
  FileText,
  RefreshCw,
  Lock
} from 'lucide-react';
import { 
  useGetAvailableSlotsMutation, 
  useScheduleInterviewMutation,
  useGetHRInterviewersQuery,
  useGetAllInterviewsQuery
} from '../../../redux/api/apiSlice';

const ScheduleInterviewModal = ({ isOpen, onClose, candidate }) => {
  const { data: interviewers = [] } = useGetHRInterviewersQuery();
  const { data: allInterviews = [] } = useGetAllInterviewsQuery();
  const [getSlots, { isLoading: isFetchingSlots }] = useGetAvailableSlotsMutation();
  const [scheduleInterview, { isLoading: isScheduling }] = useScheduleInterviewMutation();

  const [selectedInterviewerId, setSelectedInterviewerId] = useState(null);
  const [useCustomTime, setUseCustomTime] = useState(false);
  const [customStartTime, setCustomStartTime] = useState('09:00');
  const [customEndTime, setCustomEndTime] = useState('10:00');
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const toLocalDateString = (d) => {
    const dateObj = d || new Date();
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, '0');
    const day = String(dateObj.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  const isWeekday = (dateStr) => {
    if (!dateStr) return false;
    const parts = dateStr.split('-');
    if (parts.length !== 3) return false;
    const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    const day = d.getDay();
    return day !== 0 && day !== 6;
  };

  const [formData, setFormData] = useState({
    date: '',
    title: 'Initial Interview',
    description: '',
    selectedSlot: null
  });

  const [availableSlots, setAvailableSlots] = useState([]);
  const [hasAttemptedFetch, setHasAttemptedFetch] = useState(false);

  // Set default interviewer to currently logged-in HR
  useEffect(() => {
    if (isOpen && interviewers.length > 0) {
      const loggedInId = parseInt(localStorage.getItem('user_id'), 10);
      const match = interviewers.find((i) => i.id === loggedInId);
      setSelectedInterviewerId(match ? match.id : interviewers[0].id);
    }
  }, [isOpen, interviewers]);

  useEffect(() => {
    if (isOpen) {
      setErrorMsg('');
      setSuccessMsg('');
      setUseCustomTime(false);
      let defaultDate = toLocalDateString(new Date());
      if (!isWeekday(defaultDate)) {
        const parts = defaultDate.split('-');
        const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
        while (d.getDay() === 0 || d.getDay() === 6) {
          d.setDate(d.getDate() + 1);
        }
        defaultDate = toLocalDateString(d);
      }
      setFormData({
        date: defaultDate,
        title: candidate ? `Interview with ${candidate.name || candidate.candidate_name}` : 'Initial Interview',
        description: '',
        selectedSlot: null
      });
    }
  }, [isOpen, candidate]);

  const weekendWarning = Boolean(formData.date && !isWeekday(formData.date));
  const todayISO = toLocalDateString(new Date());

  useEffect(() => {
    if (!formData.date || !isWeekday(formData.date)) {
      return;
    }

    const timer = setTimeout(async () => {
      setHasAttemptedFetch(true);
      try {
        const dateStr = formData.date;
        const slots = await getSlots({
          start_date: `${dateStr}T08:00:00`,
          end_date:   `${dateStr}T17:00:00`,
          hr_id: selectedInterviewerId || undefined
        }).unwrap();
        
        setAvailableSlots(slots || []);
      } catch (error) {
        setAvailableSlots([]);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [formData.date, selectedInterviewerId, getSlots]);

  if (!isOpen || !candidate) return null;

  const candidateEmail = (candidate?.candidate_email || candidate?.email || '').toLowerCase().trim();
  const activeInterview = allInterviews.find((iv) => {
    if (iv.status === 'CANCELED') return false;
    if (candidate?.id && iv.job_application_id === candidate.id) return true;
    if (candidateEmail && iv.candidate_email && iv.candidate_email.toLowerCase().trim() === candidateEmail) return true;
    return false;
  });

  const activeStart = activeInterview?.start_time || activeInterview?.start || activeInterview?.start_datetime;
  const activeFormattedDate = activeStart ? new Date(activeStart).toLocaleString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true
  }) : 'a scheduled time';
  const activeInterviewerName = activeInterview?.interviewer_name || activeInterview?.interviewer?.fullname || 'another HR';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (activeInterview) {
      setErrorMsg(`This candidate already has an active interview scheduled with ${activeInterviewerName} on ${activeFormattedDate}. Only one active interview is permitted.`);
      return;
    }

    let finalStart = '';
    let finalEnd = '';

    if (useCustomTime) {
      if (!customStartTime || !customEndTime) {
        setErrorMsg('Please select start and end time.');
        return;
      }
      finalStart = `${formData.date}T${customStartTime}:00`;
      finalEnd = `${formData.date}T${customEndTime}:00`;
      if (new Date(finalStart) >= new Date(finalEnd)) {
        setErrorMsg('End time must be after start time.');
        return;
      }
    } else {
      if (!formData.selectedSlot) {
        setErrorMsg('Please select a time slot or use custom hours.');
        return;
      }
      finalStart = formData.selectedSlot.start_time;
      finalEnd = formData.selectedSlot.end_time;
    }

    try {
      await scheduleInterview({
        job_application_id: candidate.id,
        interviewer_id: selectedInterviewerId || undefined,
        title: formData.title,
        description: formData.description,
        start_time: finalStart,
        end_time: finalEnd
      }).unwrap();
      
      setSuccessMsg(`Interview scheduled successfully! Interview notification emailed to candidate.`);
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (error) {
      setErrorMsg(error?.data?.detail || 'Failed to schedule interview. Please check slot availability.');
    }
  };

  const formatTime = (isoString) => {
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm">
      <div className="bg-white w-full max-w-5xl max-h-[90vh] rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
        
        <div className="px-8 py-5 border-b border-gray-100 flex justify-between items-center bg-white sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[#d81159] animate-pulse"></div>
            <span className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">Schedule Interview</span>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-1 overflow-hidden flex-col md:flex-row">
          {/* Sidebar */}
          <div className="w-full md:w-80 bg-gray-50/50 border-r border-gray-100 p-8 overflow-y-auto flex flex-col">
            <div className="text-center mb-8">
              <div className="w-24 h-24 rounded-2xl overflow-hidden border-4 border-white shadow-sm mx-auto mb-4 bg-pink-50 flex items-center justify-center">
                {candidate.profileImage ? (
                  <img src={candidate.profileImage} alt={candidate.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-[#d81159] text-3xl font-bold bg-pink-100">
                    {candidate.name.charAt(0)}
                  </div>
                )}
              </div>
              <h2 className="text-xl font-bold text-gray-900">{candidate.name}</h2>
              <p className="text-sm text-gray-500 font-medium">{candidate.preferredJob}</p>
            </div>

            <div className="space-y-4 mb-8">
              <div className="p-4 rounded-2xl bg-white border border-gray-100 shadow-sm">
                <p className="text-[9px] font-bold text-gray-400 uppercase mb-1">Match Rating</p>
                <p className="text-2xl font-black text-emerald-500">{candidate.matchScore}% Match</p>
              </div>

              <div className={`p-4 rounded-2xl border transition-all ${isFetchingSlots ? 'bg-white border-gray-100' : (hasAttemptedFetch ? (availableSlots.length > 0 ? 'bg-white border-green-500/10' : 'bg-white border-red-500/10') : 'bg-white border-gray-100')}`}>
                {isFetchingSlots ? (
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 border-2 border-[#d81159] border-t-transparent rounded-full animate-spin" />
                    <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider">Syncing Calendars...</span>
                  </div>
                ) : (
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-xl ${hasAttemptedFetch ? (availableSlots.length > 0 ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-600') : 'bg-gray-100 text-gray-400'}`}>
                      {hasAttemptedFetch ? (availableSlots.length > 0 ? <ShieldCheck size={18} /> : <AlertCircle size={18} />) : <Calendar size={18} />}
                    </div>
                    <div>
                      <p className={`text-[10px] font-black uppercase tracking-wider ${hasAttemptedFetch ? (availableSlots.length > 0 ? 'text-green-600' : 'text-red-600') : 'text-gray-500'}`}>
                        {hasAttemptedFetch ? (availableSlots.length > 0 ? 'Conflict-Free Slots Found' : 'No Slots Available') : 'Select Date'}
                      </p>
                      <p className="text-[10px] text-gray-400 font-medium leading-relaxed mt-0.5">
                        {hasAttemptedFetch ? (availableSlots.length > 0 ? 'HR schedule verified.' : 'No availability found.') : 'Awaiting input to check availability.'}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div className="mt-auto">
                <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest pt-4 border-t border-gray-100/50 flex items-center gap-2">
                    <Mail size={14} className="text-[#d81159]" />
                    Email Notification Enabled
                </div>
            </div>
          </div>

          {/* Main content area */}
          <div className="flex-grow p-8 overflow-y-auto bg-white flex flex-col">
            <div className="space-y-8 flex-1">

              {errorMsg && (
                <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-2xl flex items-center gap-3 text-xs font-semibold">
                  <AlertCircle size={18} className="shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {activeInterview && (
                <div className="bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3.5 rounded-2xl flex items-start gap-3 text-xs font-semibold shadow-sm">
                  <Lock size={18} className="shrink-0 text-amber-600 mt-0.5" />
                  <div>
                    <p className="font-bold text-amber-900">Duplicate Scheduling Blocked</p>
                    <p className="mt-0.5 text-amber-800 leading-relaxed">
                      This candidate already has an active interview scheduled with <span className="font-bold text-amber-950">{activeInterviewerName}</span> on <span className="font-bold text-amber-950">{activeFormattedDate}</span>. Only one active interview is permitted.
                    </p>
                  </div>
                </div>
              )}

              {successMsg && (
                <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-2xl flex items-center gap-3 text-xs font-semibold">
                  <Check size={18} className="shrink-0" />
                  <span>{successMsg}</span>
                </div>
              )}
              
              {/* HR Interviewer / Panelist */}
              <div>
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-3 flex items-center gap-2">
                  <Users size={16} className="text-[#d81159]" /> Assigned HR Interviewer
                </h3>
                <select
                  value={selectedInterviewerId || ''}
                  onChange={(e) => setSelectedInterviewerId(e.target.value ? parseInt(e.target.value, 10) : null)}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-100 rounded-xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#d81159]/20 focus:border-[#d81159] transition-all"
                >
                  {interviewers.map((hr) => (
                    <option key={hr.id} value={hr.id}>
                      {hr.fullname} ({hr.position || 'HR Specialist'}) {hr.has_google_calendar ? '• Google Calendar Linked' : ''}
                    </option>
                  ))}
                </select>
              </div>

              {/* Event Details */}
              <div>
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
                  <FileText size={16} className="text-[#d81159]" /> Interview Details
                </h3>
                <div className="grid grid-cols-1 gap-4">
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Event Title</label>
                    <input
                      required
                      type="text"
                      value={formData.title}
                      className="w-full px-4 py-3 bg-gray-50 border border-gray-100 rounded-xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#d81159]/20 focus:border-[#d81159] transition-all"
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Description / Notes</label>
                    <textarea
                      className="w-full px-4 py-3 bg-gray-50 border border-gray-100 rounded-xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#d81159]/20 focus:border-[#d81159] transition-all resize-none min-h-[80px]"
                      placeholder="Interview agenda, technical questions to ask..."
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    />
                  </div>
                </div>
              </div>


              {/* Date & Time Availability */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight flex items-center gap-2">
                    <Clock size={16} className="text-[#d81159]" /> Schedule Date & Time
                  </h3>

                  <div className="flex items-center gap-1 bg-gray-100 p-0.5 rounded-xl text-[11px] font-bold">
                    <button
                      type="button"
                      onClick={() => setUseCustomTime(false)}
                      className={`px-2.5 py-1 rounded-lg transition-all ${
                        !useCustomTime
                          ? 'bg-white text-[#d81159] shadow-sm font-black'
                          : 'text-gray-500 hover:text-gray-900'
                      }`}
                    >
                      Slots ({availableSlots.length})
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setUseCustomTime(true);
                        setFormData({ ...formData, selectedSlot: null });
                      }}
                      className={`px-2.5 py-1 rounded-lg transition-all ${
                        useCustomTime
                          ? 'bg-white text-[#d81159] shadow-sm font-black'
                          : 'text-gray-500 hover:text-gray-900'
                      }`}
                    >
                      Custom Hours
                    </button>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="space-y-2 max-w-[250px]">
                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Interview Date</label>
                    <input
                      required
                      type="date"
                      min={todayISO}
                      className="w-full px-4 py-3 bg-gray-50 border border-gray-100 rounded-xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#d81159]/20 focus:border-[#d81159] transition-all"
                      value={formData.date}
                      onChange={(e) => {
                        setFormData({ ...formData, date: e.target.value, selectedSlot: null });
                        setAvailableSlots([]);
                        setHasAttemptedFetch(false);
                      }}
                    />
                    <p className="text-[9px] text-gray-400 font-medium flex items-center gap-1 mt-1">
                      <Clock size={10} /> Mon – Fri only &nbsp;•&nbsp; 8:00 AM – 5:00 PM
                    </p>
                  </div>

                  {/* Weekend warning */}
                  {weekendWarning && (
                    <div className="py-3 px-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2">
                      <AlertCircle size={16} className="text-amber-500 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-xs font-bold text-amber-700">Weekends Not Available</p>
                        <p className="text-[10px] text-amber-600 mt-0.5">Interviews can only be scheduled Monday through Friday. Please select a weekday.</p>
                      </div>
                    </div>
                  )}

                  {formData.date && !weekendWarning && (
                    !useCustomTime ? (
                      <div className="pt-2">
                          <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-2">Available Slots (8:00 AM – 5:00 PM)</label>
                          {isFetchingSlots ? (
                              <div className="py-4 text-sm text-gray-500 animate-pulse">Checking mutual availability with Google Calendar...</div>
                          ) : availableSlots.length > 0 ? (
                              <div className="flex flex-wrap gap-3">
                                  {availableSlots.map((slot, idx) => (
                                      <button
                                          key={idx}
                                          type="button"
                                          onClick={() => setFormData({ ...formData, selectedSlot: slot })}
                                          className={`flex flex-col items-center justify-center py-2 px-4 rounded-xl border transition-all ${
                                              formData.selectedSlot === slot
                                                  ? 'bg-[#d81159] text-white border-[#d81159] shadow-md shadow-pink-100'
                                                  : 'bg-white text-gray-600 border-gray-200 hover:border-[#d81159]/50 hover:bg-pink-50/30'
                                          }`}
                                      >
                                          <span className="text-sm font-bold">{formatTime(slot.start_time)}</span>
                                          <span className="text-[10px] opacity-80">to {formatTime(slot.end_time)}</span>
                                      </button>
                                  ))}
                              </div>
                          ) : (
                              <div className="py-4 px-5 bg-red-50 border border-red-100 rounded-xl space-y-2">
                                  <p className="text-xs font-bold text-red-600">No standard 1-hour slots found for this date.</p>
                                  <button
                                    type="button"
                                    onClick={() => setUseCustomTime(true)}
                                    className="text-xs text-[#d81159] font-bold underline"
                                  >
                                    Switch to Custom Hours
                                  </button>
                              </div>
                          )}
                      </div>
                    ) : (
                      <div className="pt-2 space-y-3">
                        <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">Custom Interview Hours (8:00 AM – 5:00 PM)</label>
                        <div className="grid grid-cols-2 gap-3 max-w-sm">
                          <div>
                            <label className="text-[10px] text-gray-500 font-semibold block mb-1">Start Time</label>
                            <input
                              type="time"
                              min="08:00"
                              max="16:30"
                              value={customStartTime}
                              onChange={(e) => setCustomStartTime(e.target.value)}
                              className="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-xl text-xs font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#d81159]/20"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] text-gray-500 font-semibold block mb-1">End Time</label>
                            <input
                              type="time"
                              min="08:30"
                              max="17:00"
                              value={customEndTime}
                              onChange={(e) => setCustomEndTime(e.target.value)}
                              className="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-xl text-xs font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#d81159]/20"
                            />
                          </div>
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>

            </div>

            {/* Form Footer */}
            <div className="flex justify-end gap-3 mt-8 pt-6 border-t border-gray-100 bg-white">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 bg-gray-50 text-gray-500 rounded-xl text-xs font-bold uppercase tracking-wider hover:bg-gray-100 transition-all"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isScheduling || Boolean(activeInterview) || (!useCustomTime && !formData.selectedSlot) || (useCustomTime && (!customStartTime || !customEndTime))}
                className="px-6 py-2.5 bg-[#d81159] text-white rounded-xl text-xs font-bold uppercase tracking-wider hover:shadow-lg hover:shadow-pink-200 transition-all disabled:opacity-50 flex items-center gap-2"
              >
                {isScheduling ? 'Scheduling...' : 'Confirm & Schedule'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ScheduleInterviewModal;