import React, { useState, useRef, useEffect } from 'react';
import { 
  Calendar, MapPin, ChevronDown, CheckCircle2, XCircle, Clock, Search, 
  Check, Archive, Trash2, RotateCcw, FileText, Download, Copy, Mail, Phone 
} from 'lucide-react';
import { getAssetUrl } from '../../../services/api';

const CandidateCard = ({ 
  candidate, 
  isSelected = false,
  onToggleSelect,
  onOpenDetails, 
  onOpenInterview, 
  onUpdateStatus, 
  onArchiveApplication,
  onRestoreApplication,
  onDeleteApplication,
  onSkillClick
}) => {
  const [isUpdating, setIsUpdating] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [copiedField, setCopiedField] = useState(null);
  const dropdownRef = useRef(null);

  const status = (candidate.status || '').toLowerCase();
  const isArchived = status === 'archived';

  const avatarUrl = candidate.profileImage
    ? getAssetUrl(candidate.profileImage)
    : `https://ui-avatars.com/api/?name=${encodeURIComponent(candidate.name)}&background=fdf2f8&color=d81159&bold=true`;

  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const handleCopy = (text, field) => {
    if (!text || text === 'N/A') return;
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
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

  const getStatusInfo = (st) => {
    switch ((st || '').toLowerCase()) {
      case 'accepted': return { icon: <CheckCircle2 className="w-4 h-4" />, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Accepted' };
      case 'rejected': return { icon: <XCircle className="w-4 h-4" />, color: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-200', label: 'Rejected' };
      case 'reviewed': return { icon: <Search className="w-4 h-4" />, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', label: 'Reviewed' };
      case 'technical interview': return { icon: <Clock className="w-4 h-4" />, color: 'text-purple-600', bg: 'bg-purple-50', border: 'border-purple-200', label: 'Technical Interview' };
      case 'final interview': return { icon: <Clock className="w-4 h-4" />, color: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-200', label: 'Final Interview' };
      case 'archived': return { icon: <Archive className="w-4 h-4" />, color: 'text-gray-600', bg: 'bg-gray-100', border: 'border-gray-200', label: 'Archived' };
      default: return { icon: <Clock className="w-4 h-4" />, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Pending' };
    }
  };

  const statusInfo = getStatusInfo(candidate.status);
  const match = Math.round(candidate.matchScore || 0);

  const getMatchBadgeStyle = () => {
    if (match >= 80) return 'bg-emerald-600 text-white';
    if (match >= 60) return 'bg-amber-500 text-white';
    return 'bg-gray-700 text-white';
  };

  return (
    <div className={`bg-white p-4 sm:p-6 md:p-8 rounded-2xl sm:rounded-[32px] border transition-all duration-300 group ${
      isSelected 
        ? 'border-[#D60041] ring-2 ring-[#D60041]/10 shadow-md' 
        : 'border-gray-100 shadow-sm hover:shadow-[0_20px_50px_rgba(0,0,0,0.04)] hover:-translate-y-0.5'
    }`}>
      <div className="flex flex-col lg:flex-row gap-5 sm:gap-6 lg:gap-8 items-start lg:items-center">
        
        {/* Selection Checkbox & Avatar */}
        <div className="flex items-center gap-3 shrink-0">
          {onToggleSelect && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => onToggleSelect(candidate.id)}
              className="w-5 h-5 rounded border-gray-300 text-[#D60041] focus:ring-[#D60041] cursor-pointer"
              title="Select for comparison or bulk actions"
            />
          )}

          <div className="relative shrink-0">
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl overflow-hidden border-2 border-white shadow-md group-hover:scale-105 transition-transform duration-300 bg-pink-50">
              <img
                src={avatarUrl}
                alt={candidate.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(candidate.name)}&background=fdf2f8&color=d81159&bold=true`;
                }}
              />
            </div>
            <div className={`absolute -bottom-1 -right-1 p-1.5 rounded-xl border-2 border-white shadow-sm ${statusInfo.bg} ${statusInfo.color}`}>
              {statusInfo.icon}
            </div>
          </div>
        </div>

        {/* Content Section */}
        <div className="flex-grow w-full min-w-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-4 mb-3 sm:mb-4">
            <div>
              <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-1">
                <h3 
                  onClick={() => onOpenDetails(candidate)}
                  className="text-lg sm:text-xl font-bold text-gray-900 tracking-tight leading-tight hover:text-[#D60041] cursor-pointer transition-colors"
                >
                  {candidate.name}
                </h3>
                <span className={`px-2.5 sm:px-3 py-0.5 sm:py-1 text-[10px] font-bold uppercase tracking-widest rounded-full shadow-sm ${getMatchBadgeStyle()}`}>
                  {match}% Match
                </span>
                {candidate.ai_powered && (
                  <span className="px-2 py-0.5 bg-gradient-to-r from-purple-50 to-pink-50 text-purple-700 border border-purple-100 text-[9px] font-black uppercase tracking-wider rounded-md">
                    AI Analyzed
                  </span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-y-1 gap-x-3 text-xs sm:text-sm text-gray-500 font-semibold">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-[#D60041] rounded-full shrink-0"></span>
                  <span className="truncate">{candidate.preferredJob}</span>
                </span>
                {candidate.company && candidate.company !== 'N/A' && (
                  <span className="text-gray-400 font-normal">
                    • Previous: {candidate.company}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Skills Pills */}
          <div className="flex flex-wrap gap-1.5 sm:gap-2 mb-4">
            {(candidate.skills || []).slice(0, 5).map((skill, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSkillClick && onSkillClick(skill)}
                title={`Filter candidates by skill: ${skill}`}
                className="bg-gray-50 border border-gray-100 hover:border-pink-200 hover:bg-pink-50/50 hover:text-[#D60041] text-gray-500 text-[10px] font-bold uppercase tracking-tight px-2.5 sm:px-3 py-1 rounded-xl transition-all duration-200 cursor-pointer"
              >
                {skill}
              </button>
            ))}
            {(candidate.skills || []).length > 5 && (
              <span className="bg-gray-50 text-gray-400 text-[10px] font-bold px-2 py-1 rounded-xl border border-gray-100">
                +{candidate.skills.length - 5}
              </span>
            )}
          </div>

          {/* Meta Info & Quick Contact */}
          <div className="flex flex-wrap items-center gap-y-2 gap-x-5 pt-3 sm:pt-4 border-t border-gray-50 text-[11px] text-gray-400 font-medium">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-gray-300 shrink-0" />
              Applied {formatDate(candidate.date)}
            </div>
            
            <div className="flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-gray-300 shrink-0" />
              {candidate.location}
            </div>

            {candidate.email && candidate.email !== 'N/A' && (
              <div className="flex items-center gap-1.5 text-gray-500 group/copy">
                <Mail className="w-3.5 h-3.5 text-gray-300 shrink-0" />
                <span className="truncate max-w-[170px]">{candidate.email}</span>
                <button
                  type="button"
                  onClick={() => handleCopy(candidate.email, 'email')}
                  title="Copy email"
                  className="hover:text-gray-900 transition-colors p-0.5"
                >
                  {copiedField === 'email' ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
                </button>
              </div>
            )}

            {candidate.phone && candidate.phone !== 'N/A' && (
              <div className="hidden sm:flex items-center gap-1.5 text-gray-500">
                <Phone className="w-3.5 h-3.5 text-gray-300 shrink-0" />
                <span>{candidate.phone}</span>
                <button
                  type="button"
                  onClick={() => handleCopy(candidate.phone, 'phone')}
                  title="Copy phone"
                  className="hover:text-gray-900 transition-colors p-0.5"
                >
                  {copiedField === 'phone' ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Action Section */}
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 sm:gap-3 w-full lg:w-auto shrink-0 mt-4 sm:mt-6 lg:mt-0 pt-4 sm:pt-6 lg:pt-0 border-t lg:border-t-0 border-gray-50">
          <div className="flex items-center gap-1.5 shrink-0">
            {/* Direct Resume View/Download */}
            {candidate.resumeUrl && (
              <button
                type="button"
                onClick={() => {
                  const fullUrl = getAssetUrl(candidate.resumeUrl);
                  window.open(fullUrl, '_blank');
                }}
                title="View / Download Resume"
                className="p-2.5 sm:p-3 bg-gray-50 border border-gray-100 text-gray-500 hover:bg-pink-50 hover:border-pink-100 hover:text-[#D60041] rounded-xl transition-all duration-200 hover:shadow-sm"
              >
                <FileText size={16} />
              </button>
            )}

            {/* Archive or Restore Button */}
            {isArchived ? (
              <button
                type="button"
                onClick={() => onRestoreApplication ? onRestoreApplication(candidate.id) : onUpdateStatus(candidate.id, 'Pending')}
                title="Restore / Unarchive Candidate"
                className="p-2.5 sm:p-3 bg-emerald-50 border border-emerald-100 text-emerald-600 hover:bg-emerald-100 rounded-xl transition-all duration-200 hover:shadow-sm"
              >
                <RotateCcw size={16} />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onArchiveApplication(candidate.id)}
                title="Archive Candidate"
                className="p-2.5 sm:p-3 bg-gray-50 border border-gray-100 text-gray-400 hover:bg-amber-50 hover:border-amber-100 hover:text-amber-600 rounded-xl transition-all duration-200 hover:shadow-sm"
              >
                <Archive size={16} />
              </button>
            )}

            {/* Remove / Delete Button */}
            <button
              type="button"
              onClick={() => onDeleteApplication(candidate.id)}
              title="Remove Candidate Application"
              className="p-2.5 sm:p-3 bg-gray-50 border border-gray-100 text-gray-400 hover:bg-rose-50 hover:border-rose-100 hover:text-rose-600 rounded-xl transition-all duration-200 hover:shadow-sm"
            >
              <Trash2 size={16} />
            </button>
          </div>

          {/* Custom Status Dropdown */}
          <div className="relative flex-1 sm:flex-none sm:min-w-[130px] lg:min-w-[140px]" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              disabled={isUpdating}
              className={`w-full flex items-center justify-center gap-2 py-2.5 sm:py-3 px-3 sm:px-4 rounded-xl border text-[10px] font-bold uppercase tracking-widest transition-all duration-200 ${statusInfo.bg} ${statusInfo.color} ${statusInfo.border} ${isUpdating ? 'opacity-50 animate-pulse' : 'hover:shadow-sm'}`}
            >
              {statusInfo.icon}
              <span className="truncate">{statusInfo.label}</span>
              <ChevronDown className={`w-3 h-3 shrink-0 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {isDropdownOpen && (
              <div className="absolute top-full right-0 mt-2 w-48 bg-white border border-gray-100 rounded-2xl shadow-2xl z-50 py-2 animate-in fade-in slide-in-from-top-2 duration-150">
                {['Pending', 'Reviewed', 'Technical Interview', 'Final Interview', 'Accepted', 'Rejected'].map((s) => {
                  const info = getStatusInfo(s);
                  const isCurrent = status === s.toLowerCase();
                  return (
                    <button
                      key={s}
                      type="button"
                      onClick={async () => {
                        setIsDropdownOpen(false);
                        setIsUpdating(true);
                        await onUpdateStatus(candidate.id, s);
                        setTimeout(() => setIsUpdating(false), 600);
                      }}
                      className={`w-full flex items-center justify-between px-4 py-2.5 text-[10px] font-bold uppercase tracking-widest transition-colors ${
                        isCurrent ? info.bg + ' ' + info.color : 'text-gray-500 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={info.color}>{info.icon}</span>
                        {s}
                      </div>
                      {isCurrent && <Check className="w-3 h-3" />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Details & Schedule Action Buttons */}
          <div className="flex items-center gap-2 flex-1 sm:flex-none">
            <button
              type="button"
              onClick={() => onOpenDetails(candidate)}
              className="flex-1 sm:flex-none px-4 sm:px-5 py-2.5 sm:py-3 bg-gray-50 text-gray-700 rounded-xl text-[10px] font-bold uppercase tracking-widest hover:bg-gray-100 transition-all border border-gray-100 hover:border-gray-200 whitespace-nowrap text-center"
            >
              Details
            </button>
            <button
              type="button"
              onClick={() => onOpenInterview(candidate)}
              className="flex-1 sm:flex-none px-4 sm:px-5 py-2.5 sm:py-3 bg-[#D60041] text-white rounded-xl text-[10px] font-bold uppercase tracking-widest hover:bg-[#B50037] shadow-sm hover:shadow-md transition-all whitespace-nowrap text-center"
            >
              Schedule
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CandidateCard;
