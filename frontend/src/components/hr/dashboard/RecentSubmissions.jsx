import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Users, ArrowRight, User, Search, Filter, 
  Eye, Calendar, CheckCircle2, Clock, Sparkles, 
  ExternalLink, ChevronRight, X, Briefcase, MapPin, Award
} from 'lucide-react';
import { getAssetUrl } from '../../../services/api';
import ViewCandidateDetailsModal from '../../modals/hr/ViewCandidateDetailsModal';
import ScheduleInterviewModal from '../../modals/hr/ScheduleInterviewModal';

const CandidateCard = ({ 
  candidate, 
  onQuickView, 
  onSchedule, 
  onScreen 
}) => {
  const { name, preferredJob, skills, matchScore, status, profileImage, date } = candidate;

  const statusStyles = {
    pending: "bg-amber-50 text-amber-700 border-amber-200/80",
    reviewed: "bg-blue-50 text-blue-700 border-blue-200/80",
    accepted: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
    rejected: "bg-rose-50 text-rose-700 border-rose-200/80",
    archived: "bg-slate-100 text-slate-600 border-slate-200"
  };

  const statusDot = {
    pending: "bg-amber-500",
    reviewed: "bg-blue-500",
    accepted: "bg-emerald-500",
    rejected: "bg-rose-500",
    archived: "bg-slate-400"
  };

  const skillsList = Array.isArray(skills)
    ? skills
    : (typeof skills === 'string' ? skills.split(',').map(s => s.trim()) : []);

  const score = matchScore || 0;
  const scoreBadgeColor = score >= 80 
    ? "from-emerald-500 to-teal-600 text-white shadow-emerald-500/20"
    : score >= 60
    ? "from-amber-500 to-orange-500 text-white shadow-amber-500/20"
    : "from-slate-400 to-slate-500 text-white shadow-slate-400/20";

  const formattedDate = date 
    ? new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : 'Recent';

  return (
    <div className="flex flex-col lg:flex-row lg:items-center justify-between p-4 sm:p-4.5 bg-white border border-slate-200/80 rounded-2xl hover:border-pink-200/90 hover:shadow-lg transition-all duration-200 group gap-4">
      {/* Left: Avatar & Info */}
      <div className="flex items-center gap-3.5 min-w-0 lg:w-[35%]">
        <div className="relative shrink-0">
          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-2xl bg-pink-50 border border-pink-100/80 flex items-center justify-center overflow-hidden group-hover:scale-105 transition-transform duration-200 shadow-inner">
            {profileImage ? (
              <img src={getAssetUrl(profileImage)} alt={name} className="w-full h-full object-cover" />
            ) : (
              <span className="text-base font-black text-[#D60041]">
                {(name || 'C').charAt(0).toUpperCase()}
              </span>
            )}
          </div>
          <span className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white ${statusDot[status?.toLowerCase()] || 'bg-amber-400'}`} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h4 className="font-extrabold text-sm sm:text-[15px] text-slate-900 truncate group-hover:text-[#D60041] transition-colors">
              {name || 'Candidate'}
            </h4>
            <span className="hidden sm:inline-block text-[10px] font-bold text-slate-400 bg-slate-50 border border-slate-100 px-1.5 py-0.5 rounded-md">
              {formattedDate}
            </span>
          </div>
          <p className="text-xs text-slate-500 font-semibold truncate mt-0.5">
            {preferredJob || 'General Applicant'}
          </p>
        </div>
      </div>

      {/* Middle: Skills & Experience */}
      <div className="hidden md:flex items-center gap-1.5 flex-wrap lg:w-[30%]">
        {skillsList.slice(0, 3).map((skill, i) => (
          <span 
            key={i} 
            className="px-2.5 py-1 bg-slate-50/80 hover:bg-slate-100 rounded-lg text-[10px] font-bold text-slate-600 border border-slate-100/90 whitespace-nowrap transition-colors"
          >
            {skill}
          </span>
        ))}
        {skillsList.length > 3 && (
          <span className="px-2 py-1 bg-slate-50 rounded-lg text-[10px] font-bold text-slate-400 border border-slate-100">
            +{skillsList.length - 3}
          </span>
        )}
      </div>

      {/* Right: ATS Match Score, Status & Actions */}
      <div className="flex items-center justify-between lg:justify-end gap-3 sm:gap-4 pt-3 lg:pt-0 border-t lg:border-t-0 border-slate-100">
        {/* Match Score Badge */}
        <div className="flex items-center gap-2">
          <div className={`px-2.5 py-1 rounded-xl bg-gradient-to-br ${scoreBadgeColor} text-center shadow-xs`}>
            <span className="text-xs sm:text-sm font-black leading-none">{score}%</span>
          </div>
          <div className="hidden sm:flex flex-col">
            <span className="text-[9px] font-black uppercase tracking-wider text-slate-400">ATS Match</span>
            <span className="text-[10px] font-bold text-slate-600">
              {score >= 80 ? 'High Match' : score >= 60 ? 'Moderate' : 'Basic'}
            </span>
          </div>
        </div>

        {/* Status Pill */}
        <span className={`px-2.5 sm:px-3 py-1 rounded-xl text-[10px] font-black uppercase tracking-wider border ${statusStyles[status?.toLowerCase()] || statusStyles.pending}`}>
          {status || 'Pending'}
        </span>

        {/* Quick Actions */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => onQuickView(candidate)}
            className="p-2 bg-slate-50 hover:bg-slate-100 hover:text-slate-900 text-slate-500 rounded-xl transition-colors"
            title="Inspect Candidate ATS Analysis"
          >
            <Eye size={15} />
          </button>

          <button
            onClick={() => onSchedule(candidate)}
            className="p-2 bg-slate-50 hover:bg-pink-50 hover:text-[#D60041] text-slate-500 rounded-xl transition-colors"
            title="Schedule Candidate Interview"
          >
            <Calendar size={15} />
          </button>

          <button
            onClick={() => onScreen(candidate)}
            className="px-3 sm:px-4 py-2 bg-slate-900 hover:bg-[#D60041] text-white rounded-xl text-[11px] font-black uppercase tracking-wider transition-all shadow-xs active:scale-95 flex items-center gap-1"
          >
            <span>Screen</span>
            <ChevronRight size={13} />
          </button>
        </div>
      </div>
    </div>
  );
};

const RecentSubmissions = ({ candidates = [] }) => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('ALL'); // 'ALL' | 'PENDING' | 'REVIEWED' | 'HIGH_MATCH'
  const [modalCandidate, setModalCandidate] = useState(null);
  const [scheduleCandidate, setScheduleCandidate] = useState(null);

  // Filter candidates based on search & tab
  const filteredCandidates = useMemo(() => {
    return candidates.filter(can => {
      const name = (can.name || '').toLowerCase();
      const role = (can.preferredJob || '').toLowerCase();
      const skillsStr = Array.isArray(can.skills) 
        ? can.skills.join(' ').toLowerCase() 
        : String(can.skills || '').toLowerCase();
      const search = searchTerm.toLowerCase().trim();

      const matchesSearch = !search || name.includes(search) || role.includes(search) || skillsStr.includes(search);

      if (!matchesSearch) return false;

      if (selectedFilter === 'HIGH_MATCH') return (can.matchScore || 0) >= 80;
      if (selectedFilter === 'PENDING') return (can.status || '').toUpperCase() === 'PENDING';
      if (selectedFilter === 'REVIEWED') return (can.status || '').toUpperCase() === 'REVIEWED';
      if (selectedFilter === 'ACCEPTED') return (can.status || '').toUpperCase() === 'ACCEPTED';
      return true;
    });
  }, [candidates, searchTerm, selectedFilter]);

  const displayedList = filteredCandidates.slice(0, 6);

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl shadow-xs p-5 sm:p-6 lg:p-7 mb-6 sm:mb-8">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center pb-5 mb-5 border-b border-slate-100 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg md:text-xl font-extrabold text-slate-900 tracking-tight">
              Recent Submissions
            </h3>
            <span className="text-[10px] font-black px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
              {candidates.length} Total
            </span>
          </div>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            Review incoming candidate applications with automated resume match scoring
          </p>
        </div>

        <button 
          onClick={() => navigate('/hr/screeningportal')} 
          className="group inline-flex items-center gap-1.5 text-xs font-bold text-[#D60041] hover:text-[#b50037] transition-colors"
        >
          <span>Open Full Screening Queue</span>
          <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mb-5">
        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search candidate, role, skill..."
            className="w-full pl-9 pr-8 py-2 bg-slate-50 border border-slate-200/80 rounded-xl text-xs text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X size={13} />
            </button>
          )}
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto scrollbar-hide py-1">
          {[
            { id: 'ALL', label: 'All' },
            { id: 'HIGH_MATCH', label: 'High Match (≥80%)' },
            { id: 'PENDING', label: 'Pending' },
            { id: 'REVIEWED', label: 'Screened' },
            { id: 'ACCEPTED', label: 'Accepted' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setSelectedFilter(tab.id)}
              className={`px-3 py-1.5 rounded-xl text-[11px] font-bold whitespace-nowrap transition-all ${
                selectedFilter === tab.id
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-50 text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Candidate List */}
      {displayedList.length === 0 ? (
        <div className="py-12 text-center flex flex-col items-center justify-center bg-slate-50/50 rounded-2xl border border-slate-100">
          <div className="w-12 h-12 rounded-2xl bg-white border border-slate-200 flex items-center justify-center text-slate-400 mb-3 shadow-inner">
            <Users size={22} />
          </div>
          <h4 className="text-sm font-bold text-slate-800">No applicants found</h4>
          <p className="text-xs text-slate-500 mt-1 max-w-xs">
            {searchTerm ? `No submissions matching "${searchTerm}"` : 'No candidates in this filter category.'}
          </p>
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="mt-3 text-xs font-bold text-[#D60041] hover:underline"
            >
              Clear search filter
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2.5">
          {displayedList.map((can) => (
            <CandidateCard
              key={can.id}
              candidate={can}
              onQuickView={(candidate) => setModalCandidate(candidate)}
              onSchedule={(candidate) => setScheduleCandidate(candidate)}
              onScreen={(candidate) => navigate(`/hr/screeningportal?candidateId=${candidate.id}`)}
            />
          ))}
        </div>
      )}

      {/* Footer view all link */}
      {filteredCandidates.length > 6 && (
        <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 font-medium">
          <span>Showing 6 of {filteredCandidates.length} filtered applicants</span>
          <button
            onClick={() => navigate('/hr/screeningportal')}
            className="font-bold text-[#D60041] hover:underline flex items-center gap-1"
          >
            <span>View all in Screening Portal</span>
            <ChevronRight size={14} />
          </button>
        </div>
      )}

      {/* Candidate Inspection Modal */}
      {modalCandidate && (
        <ViewCandidateDetailsModal
          candidate={modalCandidate}
          isOpen={!!modalCandidate}
          onClose={() => setModalCandidate(null)}
          onScheduleInterview={(candidate) => {
            setModalCandidate(null);
            setScheduleCandidate(candidate);
          }}
        />
      )}

      {/* Schedule Interview Modal */}
      {scheduleCandidate && (
        <ScheduleInterviewModal
          candidate={scheduleCandidate}
          isOpen={!!scheduleCandidate}
          onClose={() => setScheduleCandidate(null)}
        />
      )}
    </div>
  );
};

export default RecentSubmissions;
