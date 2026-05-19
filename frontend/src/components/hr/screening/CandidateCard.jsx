import React, { useState, useRef, useEffect } from 'react';
import { Calendar, MapPin, ChevronDown, CheckCircle2, XCircle, Clock, Search, Check } from 'lucide-react';

const CandidateCard = ({ candidate, onOpenDetails, onOpenInterview, onUpdateStatus }) => {
  const [isUpdating, setIsUpdating] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  
  const status = candidate.status.toLowerCase();
  
  const avatarUrl = candidate.profileImage 
    ? (candidate.profileImage.startsWith('http') ? candidate.profileImage : `http://localhost:8000/${candidate.profileImage}`)
    : `https://ui-avatars.com/api/?name=${encodeURIComponent(candidate.name)}&background=fdf2f8&color=d81159&bold=true`;

  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getStatusInfo = (status) => {
    switch(status.toLowerCase()) {
      case 'accepted': return { icon: <CheckCircle2 className="w-4 h-4" />, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100', label: 'Accepted' };
      case 'rejected': return { icon: <XCircle className="w-4 h-4" />, color: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-100', label: 'Rejected' };
      case 'reviewed': return { icon: <Search className="w-4 h-4" />, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-100', label: 'Reviewed' };
      default: return { icon: <Clock className="w-4 h-4" />, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100', label: 'Pending' };
    }
  };

  const statusInfo = getStatusInfo(candidate.status);

  return (
    <div className="bg-white p-6 md:p-8 rounded-[32px] border border-gray-100 shadow-sm hover:shadow-[0_20px_50px_rgba(0,0,0,0.04)] hover:-translate-y-1 transition-all duration-500 group">
      <div className="flex flex-col lg:flex-row gap-8 items-start lg:items-center">
        {/* Profile Section */}
        <div className="relative shrink-0">
          <div className="w-20 h-20 rounded-2xl overflow-hidden border-2 border-white shadow-xl group-hover:scale-105 transition-transform duration-500">
            <img 
              src={avatarUrl} 
              alt={candidate.name} 
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(candidate.name)}&background=fdf2f8&color=d81159&bold=true`;
              }}
            />
          </div>
          <div className={`absolute -bottom-1 -right-1 p-1.5 rounded-xl border-4 border-white shadow-lg ${statusInfo.bg} ${statusInfo.color}`}>
            {statusInfo.icon}
          </div>
        </div>

        {/* Content Section */}
        <div className="flex-grow w-full">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h3 className="text-xl font-bold text-gray-900 tracking-tight leading-none">{candidate.name}</h3>
                <span className="px-3 py-1 bg-gray-900 text-white text-[10px] font-bold uppercase tracking-widest rounded-full">
                  {Math.round(candidate.matchScore)}% Match
                </span>
              </div>
              <p className="text-sm text-gray-500 font-semibold flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-[#D60041] rounded-full"></span>
                {candidate.preferredJob}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mb-6">
            {candidate.skills.slice(0, 5).map((skill, idx) => (
              <span key={idx} className="bg-gray-50 border border-gray-100 text-gray-400 text-[10px] font-bold uppercase tracking-tight px-3 py-1.5 rounded-xl transition-all duration-300 group-hover:bg-white group-hover:border-pink-100 group-hover:text-[#D60041]">
                {skill}
              </span>
            ))}
            {candidate.skills.length > 5 && (
              <span className="bg-gray-50 text-gray-300 text-[10px] font-bold px-2 py-1.5 rounded-xl">
                +{candidate.skills.length - 5}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-6 pt-6 border-t border-gray-50">
            <div className="flex items-center gap-2 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
              <Calendar className="w-3.5 h-3.5 text-gray-300" />
              Applied on {formatDate(candidate.date)}
            </div>
            <div className="flex items-center gap-2 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
              <MapPin className="w-3.5 h-3.5 text-gray-300" />
              {candidate.location}
            </div>
          </div>
        </div>

        {/* Action Section */}
        <div className="flex flex-row flex-wrap lg:flex-nowrap gap-3 w-full lg:w-auto shrink-0 mt-6 lg:mt-0 pt-6 lg:pt-0 border-t lg:border-t-0 border-gray-50">
          {/* Custom Status Dropdown as a Button */}
          <div className="relative flex-1 lg:flex-none lg:min-w-[140px]" ref={dropdownRef}>
            <button 
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              disabled={isUpdating}
              className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl border-2 text-[10px] font-bold uppercase tracking-widest transition-all duration-300 ${statusInfo.bg} ${statusInfo.color} ${statusInfo.border} ${isUpdating ? 'opacity-50 animate-pulse' : 'hover:shadow-md hover:scale-[1.02] active:scale-95'}`}
            >
              {statusInfo.icon}
              {statusInfo.label}
              <ChevronDown className={`w-3 h-3 transition-transform duration-300 ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {isDropdownOpen && (
              <div className="absolute top-full right-0 mt-2 w-48 bg-white border border-gray-100 rounded-2xl shadow-2xl z-50 py-2 animate-in fade-in slide-in-from-top-2 duration-200">
                {['Pending', 'Reviewed', 'Accepted', 'Rejected'].map((s) => {
                  const info = getStatusInfo(s);
                  return (
                    <button
                      key={s}
                      onClick={async () => {
                        setIsDropdownOpen(false);
                        setIsUpdating(true);
                        await onUpdateStatus(candidate.id, s);
                        setTimeout(() => setIsUpdating(false), 800);
                      }}
                      className={`w-full flex items-center justify-between px-4 py-2.5 text-[10px] font-bold uppercase tracking-widest transition-colors ${candidate.status.toLowerCase() === s.toLowerCase() ? info.bg + ' ' + info.color : 'text-gray-500 hover:bg-gray-50'}`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={info.color}>{info.icon}</span>
                        {s}
                      </div>
                      {candidate.status.toLowerCase() === s.toLowerCase() && <Check className="w-3 h-3" />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <button
            onClick={() => onOpenDetails(candidate)}
            className="flex-1 lg:flex-none px-6 py-3 bg-gray-50 text-gray-700 rounded-xl text-[10px] font-bold uppercase tracking-widest hover:bg-gray-100 transition-all active:scale-95 border border-transparent hover:border-gray-200 whitespace-nowrap"
          >
            Details
          </button>
          <button
            onClick={() => onOpenInterview(candidate)}
            className="flex-1 lg:flex-none px-6 py-3 bg-[#D60041] text-white rounded-xl text-[10px] font-bold uppercase tracking-widest hover:bg-[#B50037] shadow-lg shadow-pink-100/50 transition-all active:scale-95 whitespace-nowrap"
          >
            Schedule
          </button>
        </div>
      </div>
    </div>
  );
};

export default CandidateCard;
