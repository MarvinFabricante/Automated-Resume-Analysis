import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Check,
  Clock,
  ShieldCheck,
  AlertCircle,
  X,
  Users,
  Video,
  FileText
} from 'lucide-react';
import { 
  useGetUsersQuery, 
  useGetAvailableSlotsMutation, 
  useScheduleInterviewMutation 
} from '../../../redux/api/apiSlice';

const ScheduleInterviewModal = ({ isOpen, onClose, candidate }) => {
  const { data: users = [], isLoading: isLoadingUsers } = useGetUsersQuery();
  const [getSlots, { isLoading: isFetchingSlots }] = useGetAvailableSlotsMutation();
  const [scheduleInterview, { isLoading: isScheduling }] = useScheduleInterviewMutation();

  const [formData, setFormData] = useState({
    date: '',
    title: 'Initial Interview',
    description: '',
    panelistIds: [],
    selectedSlot: null
  });

  const [availableSlots, setAvailableSlots] = useState([]);
  const [hasAttemptedFetch, setHasAttemptedFetch] = useState(false);

  useEffect(() => {
    if (formData.date && formData.panelistIds.length > 0) {
      const fetchSlots = async () => {
        setHasAttemptedFetch(true);
        try {
          const startDate = new Date(formData.date);
          startDate.setHours(0, 0, 0, 0);
          
          const endDate = new Date(formData.date);
          endDate.setHours(23, 59, 59, 999);

          const slots = await getSlots({
            panelist_ids: formData.panelistIds,
            start_date: startDate.toISOString(),
            end_date: endDate.toISOString()
          }).unwrap();
          
          setAvailableSlots(slots || []);
        } catch (error) {
          console.error("Failed to fetch slots:", error);
          setAvailableSlots([]);
        }
      };
      
      const timer = setTimeout(() => {
        fetchSlots();
      }, 500); // debounce
      return () => clearTimeout(timer);
    } else {
      setAvailableSlots([]);
      setHasAttemptedFetch(false);
    }
  }, [formData.date, formData.panelistIds, getSlots]);

  if (!isOpen || !candidate) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.selectedSlot) {
      alert("Please select a time slot.");
      return;
    }
    if (formData.panelistIds.length === 0) {
      alert("Please select at least one panelist.");
      return;
    }

    try {
      await scheduleInterview({
        job_application_id: candidate.id,
        title: formData.title,
        description: formData.description,
        start_time: formData.selectedSlot.start_time,
        end_time: formData.selectedSlot.end_time,
        panelist_ids: formData.panelistIds
      }).unwrap();
      
      alert(`Interview successfully scheduled!\nGoogle Calendar Event created and Twilio SMS sent to ${candidate.name}.`);
      onClose();
    } catch (error) {
      console.error("Schedule error:", error);
      alert("Failed to schedule interview. Ensure panelists have Google Calendar access.");
    }
  };

  const togglePanelist = (userId) => {
    setFormData(prev => {
      const current = prev.panelistIds;
      const isSelected = current.includes(userId);
      return {
        ...prev,
        panelistIds: isSelected 
          ? current.filter(id => id !== userId) 
          : [...current, userId],
        selectedSlot: null // reset slot if panelists change
      };
    });
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
                        {hasAttemptedFetch ? (availableSlots.length > 0 ? 'Conflict-Free Slots Found' : 'No Slots Available') : 'Select Date & Panel'}
                      </p>
                      <p className="text-[10px] text-gray-400 font-medium leading-relaxed mt-0.5">
                        {hasAttemptedFetch ? (availableSlots.length > 0 ? 'HR & Panel schedules verified.' : 'No mutual availability found.') : 'Awaiting input to check availability.'}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div className="mt-auto">
                <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest pt-4 border-t border-gray-100/50 flex items-center gap-2">
                    <Video size={14} className="text-[#d81159]" />
                    Google Meet Integrated
                </div>
            </div>
          </div>

          {/* Main content area */}
          <div className="flex-grow p-8 overflow-y-auto bg-white flex flex-col">
            <div className="space-y-8 flex-1">
              
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
                      placeholder="Meeting agenda, technical questions to ask..."
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              {/* Panel Selection */}
              <div>
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
                  <Users size={16} className="text-[#d81159]" /> Select Panelists
                </h3>
                {isLoadingUsers ? (
                    <p className="text-sm text-gray-400">Loading users...</p>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {users.map(user => (
                        <div 
                            key={user.id} 
                            onClick={() => togglePanelist(user.id)}
                            className={`cursor-pointer flex flex-col p-3 rounded-xl border transition-all ${
                                formData.panelistIds.includes(user.id) 
                                    ? 'bg-pink-50 border-[#d81159] text-[#d81159]' 
                                    : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                            }`}
                        >
                            <span className="text-xs font-bold truncate">{user.fullname || user.email}</span>
                            <span className="text-[10px] opacity-80 mt-1 uppercase tracking-wider">{user.role}</span>
                        </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Date & Time Availability */}
              <div>
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
                  <Clock size={16} className="text-[#d81159]" /> Schedule Date & Time
                </h3>
                
                <div className="space-y-4">
                  <div className="space-y-2 max-w-[250px]">
                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Interview Date</label>
                    <input
                      required
                      type="date"
                      className="w-full px-4 py-3 bg-gray-50 border border-gray-100 rounded-xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#d81159]/20 focus:border-[#d81159] transition-all"
                      value={formData.date}
                      onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    />
                  </div>

                  {formData.date && formData.panelistIds.length > 0 && (
                    <div className="pt-2">
                        <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-2">Available System Recommended Slots</label>
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
                            <div className="py-4 px-5 bg-red-50 border border-red-100 rounded-xl">
                                <p className="text-xs font-bold text-red-600">No available slots found for the selected date and panelists.</p>
                                <p className="text-[10px] text-red-500 mt-1">Please try another date or adjust the panel.</p>
                            </div>
                        )}
                    </div>
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
                disabled={isScheduling || !formData.selectedSlot}
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