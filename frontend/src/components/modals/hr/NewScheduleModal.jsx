import React, { useState, useEffect } from 'react';
import {
  X,
  Calendar,
  Clock,
  User,
  Search,
  Briefcase,
  AlertCircle,
  CheckCircle2,
  Check,
  Video,
  ShieldCheck,
  RefreshCw,
  Sparkles,
  Users,
  Lock
} from 'lucide-react';
import {
  useGetApplicationsQuery,
  useGetAllInterviewsQuery,
  useGetAvailableSlotsMutation,
  useGetHRInterviewersQuery,
  useScheduleInterviewMutation
} from '../../../redux/api/apiSlice';

const NewScheduleModal = ({ isOpen, onClose, initialDate, initialTime, initialInterviewerId, onScheduled }) => {
  const { data: candidates = [], isLoading: isCandidatesLoading } = useGetApplicationsQuery();
  const { data: allInterviews = [] } = useGetAllInterviewsQuery();
  const { data: interviewers = [] } = useGetHRInterviewersQuery();
  const [getSlots, { isLoading: isFetchingSlots }] = useGetAvailableSlotsMutation();
  const [scheduleInterview, { isLoading: isScheduling }] = useScheduleInterviewMutation();

  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [selectedInterviewerId, setSelectedInterviewerId] = useState(null);
  const [searchCandidate, setSearchCandidate] = useState('');
  const [date, setDate] = useState('');
  const [title, setTitle] = useState('Technical Interview');
  const [description, setDescription] = useState('');
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [errorMsg, setErrorMsg] = useState('');
  const [useCustomTime, setUseCustomTime] = useState(false);
  const [customStartTime, setCustomStartTime] = useState('09:00');
  const [customEndTime, setCustomEndTime] = useState('10:00');

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

  // Set default interviewer to passed initialInterviewerId, currently logged-in HR, or first HR
  useEffect(() => {
    if (isOpen && interviewers.length > 0) {
      if (initialInterviewerId && interviewers.some((i) => i.id === Number(initialInterviewerId))) {
        setSelectedInterviewerId(Number(initialInterviewerId));
      } else {
        const loggedInId = parseInt(localStorage.getItem('user_id'), 10);
        const match = interviewers.find((i) => i.id === loggedInId);
        setSelectedInterviewerId(match ? match.id : interviewers[0].id);
      }
    }
  }, [isOpen, interviewers, initialInterviewerId]);

  useEffect(() => {
    if (isOpen) {
      setErrorMsg('');
      setSelectedSlot(null);
      setAvailableSlots([]);

      if (initialTime) {
        setUseCustomTime(true);
        setCustomStartTime(initialTime);
        const [h, m] = initialTime.split(':').map(Number);
        const endH = Math.min((h || 9) + 1, 17);
        const endM = m !== undefined ? m : 0;
        setCustomEndTime(`${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`);
      } else {
        setUseCustomTime(false);
      }

      let defaultDate = initialDate || toLocalDateString(new Date());
      // Advance to next Monday if today or initialDate falls on weekend
      if (!isWeekday(defaultDate)) {
        const parts = defaultDate.split('-');
        const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
        while (d.getDay() === 0 || d.getDay() === 6) {
          d.setDate(d.getDate() + 1);
        }
        defaultDate = toLocalDateString(d);
      }
      setDate(defaultDate);
    }
  }, [isOpen, initialDate, initialTime]);

  useEffect(() => {
    if (selectedCandidate) {
      setTitle(`Interview with ${selectedCandidate.candidate_name || selectedCandidate.name}`);
    }
  }, [selectedCandidate]);

  // Fetch available slots for the selected date AND selected HR interviewer
  useEffect(() => {
    if (!date || !isWeekday(date)) {
      setAvailableSlots([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const slots = await getSlots({
          start_date: `${date}T08:00:00`,
          end_date: `${date}T17:00:00`,
          hr_id: selectedInterviewerId || undefined
        }).unwrap();
        setAvailableSlots(slots || []);
      } catch {
        setAvailableSlots([]);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [date, selectedInterviewerId, getSlots]);

  if (!isOpen) return null;

  const selectedInterviewer = interviewers.find((i) => i.id === selectedInterviewerId);

  const getCandidateActiveInterview = (c) => {
    if (!allInterviews || allInterviews.length === 0 || !c) return null;
    const cEmail = (c.candidate_email || c.email || '').toLowerCase().trim();
    return allInterviews.find((iv) => {
      if (iv.status === 'CANCELED') return false;
      if (iv.job_application_id && c.id && iv.job_application_id === c.id) return true;
      if (cEmail && iv.candidate_email && iv.candidate_email.toLowerCase().trim() === cEmail) return true;
      return false;
    });
  };

  const filteredCandidates = candidates.filter((c) => {
    const name = c.candidate_name || c.name || '';
    const job = c.job_title || c.preferredJob || '';
    const email = c.candidate_email || c.email || '';
    const query = searchCandidate.toLowerCase();
    return name.toLowerCase().includes(query) || job.toLowerCase().includes(query) || email.toLowerCase().includes(query);
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!selectedCandidate) {
      setErrorMsg('Please select a candidate application.');
      return;
    }

    const existingActive = getCandidateActiveInterview(selectedCandidate);
    if (existingActive) {
      const interviewerName = existingActive.interviewer_name || existingActive.interviewer?.fullname || 'another HR';
      setErrorMsg(`Candidate '${selectedCandidate.candidate_name || selectedCandidate.name}' is already scheduled for an interview with ${interviewerName}. Another HR cannot schedule an interview for this candidate.`);
      return;
    }

    let finalStart = '';
    let finalEnd = '';

    if (useCustomTime) {
      if (!customStartTime || !customEndTime) {
        setErrorMsg('Please enter both start time and end time.');
        return;
      }
      const [sH, sM] = customStartTime.split(':').map(Number);
      const [eH, eM] = customEndTime.split(':').map(Number);

      if (sH < 8 || eH > 17 || (eH === 17 && eM > 0)) {
        setErrorMsg('Interviews must fall within working hours (8:00 AM – 5:00 PM).');
        return;
      }
      finalStart = `${date}T${customStartTime}:00`;
      finalEnd = `${date}T${customEndTime}:00`;
      if (new Date(finalStart) >= new Date(finalEnd)) {
        setErrorMsg('End time must be after start time.');
        return;
      }
    } else {
      if (!selectedSlot) {
        setErrorMsg('Please select an available time slot or switch to Custom Hours.');
        return;
      }
      finalStart = selectedSlot.start_time;
      finalEnd = selectedSlot.end_time;
    }

    try {
      await scheduleInterview({
        job_application_id: selectedCandidate.id,
        interviewer_id: selectedInterviewerId || undefined,
        title: title.trim() || 'Technical Interview',
        description: description.trim() || undefined,
        start_time: finalStart,
        end_time: finalEnd
      }).unwrap();

      if (onScheduled) {
        onScheduled({
          candidateName: selectedCandidate.candidate_name || selectedCandidate.name || 'Candidate',
          title: title.trim() || 'Technical Interview',
          date: date,
          startTime: finalStart
        });
      }
      onClose();
    } catch (err) {
      setErrorMsg(err?.data?.detail || 'Failed to schedule interview. Please check slot availability.');
    }
  };

  const formatTimeSlot = (isoString) => {
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-4xl max-h-[90vh] rounded-3xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 sm:px-8 py-5 border-b border-gray-100 flex justify-between items-center bg-white sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className="h-2.5 w-2.5 rounded-full bg-[#D60041] animate-pulse" />
            <span className="text-xs font-black text-gray-500 uppercase tracking-wider">
              Schedule New Interview Session
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400 hover:text-gray-700"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-6">
          {errorMsg && (
            <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-2xl flex items-center gap-3 text-xs font-semibold">
              <AlertCircle size={18} className="shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Candidate Selection Section */}
          <div>
            <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
              1. Select Candidate Application
            </label>

            {!selectedCandidate ? (
              <div className="border border-gray-200 rounded-2xl p-4 bg-gray-50/50 space-y-3">
                <div className="relative">
                  <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search candidate by name, job role, or email..."
                    value={searchCandidate}
                    onChange={(e) => setSearchCandidate(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-xs font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                  />
                </div>

                <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                  {isCandidatesLoading ? (
                    <p className="text-xs text-gray-400 p-2 text-center">Loading candidate applications...</p>
                  ) : filteredCandidates.length === 0 ? (
                    <p className="text-xs text-gray-400 p-4 text-center">No matching candidates found.</p>
                  ) : (
                    filteredCandidates.map((c) => {
                      const activeIv = getCandidateActiveInterview(c);
                      const isScheduled = Boolean(activeIv);
                      const interviewerName = activeIv?.interviewer_name || activeIv?.interviewer?.fullname || 'HR Panelist';

                      if (isScheduled) {
                        return (
                          <div
                            key={c.id}
                            title={`Candidate already has an active interview scheduled with ${interviewerName}. Duplicate scheduling is locked.`}
                            className="p-3 bg-gray-50/80 border border-gray-200/90 rounded-xl cursor-not-allowed transition-all flex items-center justify-between shadow-sm opacity-80"
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="w-9 h-9 rounded-lg bg-gray-100 text-gray-400 flex items-center justify-center font-bold text-sm shrink-0">
                                {(c.candidate_name || c.name || 'C').charAt(0)}
                              </div>
                              <div className="truncate">
                                <div className="flex items-center gap-2">
                                  <h5 className="text-xs font-bold text-gray-600 truncate">
                                    {c.candidate_name || c.name}
                                  </h5>
                                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md shrink-0">
                                    <Lock size={10} /> Scheduled with {interviewerName}
                                  </span>
                                </div>
                                <p className="text-[11px] text-gray-400 font-medium truncate mt-0.5">
                                  {c.job_title || c.preferredJob || 'Applicant'} • {c.candidate_email || c.email}
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <span className="text-[11px] text-gray-400 font-bold px-2 py-0.5 bg-gray-100 rounded-md">Locked</span>
                            </div>
                          </div>
                        );
                      }

                      return (
                        <div
                          key={c.id}
                          onClick={() => setSelectedCandidate(c)}
                          className="p-3 bg-white hover:bg-pink-50/60 border border-gray-200/80 hover:border-[#D60041]/40 rounded-xl cursor-pointer transition-all flex items-center justify-between group shadow-sm"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="w-9 h-9 rounded-lg bg-pink-100 text-[#D60041] flex items-center justify-center font-bold text-sm shrink-0">
                              {(c.candidate_name || c.name || 'C').charAt(0)}
                            </div>
                            <div className="truncate">
                              <h5 className="text-xs font-bold text-gray-900 group-hover:text-[#D60041] transition-colors truncate">
                                {c.candidate_name || c.name}
                              </h5>
                              <p className="text-[11px] text-gray-500 font-medium truncate">
                                {c.job_title || c.preferredJob || 'Applicant'} • {c.candidate_email || c.email}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            {c.match_score && (
                              <span className="text-[10px] font-black text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
                                {Math.round(c.match_score)}% Match
                              </span>
                            )}
                            <span className="text-xs text-[#D60041] font-bold group-hover:underline">Select</span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            ) : (
              <div className="p-4 bg-pink-50/50 border border-pink-200 rounded-2xl flex items-center justify-between shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-pink-100 text-[#D60041] flex items-center justify-center font-black text-lg shadow-sm">
                    {(selectedCandidate.candidate_name || selectedCandidate.name || 'C').charAt(0)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-bold text-gray-900">
                        {selectedCandidate.candidate_name || selectedCandidate.name}
                      </h4>
                      <span className="text-[10px] font-black text-[#D60041] bg-white border border-pink-200 px-2 py-0.5 rounded-full uppercase">
                        Selected
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 font-medium mt-0.5">
                      {selectedCandidate.job_title || selectedCandidate.preferredJob} • {selectedCandidate.candidate_email || selectedCandidate.email}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setSelectedCandidate(null)}
                  className="text-xs font-bold text-gray-500 hover:text-rose-600 px-3 py-1.5 bg-white hover:bg-rose-50 border border-gray-200 rounded-xl transition-colors"
                >
                  Change
                </button>
              </div>
            )}
          </div>

          {/* HR Interviewer / Panelist Selection */}
          <div>
            <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2 flex items-center justify-between">
              <span>2. Select HR Interviewer / Panelist</span>
              <span className="text-[10px] text-gray-500 font-medium normal-case">
                Syncs with selected HR's Google Calendar
              </span>
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {interviewers.map((hr) => {
                const isSelected = selectedInterviewerId === hr.id;
                return (
                  <button
                    key={hr.id}
                    type="button"
                    onClick={() => setSelectedInterviewerId(hr.id)}
                    className={`p-3 rounded-2xl border text-left transition-all flex items-start gap-3 relative ${
                      isSelected
                        ? 'bg-rose-50/70 border-[#D60041] ring-1 ring-[#D60041] shadow-sm'
                        : 'bg-gray-50/50 hover:bg-white border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="relative shrink-0">
                      {hr.profile_image_url ? (
                        <img
                          src={hr.profile_image_url}
                          alt={hr.fullname}
                          className="w-10 h-10 rounded-xl object-cover border border-gray-200 shadow-sm"
                        />
                      ) : (
                        <div
                          className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm shadow-sm ${
                            isSelected
                              ? 'bg-[#D60041] text-white'
                              : 'bg-white text-gray-700 border border-gray-200'
                          }`}
                        >
                          {(hr.fullname || hr.email || 'H').charAt(0).toUpperCase()}
                        </div>
                      )}
                      {hr.has_google_calendar && (
                        <span
                          title="Google Calendar Synced"
                          className="absolute -bottom-1 -right-1 w-3.5 h-3.5 bg-emerald-500 border-2 border-white rounded-full flex items-center justify-center"
                        >
                          <Check size={8} className="text-white" strokeWidth={3} />
                        </span>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <p className={`text-xs font-bold truncate ${isSelected ? 'text-[#D60041]' : 'text-gray-900'}`}>
                          {hr.fullname}
                        </p>
                      </div>
                      <p className="text-[11px] text-gray-500 font-medium truncate">
                        {hr.position || 'HR Specialist'}
                      </p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span
                          className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold ${
                            hr.has_google_calendar
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {hr.has_google_calendar ? 'G-Calendar Linked' : 'System Calendar'}
                        </span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Date & Title */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                3. Interview Date (Mon – Fri)
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                required
              />
              {date && !isWeekday(date) && (
                <p className="text-[11px] text-amber-600 font-medium mt-1">
                  Selected date falls on a weekend. Please choose a weekday.
                </p>
              )}
            </div>

            <div>
              <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                Session Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Initial Screening Interview"
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                required
              />
            </div>
          </div>

          {/* Available Slots & Time Picker */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-black text-gray-700 uppercase tracking-wider">
                4. Select Interview Time Window (8:00 AM – 5:00 PM)
              </label>

              <div className="flex items-center gap-1 bg-gray-100 p-0.5 rounded-xl text-[11px] font-bold">
                <button
                  type="button"
                  onClick={() => setUseCustomTime(false)}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    !useCustomTime
                      ? 'bg-white text-[#D60041] shadow-sm font-black'
                      : 'text-gray-500 hover:text-gray-900'
                  }`}
                >
                  Recommended ({availableSlots.length})
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setUseCustomTime(true);
                    setSelectedSlot(null);
                  }}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    useCustomTime
                      ? 'bg-white text-[#D60041] shadow-sm font-black'
                      : 'text-gray-500 hover:text-gray-900'
                  }`}
                >
                  Custom Hours
                </button>
              </div>
            </div>

            {!useCustomTime ? (
              <div className="p-4 bg-gray-50/60 border border-gray-200 rounded-2xl min-h-[100px] flex items-center">
                {isFetchingSlots ? (
                  <div className="w-full text-center py-4">
                    <div className="w-6 h-6 border-2 border-[#D60041] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    <p className="text-xs text-gray-500 font-semibold">Scanning conflict-free hours for {selectedInterviewer?.fullname || 'HR'}...</p>
                  </div>
                ) : availableSlots.length === 0 ? (
                  <div className="w-full text-center py-4 text-gray-400 space-y-2">
                    <Clock size={24} className="mx-auto text-gray-300" />
                    <p className="text-xs font-semibold">
                      {date && isWeekday(date)
                        ? 'No 1-hour standard slots free on this date.'
                        : 'Select a valid weekday to view available slots.'}
                    </p>
                    <button
                      type="button"
                      onClick={() => setUseCustomTime(true)}
                      className="text-xs text-[#D60041] font-bold underline hover:text-rose-700"
                    >
                      Set custom start & end hours
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 w-full">
                    {availableSlots.map((slot, idx) => {
                      const isSelected = selectedSlot && selectedSlot.start_time === slot.start_time;
                      return (
                        <button
                          type="button"
                          key={idx}
                          onClick={() => {
                            setSelectedSlot(slot);
                            setCustomStartTime(new Date(slot.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }));
                            setCustomEndTime(new Date(slot.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }));
                          }}
                          className={`p-3 rounded-xl border text-xs font-bold transition-all text-center flex flex-col items-center justify-center gap-1 ${
                            isSelected
                              ? 'bg-[#D60041] text-white border-[#D60041] shadow-md shadow-[#D60041]/20 scale-102'
                              : 'bg-white hover:bg-pink-50/60 border-gray-200 text-gray-800 hover:border-[#D60041]/50'
                          }`}
                        >
                          <Clock size={14} className={isSelected ? 'text-white' : 'text-[#D60041]'} />
                          <span>{formatTimeSlot(slot.start_time)}</span>
                          <span className={`text-[9px] ${isSelected ? 'text-pink-100' : 'text-gray-400'}`}>1 Hour</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 bg-white border border-gray-200 rounded-2xl space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-gray-600 mb-1">Start Time (From 8:00 AM)</label>
                    <input
                      type="time"
                      min="08:00"
                      max="16:30"
                      value={customStartTime}
                      onChange={(e) => setCustomStartTime(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-gray-600 mb-1">End Time (Until 5:00 PM)</label>
                    <input
                      type="time"
                      min="08:30"
                      max="17:00"
                      value={customEndTime}
                      onChange={(e) => setCustomEndTime(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
                      required
                    />
                  </div>
                </div>

                {/* Quick Presets */}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <span className="text-[10px] text-gray-400 font-bold uppercase mr-1">Presets:</span>
                  {[
                    ['09:00', '10:00'],
                    ['10:00', '11:00'],
                    ['11:00', '12:00'],
                    ['13:00', '14:00'],
                    ['14:00', '15:00'],
                    ['15:00', '16:00'],
                    ['16:00', '17:00'],
                  ].map(([st, et]) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => {
                        setCustomStartTime(st);
                        setCustomEndTime(et);
                      }}
                      className={`px-2 py-1 rounded-lg border text-[11px] font-semibold transition-colors ${
                        customStartTime === st && customEndTime === et
                          ? 'bg-[#D60041] text-white border-[#D60041]'
                          : 'bg-gray-50 hover:bg-gray-100 border-gray-200 text-gray-700'
                      }`}
                    >
                      {st} - {et}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Description & Auto-features note */}
          <div>
            <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
              Agenda & Notes (Optional)
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Add key evaluation criteria or panel discussion topics..."
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] resize-none"
            />
          </div>

          {/* Auto Sync Banner */}
          <div className="p-4 bg-gradient-to-r from-pink-50/70 to-red-50/70 border border-pink-200 rounded-2xl flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white border border-pink-200 text-[#D60041] flex items-center justify-center shrink-0 shadow-sm">
              <Sparkles size={18} />
            </div>
            <div className="text-xs text-gray-700">
              <p className="font-bold text-gray-900">Seamless Automatic Synchronization</p>
              <p className="text-[11px] text-gray-500 font-medium mt-0.5">
                Creating this schedule records the interview in ARAS, adds the event to your Google Calendar, and sends an email notice to the candidate's Gmail account.
              </p>
            </div>
          </div>

          {/* Footer Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100 sticky bottom-0 bg-white">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-xs font-bold transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isScheduling || !selectedCandidate || (!useCustomTime && !selectedSlot) || (useCustomTime && (!customStartTime || !customEndTime))}
              className="px-6 py-2.5 bg-[#D60041] hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-[#D60041]/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isScheduling ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  Creating Schedule & Syncing...
                </>
              ) : (
                'Confirm & Schedule Interview'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default NewScheduleModal;
