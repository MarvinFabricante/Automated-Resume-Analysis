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
  Video,
  ShieldCheck,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import {
  useGetApplicationsQuery,
  useGetAvailableSlotsMutation,
  useScheduleInterviewMutation
} from '../../../redux/api/apiSlice';

const NewScheduleModal = ({ isOpen, onClose, initialDate, onScheduled }) => {
  const { data: candidates = [], isLoading: isCandidatesLoading } = useGetApplicationsQuery();
  const [getSlots, { isLoading: isFetchingSlots }] = useGetAvailableSlotsMutation();
  const [scheduleInterview, { isLoading: isScheduling }] = useScheduleInterviewMutation();

  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [searchCandidate, setSearchCandidate] = useState('');
  const [date, setDate] = useState('');
  const [title, setTitle] = useState('Technical Interview');
  const [description, setDescription] = useState('');
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [errorMsg, setErrorMsg] = useState('');

  const isWeekday = (dateStr) => {
    if (!dateStr) return false;
    const d = new Date(dateStr + 'T00:00:00');
    const day = d.getDay();
    return day !== 0 && day !== 6;
  };

  useEffect(() => {
    if (isOpen) {
      setErrorMsg('');
      setSelectedSlot(null);
      setAvailableSlots([]);
      const todayISO = new Date().toISOString().split('T')[0];
      setDate(initialDate || todayISO);
    }
  }, [isOpen, initialDate]);

  useEffect(() => {
    if (selectedCandidate) {
      setTitle(`Interview with ${selectedCandidate.candidate_name || selectedCandidate.name}`);
    }
  }, [selectedCandidate]);

  useEffect(() => {
    if (!date || !isWeekday(date)) {
      setAvailableSlots([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const slots = await getSlots({
          start_date: `${date}T08:00:00`,
          end_date: `${date}T17:00:00`
        }).unwrap();
        setAvailableSlots(slots || []);
      } catch {
        setAvailableSlots([]);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [date, getSlots]);

  if (!isOpen) return null;

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
      setErrorMsg('Please select a candidate for the interview.');
      return;
    }

    if (!selectedSlot) {
      setErrorMsg('Please select an available time slot.');
      return;
    }

    try {
      await scheduleInterview({
        job_application_id: selectedCandidate.id,
        title,
        description,
        start_time: selectedSlot.start_time,
        end_time: selectedSlot.end_time
      }).unwrap();

      if (onScheduled) onScheduled();
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
                    filteredCandidates.map((c) => (
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
                    ))
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

          {/* Date & Title */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2">
                2. Interview Date (Mon – Fri)
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

          {/* Available Slots */}
          <div>
            <label className="block text-xs font-black text-gray-700 uppercase tracking-wider mb-2 flex items-center justify-between">
              <span>3. Choose System-Recommended Slot (8:00 AM – 5:00 PM)</span>
              {isFetchingSlots && (
                <span className="text-[10px] text-[#D60041] font-bold flex items-center gap-1 normal-case">
                  <RefreshCw size={10} className="animate-spin" /> Verifying Google Calendar free/busy...
                </span>
              )}
            </label>

            <div className="p-4 bg-gray-50/60 border border-gray-200 rounded-2xl min-h-[100px] flex items-center">
              {isFetchingSlots ? (
                <div className="w-full text-center py-4">
                  <div className="w-6 h-6 border-2 border-[#D60041] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  <p className="text-xs text-gray-500 font-semibold">Scanning conflict-free hours...</p>
                </div>
              ) : availableSlots.length === 0 ? (
                <div className="w-full text-center py-4 text-gray-400">
                  <Clock size={24} className="mx-auto mb-1 text-gray-300" />
                  <p className="text-xs font-semibold">
                    {date && isWeekday(date) ? 'No available slots found on this date.' : 'Select a valid weekday to view available slots.'}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 w-full">
                  {availableSlots.map((slot, idx) => {
                    const isSelected = selectedSlot && selectedSlot.start_time === slot.start_time;
                    return (
                      <button
                        type="button"
                        key={idx}
                        onClick={() => setSelectedSlot(slot)}
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
                Creating this schedule records the interview in ARAS, adds the event with Google Meet to your Google Calendar, and sends an SMS notice to the candidate.
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
              disabled={isScheduling || !selectedCandidate || !selectedSlot}
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
