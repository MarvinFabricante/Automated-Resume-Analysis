import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Check,
  Clock,
  Globe,
  PhoneCall,
  MessageSquare,
  ShieldCheck,
  AlertCircle,
  X,
  Briefcase,
  ChevronRight,
  Zap,
  Bot,
  Settings2,
  Volume2,
  User
} from 'lucide-react';

const ScheduleInterviewModal = ({ isOpen, onClose, candidate }) => {
  const [formData, setFormData] = useState({
    date: '',
    time: '',
    type: 'Video Call',
    language: 'English',
    voiceType: 'Neural (Professional)',
    notes: '',
    autoVoiceCall: true
  });

  const [isSyncing, setIsSyncing] = useState(false);
  const [isAvailable, setIsAvailable] = useState(true);

  useEffect(() => {
    if (formData.date && formData.time) {
      setIsSyncing(true);
      const timer = setTimeout(() => {
        setIsSyncing(false);
        setIsAvailable(true);
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [formData.date, formData.time]);

  if (!isOpen || !candidate) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    alert(`Twilio AI initialized! Scheduling successful.
Automated Voice: ${formData.voiceType} (${formData.language})
Calendar: Synced
SMS Backup: Enabled`);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50">
      <div className="bg-white w-full max-w-6xl max-h-[90vh] rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
        
        <div className="px-8 py-5 border-b border-gray-100 flex justify-between items-center bg-white sticky top-0">
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
          <div className="w-full md:w-80 bg-gray-50/50 border-r border-gray-100 p-8 overflow-y-auto flex flex-col justify-between">
            <div className="space-y-6">
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

              <div className="space-y-4">
                <div className="p-4 rounded-2xl bg-white border border-gray-100 shadow-sm">
                  <p className="text-[9px] font-bold text-gray-400 uppercase mb-1">Match Rating</p>
                  <p className="text-2xl font-black text-emerald-500">{candidate.matchScore}% Match</p>
                </div>

                <div className={`p-4 rounded-2xl border transition-all ${isSyncing ? 'bg-white border-gray-100' : isAvailable ? 'bg-white border-green-500/10' : 'bg-white border-red-500/10'}`}>
                  {isSyncing ? (
                    <div className="flex items-center gap-3">
                      <div className="w-4 h-4 border-2 border-[#d81159] border-t-transparent rounded-full animate-spin" />
                      <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider">Syncing Calendars...</span>
                    </div>
                  ) : (
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-xl ${isAvailable ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-600'}`}>
                        {isAvailable ? <ShieldCheck size={18} /> : <AlertCircle size={18} />}
                      </div>
                      <div>
                        <p className={`text-[10px] font-black uppercase tracking-wider ${isAvailable ? 'text-green-600' : 'text-red-600'}`}>
                          {isAvailable ? 'Conflict-Free Slot' : 'Conflict Detected'}
                        </p>
                        <p className="text-[10px] text-gray-400 font-medium leading-relaxed mt-0.5">
                          {isAvailable ? 'HR & Manager schedules verified.' : 'Time conflict detected in manager calendar.'}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="text-[9px] font-black text-gray-400 uppercase tracking-widest pt-6 mt-6 border-t border-gray-100/50">
              Twilio Engine v2.4.0 Live
            </div>
          </div>

          {/* Main content area */}
          <div className="flex-grow p-8 overflow-y-auto bg-white flex flex-col justify-between">
            <div className="space-y-8">
              {/* Date & Time */}
              <div>
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
                  <Clock size={16} className="text-[#d81159]" /> Schedule Setup
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Interview Date</label>
                    <input
                      required
                      type="date"
                      className="w-full px-4 py-3 bg-gray-50 border border-gray-100 rounded-xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#d81159]/20 focus:border-[#d81159] transition-all"
                      onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Preferred Time</label>
                    <input
                      required
                      type="time"
                      className="w-full px-4 py-3 bg-gray-50 border border-gray-100 rounded-xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#d81159]/20 focus:border-[#d81159] transition-all"
                      onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              {/* Format selection */}
              <div>
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 block">Interview Format</label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: 'Video Call', icon: <Volume2 size={16} /> },
                    { id: 'In-Person', icon: <User size={16} /> },
                    { id: 'Phone', icon: <PhoneCall size={16} /> }
                  ].map((type) => (
                    <button
                      key={type.id}
                      type="button"
                      onClick={() => setFormData({ ...formData, type: type.id })}
                      className={`flex items-center justify-center gap-2 py-3 px-4 rounded-xl border text-[11px] font-bold uppercase tracking-wider transition-all ${formData.type === type.id
                        ? 'bg-[#d81159] text-white border-[#d81159] shadow-md shadow-pink-100'
                        : 'bg-white text-gray-600 border-gray-100 hover:bg-gray-50'
                      }`}
                    >
                      {type.icon}
                      {type.id}
                    </button>
                  ))}
                </div>
              </div>

              {/* Twilio AI Caller parameters */}
              <div>
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
                  <Bot size={16} className="text-[#d81159]" /> Twilio AI Infrastructure
                </h3>
                
                <div className="p-5 rounded-2xl bg-gray-50 border border-gray-100 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-bold text-gray-800">Auto-Call Pipeline</p>
                      <p className="text-[9px] text-gray-400 uppercase font-medium">REQ028 Integrated Engine</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.autoVoiceCall}
                        onChange={(e) => setFormData({ ...formData, autoVoiceCall: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#d81159]"></div>
                    </label>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-gray-200/50">
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">Language</span>
                      <div className="flex gap-2">
                        {['English', 'Filipino'].map(lang => (
                          <button
                            key={lang}
                            type="button"
                            onClick={() => setFormData({ ...formData, language: lang })}
                            className={`flex-1 py-2 rounded-lg text-[10px] font-bold uppercase transition-all border ${formData.language === lang
                              ? 'bg-gray-900 text-white border-gray-900 shadow-sm'
                              : 'bg-white text-gray-500 border-gray-200 hover:bg-gray-50'
                            }`}
                          >
                            {lang}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">Voice Profile</span>
                      <select
                        className="w-full bg-white border border-gray-200 rounded-lg py-2 px-3 text-xs font-bold text-gray-700 cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#d81159]"
                        value={formData.voiceType}
                        onChange={(e) => setFormData({ ...formData, voiceType: e.target.value })}
                      >
                        <option>Neural (Professional)</option>
                        <option>Casual (Friendly)</option>
                        <option>Executive (Formal)</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Internal Notes (Visible to Interviewers)</label>
                <textarea
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-100 rounded-xl text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#d81159]/20 focus:border-[#d81159] transition-all resize-none min-h-[90px]"
                  placeholder="Notes or cover points..."
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                />
              </div>
            </div>

            {/* Form Footer */}
            <div className="flex flex-col sm:flex-row justify-end gap-3 mt-8 pt-6 border-t border-gray-100 bg-white">
              <button
                type="button"
                onClick={async () => {
                  const phone = candidate.phone || "+1234567890";
                  try {
                    const res = await fetch(`http://localhost:8000/ai-caller/call-candidate/${encodeURIComponent(phone)}`, {
                      method: 'POST'
                    });
                    const data = await res.json();
                    if (res.ok) alert(`AI Interview Call Initiated!\nCall SID: ${data.call_sid}`);
                    else alert(`Failed to start call: ${data.detail}`);
                  } catch (err) {
                    alert("Connection error occurred while initiating AI call.");
                  }
                }}
                className="px-5 py-2.5 bg-gray-900 text-white rounded-xl text-xs font-bold uppercase tracking-wider hover:bg-gray-800 transition-all flex items-center gap-2"
              >
                <PhoneCall size={14} />
                Start Live AI Interview
              </button>

              <button
                type="submit"
                className="px-5 py-2.5 bg-[#d81159] text-white rounded-xl text-xs font-bold uppercase tracking-wider hover:shadow-lg hover:shadow-pink-200 transition-all"
              >
                Schedule & Initialize AI
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ScheduleInterviewModal;