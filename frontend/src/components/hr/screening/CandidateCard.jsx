import React, { useState, useRef, useEffect } from 'react';
import { 
  Calendar, MapPin, ChevronDown, CheckCircle2, XCircle, Clock, Search, 
  Check, Archive, Trash2, RotateCcw, FileText, Download, Copy, Mail, Phone,
  Zap, Briefcase, GraduationCap, Sparkles
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
    : `https://ui-avatars.com/api/?name=${encodeURIComponent(candidate.name || 'Candidate')}&background=fdf2f8&color=d81159&bold=true`;

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
      case 'accepted': return { icon: <CheckCircle2 className="w-3.5 h-3.5" />, color: 'text-teal-700', bg: 'bg-teal-50', border: 'border-teal-200', label: 'Accepted' };
      case 'rejected': return { icon: <XCircle className="w-3.5 h-3.5" />, color: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-200', label: 'Rejected' };
      case 'reviewed': return { icon: <Search className="w-3.5 h-3.5" />, color: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200', label: 'Reviewed' };
      case 'technical interview': return { icon: <Clock className="w-3.5 h-3.5" />, color: 'text-purple-700', bg: 'bg-purple-50', border: 'border-purple-200', label: 'Tech Interview' };
      case 'final interview': return { icon: <Clock className="w-3.5 h-3.5" />, color: 'text-indigo-700', bg: 'bg-indigo-50', border: 'border-indigo-200', label: 'Final Interview' };
      case 'archived': return { icon: <Archive className="w-3.5 h-3.5" />, color: 'text-gray-700', bg: 'bg-gray-100', border: 'border-gray-200', label: 'Archived' };
      default: return { icon: <Clock className="w-3.5 h-3.5" />, color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Pending' };
    }
  };

  const statusInfo = getStatusInfo(candidate.status);
  const match = Math.round(candidate.matchScore || 0);

  const getMatchTheme = () => {
    if (match >= 80) return {
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200 ring-1 ring-emerald-500/20',
      dot: 'bg-emerald-500',
      ring: '#10b981'
    };
    if (match >= 60) return {
      badge: 'bg-amber-50 text-amber-700 border-amber-200 ring-1 ring-amber-500/20',
      dot: 'bg-amber-500',
      ring: '#f59e0b'
    };
    return {
      badge: 'bg-rose-50 text-rose-700 border-rose-200 ring-1 ring-rose-500/20',
      dot: 'bg-rose-500',
      ring: '#f43f5e'
    };
  };

  const matchTheme = getMatchTheme();

  return (
    <div className={`bg-white p-4 sm:p-5 md:p-6 rounded-2xl sm:rounded-3xl border transition-all duration-300 group ${
      isSelected 
        ? 'border-[#D60041] ring-2 ring-[#D60041]/10 shadow-md' 
        : 'border-gray-200/80 shadow-sm hover:shadow-md hover:border-gray-300'
    }`}>
      <div className="flex flex-col lg:flex-row gap-4 sm:gap-6 items-start lg:items-center">
        
        {/* Selection Checkbox & Avatar */}
        <div className="flex items-center gap-3 shrink-0">
          {onToggleSelect && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => onToggleSelect(candidate.id)}
              className="w-4 h-4 rounded border-gray-300 text-[#D60041] focus:ring-[#D60041] cursor-pointer"
              title="Select candidate"
            />
          )}

          <div className="relative shrink-0">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl overflow-hidden border-2 border-white shadow-sm bg-pink-50">
              <img
                src={avatarUrl}
                alt={candidate.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(candidate.name || 'Candidate')}&background=fdf2f8&color=d81159&bold=true`;
                }}
              />
            </div>
            <div className={`absolute -bottom-1 -right-1 p-1 rounded-lg border-2 border-white shadow-xs ${statusInfo.bg} ${statusInfo.color}`}>
              {statusInfo.icon}
            </div>
          </div>
        </div>

        {/* Content Section */}
        <div className="flex-grow w-full min-w-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <h3 
                  onClick={() => onOpenDetails(candidate)}
                  className="text-base sm:text-lg font-bold text-gray-900 tracking-tight hover:text-[#D60041] cursor-pointer transition-colors"
                >
                  {candidate.name}
                </h3>
                
                {/* Match Score Badge */}
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-[11px] font-black uppercase tracking-wider rounded-full border ${matchTheme.badge}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${matchTheme.dot}`}></span>
                  {match}% Match
                </span>

                {candidate.ai_powered && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gradient-to-r from-purple-50 to-pink-50 text-purple-700 border border-purple-100 text-[10px] font-bold uppercase tracking-wider rounded-md">
                    <Sparkles size={11} className="text-purple-600" />
                    AI Verified
                  </span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-y-1 gap-x-2 text-xs text-gray-500 font-semibold">
                <span className="flex items-center gap-1.5 text-gray-700 font-bold">
                  <span className="w-1.5 h-1.5 bg-[#D60041] rounded-full shrink-0"></span>
                  <span className="truncate">{candidate.preferredJob}</span>
                </span>
                {candidate.company && candidate.company !== 'N/A' && (
                  <span className="text-gray-400 font-normal">
                    • Prev: {candidate.company}
                  </span>
                )}
              </div>
            </div>

            {/* Mini Score Pillar Breakdown */}
            <div className="flex items-center gap-2 self-start sm:self-auto bg-gray-50/80 px-2.5 py-1.5 rounded-xl border border-gray-100 shrink-0">
              <div className="flex items-center gap-1 text-[10px] font-bold text-blue-700" title="Skills score (40% weight)">
                <Zap size={11} className="text-blue-500" />
                <span>{Math.round(candidate.skillsScore || 0)}%</span>
              </div>
              <span className="text-gray-300 text-xs">|</span>
              <div className="flex items-center gap-1 text-[10px] font-bold text-purple-700" title="Experience score (40% weight)">
                <Briefcase size={11} className="text-purple-500" />
                <span>{Math.round(candidate.experienceScore || 0)}%</span>
              </div>
              <span className="text-gray-300 text-xs">|</span>
              <div className="flex items-center gap-1 text-[10px] font-bold text-amber-700" title="Education score (20% weight)">
                <GraduationCap size={11} className="text-amber-500" />
                <span>{Math.round(candidate.educationScore || 0)}%</span>
              </div>
            </div>
          </div>

          {/* Skills Pills */}
          <div className="flex flex-wrap gap-1.5 mb-3">
            {(candidate.skills || []).slice(0, 5).map((skill, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSkillClick && onSkillClick(skill)}
                title={`Filter candidates by skill: ${skill}`}
                className="bg-gray-50 hover:bg-pink-50 text-gray-600 hover:text-[#D60041] border border-gray-200/80 hover:border-pink-200 text-[10px] font-semibold uppercase tracking-tight px-2 py-0.8 rounded-lg transition-all duration-150 cursor-pointer"
              >
                {skill}
              </button>
            ))}
            {(candidate.skills || []).length > 5 && (
              <span className="bg-gray-50 text-gray-400 text-[10px] font-semibold px-1.5 py-0.8 rounded-lg border border-gray-200/70">
                +{candidate.skills.length - 5}
              </span>
            )}
          </div>

          {/* Meta Info & Quick Contact */}
          <div className="flex flex-wrap items-center gap-y-1.5 gap-x-4 pt-2.5 border-t border-gray-100 text-[11px] text-gray-500 font-medium">
            <div className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-gray-400 shrink-0" />
              <span>Applied {formatDate(candidate.date)}</span>
            </div>
            
            <div className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-gray-400 shrink-0" />
              <span className="truncate max-w-[140px]">{candidate.location || "N/A"}</span>
            </div>

            {candidate.email && candidate.email !== 'N/A' && (
              <div className="flex items-center gap-1 text-gray-600">
                <Mail className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                <span className="truncate max-w-[150px] sm:max-w-[180px]">{candidate.email}</span>
                <button
                  type="button"
                  onClick={() => handleCopy(candidate.email, 'email')}
                  title="Copy email"
                  className="hover:text-gray-900 transition-colors p-0.5 cursor-pointer"
                >
                  {copiedField === 'email' ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
                </button>
              </div>
            )}

            {candidate.phone && candidate.phone !== 'N/A' && (
              <div className="flex items-center gap-1 text-gray-600">
                <Phone className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                <a href={`tel:${candidate.phone}`} className="hover:text-[#D60041] transition-colors">
                  {candidate.phone}
                </a>
                <button
                  type="button"
                  onClick={() => handleCopy(candidate.phone, 'phone')}
                  title="Copy phone"
                  className="hover:text-gray-900 transition-colors p-0.5 cursor-pointer"
                >
                  {copiedField === 'phone' ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Action Section - Responsive Two-tier on mobile, inline on desktop */}
        <div className="w-full lg:w-auto shrink-0 pt-3 lg:pt-0 border-t lg:border-t-0 border-gray-100 flex flex-col sm:flex-row lg:flex-row items-stretch sm:items-center gap-2">
          
          {/* Row 1 on mobile: Status Dropdown + Quick Icon Actions */}
          <div className="flex items-center gap-2">
            {/* Direct Resume View/Download */}
            {candidate.resumeUrl && (
              <button
                type="button"
                onClick={() => {
                  const fullUrl = getAssetUrl(candidate.resumeUrl);
                  window.open(fullUrl, '_blank');
                }}
                title="View / Download Resume"
                className="p-2 sm:p-2.5 bg-gray-50 border border-gray-200 text-gray-600 hover:bg-pink-50 hover:border-pink-200 hover:text-[#D60041] rounded-xl transition-all cursor-pointer shadow-xs hover:shadow-sm"
              >
                <FileText size={15} />
              </button>
            )}

            {/* Archive or Restore Button */}
            {isArchived ? (
              <button
                type="button"
                onClick={() => onRestoreApplication ? onRestoreApplication(candidate.id) : onUpdateStatus(candidate.id, 'Pending')}
                title="Restore Application"
                className="p-2 sm:p-2.5 bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-100 hover:border-emerald-300 rounded-xl transition-all cursor-pointer shadow-xs hover:shadow-sm"
              >
                <RotateCcw size={15} />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onArchiveApplication(candidate.id)}
                title="Archive Candidate"
                className="p-2 sm:p-2.5 bg-gray-50 border border-gray-200 text-gray-500 hover:bg-amber-50 hover:border-amber-200 hover:text-amber-700 rounded-xl transition-all cursor-pointer shadow-xs hover:shadow-sm"
              >
                <Archive size={15} />
              </button>
            )}

            {/* Remove / Delete Button */}
            <button
              type="button"
              onClick={() => onDeleteApplication(candidate.id)}
              title="Remove Candidate Application"
              className="p-2 sm:p-2.5 bg-gray-50 border border-gray-200 text-gray-500 hover:bg-rose-50 hover:border-rose-200 hover:text-rose-700 rounded-xl transition-all cursor-pointer shadow-xs hover:shadow-sm"
            >
              <Trash2 size={15} />
            </button>

            {/* Status Dropdown */}
            <div className="relative flex-1 sm:flex-none sm:min-w-[130px]" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                disabled={isUpdating}
                className={`w-full flex items-center justify-between gap-1.5 py-2 px-2.5 rounded-xl border text-[11px] font-bold uppercase tracking-wider transition-all cursor-pointer ${statusInfo.bg} ${statusInfo.color} ${statusInfo.border} hover:brightness-95 hover:shadow-xs ${isUpdating ? 'opacity-50 animate-pulse' : ''}`}
              >
                <div className="flex items-center gap-1.5 truncate">
                  {statusInfo.icon}
                  <span className="truncate">{statusInfo.label}</span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 shrink-0 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              {isDropdownOpen && (
                <div className="absolute top-full right-0 mt-1.5 w-48 bg-white border border-gray-100 rounded-2xl shadow-xl z-50 py-1.5 animate-in fade-in slide-in-from-top-1 duration-150">
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
                          setTimeout(() => setIsUpdating(false), 500);
                        }}
                        className={`w-full flex items-center justify-between px-3.5 py-2 text-[11px] font-bold uppercase tracking-wider transition-colors cursor-pointer ${
                          isCurrent ? info.bg + ' ' + info.color : 'text-gray-600 hover:bg-pink-50 hover:text-[#D60041]'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className={info.color}>{info.icon}</span>
                          <span>{s}</span>
                        </div>
                        {isCurrent && <Check className="w-3.5 h-3.5" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Row 2 on mobile: Details & Schedule Buttons */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onOpenDetails(candidate)}
              className="flex-1 sm:flex-none px-3.5 sm:px-4 py-2 bg-gray-50 hover:bg-pink-50 text-gray-700 hover:text-[#D60041] rounded-xl text-xs font-bold transition-all border border-gray-200 hover:border-pink-200 text-center cursor-pointer shadow-xs hover:shadow-sm"
            >
              Details
            </button>
            <button
              type="button"
              onClick={() => onOpenInterview(candidate)}
              className="flex-1 sm:flex-none px-3.5 sm:px-4 py-2 bg-[#D60041] hover:bg-[#B50037] text-white rounded-xl text-xs font-bold transition-all shadow-xs hover:shadow-md hover:shadow-pink-500/25 active:scale-[0.98] text-center cursor-pointer whitespace-nowrap"
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
