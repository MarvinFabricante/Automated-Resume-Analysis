import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from '@/utils/navigation';
import {
  Users, ArrowRight, Search,
  Eye, Calendar, CheckCircle2, Clock, Sparkles,
  ChevronRight, X, Briefcase, MapPin, Award,
  Filter, ArrowUpDown, RotateCcw
} from 'lucide-react';
import { getAssetUrl } from '../../../services/api';
import {
  getCandidatePosition,
  matchesPositionFilter,
  sortCandidatesByOption,
} from '../../../utils/hrAnalytics';
import ViewCandidateDetailsModal from '../../modals/hr/ViewCandidateDetailsModal';
import NewScheduleModal from '../../modals/hr/NewScheduleModal';

export interface RecentCandidate {
  id?: string | number;
  name?: string;
  candidate_name?: string;
  preferredJob?: string;
  job_title?: string;
  jobDepartment?: string;
  jobLocation?: string;
  location?: string;
  skills?: string[] | string;
  matchScore?: number;
  match_score?: number;
  status?: string;
  profileImage?: string;
  profile_image_url?: string;
  date?: string;
  created_at?: string;
  candidate_email?: string;
  email?: string;
  [key: string]: any;
}

interface CandidateCardProps {
  candidate: RecentCandidate;
  onQuickView: (candidate: RecentCandidate) => void;
  onSchedule: (candidate: RecentCandidate) => void;
  onScreen: (candidate: RecentCandidate) => void;
}

const getRelativeTime = (dStr?: string) => {
  if (!dStr) return 'Recently';
  try {
    const d = new Date(dStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    if (diffMs < 0) return 'Just now';
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHrs / 24);

    if (diffMins < 5) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHrs < 24) return `${diffHrs}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return 'Recently';
  }
};

const getStatusInfo = (rawStatus?: string) => {
  const s = (rawStatus || '').toUpperCase().trim();
  if (s === 'PENDING') {
    return {
      label: 'Pending Review',
      badgeClass: 'bg-amber-50 text-amber-700 border-amber-200/90',
      dotClass: 'bg-amber-500'
    };
  }
  if (s === 'REVIEWED') {
    return {
      label: 'Screened',
      badgeClass: 'bg-blue-50 text-blue-700 border-blue-200/90',
      dotClass: 'bg-blue-500'
    };
  }
  if (s.includes('TECHNICAL') || s.includes('INTERVIEW')) {
    return {
      label: s === 'FINAL INTERVIEW' ? 'Final Interview' : 'Tech Interview',
      badgeClass: 'bg-purple-50 text-purple-700 border-purple-200/90',
      dotClass: 'bg-purple-500'
    };
  }
  if (s === 'ACCEPTED') {
    return {
      label: 'Accepted',
      badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200/90',
      dotClass: 'bg-emerald-500'
    };
  }
  if (s === 'REJECTED') {
    return {
      label: 'Not Selected',
      badgeClass: 'bg-rose-50 text-rose-700 border-rose-200/90',
      dotClass: 'bg-rose-500'
    };
  }
  if (s === 'ARCHIVED') {
    return {
      label: 'Archived',
      badgeClass: 'bg-slate-100 text-slate-600 border-slate-200',
      dotClass: 'bg-slate-400'
    };
  }
  return {
    label: rawStatus || 'Pending',
    badgeClass: 'bg-slate-50 text-slate-700 border-slate-200',
    dotClass: 'bg-slate-400'
  };
};

const CandidateCard: React.FC<CandidateCardProps> = ({
  candidate,
  onQuickView,
  onSchedule,
  onScreen
}) => {
  const name = candidate.candidate_name || candidate.name || 'Candidate';
  const preferredJob = candidate.job_title || candidate.preferredJob || 'Applicant';
  const department = candidate.jobDepartment || candidate.job?.department;
  const location = candidate.jobLocation || candidate.location;
  const skills = candidate.skills;
  const score = Math.round(candidate.match_score ?? candidate.matchScore ?? 0);
  const status = candidate.status;
  const profileImage = candidate.profileImage || candidate.profile_image_url;
  const dateStr = candidate.date || candidate.created_at;

  const statusInfo = getStatusInfo(status);

  const skillsList = Array.isArray(skills)
    ? skills
    : (typeof skills === 'string' ? skills.split(',').map((s: string) => s.trim()) : []);

  const scoreStyles = score >= 80
    ? 'bg-emerald-50 text-emerald-700 border-emerald-200/90'
    : score >= 60
      ? 'bg-amber-50 text-amber-700 border-amber-200/90'
      : 'bg-slate-50 text-slate-600 border-slate-200/90';

  const scoreTierText = score >= 80
    ? 'High Match'
    : score >= 60
      ? 'Moderate Fit'
      : 'Basic Fit';

  return (
    <div className="flex flex-col p-4 sm:p-5 bg-white border border-slate-200/90 rounded-2xl hover:border-rose-200/90 hover:shadow-md transition-all duration-200 group gap-3.5">
      {/* Top: Avatar & Candidate Identity + Status Badge */}
      <div className="flex items-start justify-between gap-3 min-w-0">
        <div className="flex items-start gap-3.5 min-w-0 flex-1">
          <div className="relative shrink-0 mt-0.5">
            <div className="w-12 h-12 rounded-2xl bg-rose-50/80 border border-rose-100 flex items-center justify-center overflow-hidden group-hover:scale-105 transition-transform duration-200 shadow-inner">
              {profileImage ? (
                <img src={getAssetUrl(profileImage)} alt={name} className="w-full h-full object-cover" />
              ) : (
                <span className="text-base font-black text-[#D60041]">
                  {name.charAt(0).toUpperCase()}
                </span>
              )}
            </div>
            <span
              className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white ${statusInfo.dotClass}`}
              title={`Status: ${statusInfo.label}`}
            />
          </div>

          <div className="min-w-0 flex-1">
            {/* Name & Time row */}
            <div className="flex items-center gap-2 flex-wrap min-w-0">
              <h4 className="font-extrabold text-sm sm:text-base text-slate-900 truncate group-hover:text-[#D60041] transition-colors">
                {name}
              </h4>
              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-500 bg-slate-50 border border-slate-200/70 px-2 py-0.5 rounded-md shrink-0">
                <Clock size={10} className="text-slate-400" />
                <span>{getRelativeTime(dateStr)}</span>
              </span>
            </div>

            {/* Role & Context Row */}
            <div className="flex items-center gap-2 text-xs text-slate-600 font-semibold mt-1 flex-wrap">
              <span className="text-slate-800 font-bold flex items-center gap-1.5 truncate max-w-[240px]">
                <Briefcase size={12} className="text-slate-400 shrink-0" />
                <span className="truncate">{preferredJob}</span>
              </span>
              {department && department !== 'N/A' && (
                <span className="text-slate-400 text-[11px] font-medium hidden sm:inline">
                  • {department}
                </span>
              )}
              {location && location !== 'N/A' && (
                <span className="inline-flex items-center gap-1 text-[11px] text-slate-400 font-normal">
                  <MapPin size={11} className="shrink-0" />
                  <span className="truncate max-w-[150px]">{location}</span>
                </span>
              )}
            </div>

            {/* Skills Tags */}
            {skillsList.length > 0 && (
              <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                {skillsList.slice(0, 4).map((skill: string, i: number) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 bg-slate-50 hover:bg-slate-100 rounded-md text-[10px] font-bold text-slate-600 border border-slate-200/60 truncate max-w-[140px] transition-colors"
                  >
                    {skill}
                  </span>
                ))}
                {skillsList.length > 4 && (
                  <span className="px-1.5 py-0.5 bg-slate-100 rounded-md text-[10px] font-black text-slate-400">
                    +{skillsList.length - 4}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Status Badge */}
        <span className={`inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-xl text-[10.5px] font-black uppercase tracking-wider border shrink-0 ${statusInfo.badgeClass}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${statusInfo.dotClass}`} />
          <span>{statusInfo.label}</span>
        </span>
      </div>

      {/* Bottom: Score & Actions */}
      <div className="flex items-center justify-between gap-3 pt-3 border-t border-slate-100 w-full flex-wrap sm:flex-nowrap">
        {/* ATS Score & Match Label */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className={`px-2.5 py-1.5 rounded-xl border flex items-center gap-1.5 shadow-2xs font-black text-xs sm:text-sm shrink-0 ${scoreStyles}`}>
            {score >= 80 ? (
              <Sparkles size={13} className="text-emerald-500 shrink-0" />
            ) : (
              <Award size={13} className="text-slate-400 shrink-0" />
            )}
            <span>{score}%</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[9px] font-black uppercase tracking-wider text-slate-400 leading-none">ATS Match</span>
            <span className="text-[10.5px] font-bold text-slate-700 mt-0.5 whitespace-nowrap">
              {scoreTierText}
            </span>
          </div>
        </div>

        {/* Quick Action Buttons */}
        <div className="flex items-center gap-2 shrink-0 ml-auto">
          {/* Inspect Button */}
          <button
            type="button"
            onClick={() => onQuickView(candidate)}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200/80 rounded-xl text-xs font-bold transition-all active:scale-95 cursor-pointer shadow-2xs"
            title="Inspect candidate resume & ATS score breakdown"
          >
            <Eye size={14} className="text-slate-500" />
            <span>Inspect</span>
          </button>

          {/* Schedule Interview Button */}
          <button
            type="button"
            onClick={() => onSchedule(candidate)}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-rose-50 hover:bg-rose-100 text-[#D60041] border border-rose-200/90 rounded-xl text-xs font-bold transition-all active:scale-95 cursor-pointer shadow-2xs"
            title="Schedule interview session for this candidate"
          >
            <Calendar size={14} className="text-[#D60041]" />
            <span>Schedule</span>
          </button>

          {/* Screen Button */}
          <button
            type="button"
            onClick={() => onScreen(candidate)}
            className="inline-flex items-center justify-center gap-1 px-3.5 sm:px-4 py-2 bg-slate-900 hover:bg-[#D60041] text-white rounded-xl text-xs font-black uppercase tracking-wider transition-all shadow-xs active:scale-95 cursor-pointer"
            title="Open candidate in Screening Portal"
          >
            <span>Screen</span>
            <ChevronRight size={13} />
          </button>
        </div>
      </div>
    </div>
  );
};

interface RecentSubmissionsProps {
  candidates?: RecentCandidate[];
}

const RecentSubmissions: React.FC<RecentSubmissionsProps> = ({ candidates = [] }) => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedFilter, setSelectedFilter] = useState<string>('ALL'); // 'ALL' | 'PENDING' | 'REVIEWED' | 'HIGH_MATCH' | 'ACCEPTED'
  const [positionFilter, setPositionFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<string>('date_desc');
  const [showAllFiltered, setShowAllFiltered] = useState<boolean>(false);
  const [visibleLimit, setVisibleLimit] = useState<number>(20);
  const [modalCandidate, setModalCandidate] = useState<RecentCandidate | null>(null);
  const [scheduleCandidate, setScheduleCandidate] = useState<RecentCandidate | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  useEffect(() => {
    setVisibleLimit(20);
  }, [positionFilter, selectedFilter, searchTerm, sortBy]);

  // Single-pass index + category counts so 500+ applicants never trigger repeated full scans
  const {
    indexedCandidates,
    positionOptions,
    highMatchCount,
    pendingCount,
    reviewedCount,
    acceptedCount,
  } = useMemo(() => {
    const posCounts = new Map<string, number>();
    let highMatch = 0;
    let pending = 0;
    let reviewed = 0;
    let accepted = 0;

    const indexed = candidates.map((can) => {
      const pos = getCandidatePosition(can);
      if (pos) posCounts.set(pos, (posCounts.get(pos) || 0) + 1);

      const score = Number(can.match_score ?? can.matchScore ?? 0) || 0;
      const status = String(can.status || '').toUpperCase();
      if (score >= 80) highMatch += 1;
      if (status === 'PENDING') pending += 1;
      else if (status === 'REVIEWED') reviewed += 1;
      else if (status === 'ACCEPTED') accepted += 1;

      const skillsText = Array.isArray(can.skills)
        ? can.skills.join(' ')
        : String(can.skills || '');
      const haystack = `${can.candidate_name || can.name || ''} ${can.job_title || can.preferredJob || ''} ${can.jobDepartment || can.job?.department || ''} ${skillsText}`.toLowerCase();

      return { can, score, status, haystack };
    });

    const opts = Array.from(posCounts.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([title, count]) => ({ title, count }));

    return {
      indexedCandidates: indexed,
      positionOptions: opts,
      highMatchCount: highMatch,
      pendingCount: pending,
      reviewedCount: reviewed,
      acceptedCount: accepted,
    };
  }, [candidates]);

  // Filter by position/search/status and sort deterministically by score or date
  const filteredCandidates = useMemo(() => {
    const search = searchTerm.toLowerCase().trim();
    const filtered: RecentCandidate[] = [];

    for (const entry of indexedCandidates) {
      if (!matchesPositionFilter(entry.can, positionFilter)) continue;
      if (search && !entry.haystack.includes(search)) continue;
      if (selectedFilter === 'HIGH_MATCH' && entry.score < 80) continue;
      if (selectedFilter === 'PENDING' && entry.status !== 'PENDING') continue;
      if (selectedFilter === 'REVIEWED' && entry.status !== 'REVIEWED') continue;
      if (selectedFilter === 'ACCEPTED' && entry.status !== 'ACCEPTED') continue;
      filtered.push(entry.can);
    }

    return sortCandidatesByOption(filtered, sortBy);
  }, [indexedCandidates, positionFilter, searchTerm, selectedFilter, sortBy]);

  const hasActiveControls =
    positionFilter !== 'ALL' ||
    selectedFilter !== 'ALL' ||
    Boolean(searchTerm.trim()) ||
    sortBy !== 'date_desc';

  const displayedList =
    hasActiveControls || showAllFiltered
      ? filteredCandidates.slice(0, visibleLimit)
      : filteredCandidates.slice(0, 6);

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl shadow-xs p-4 sm:p-6 lg:p-7 mb-6 sm:mb-8 relative">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-8 right-8 bg-slate-900 text-white px-5 py-3.5 rounded-2xl shadow-2xl flex items-center gap-3 text-xs font-bold z-50 border border-slate-800 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <CheckCircle2 size={16} className="text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-4 mb-4 sm:pb-5 sm:mb-5 border-b border-slate-100 gap-3 sm:gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h3 className="text-base sm:text-lg md:text-xl font-extrabold text-slate-900 tracking-tight">
              Recent Submissions
            </h3>
            <span className="text-[10px] font-black px-2.5 py-0.5 rounded-full bg-rose-50 text-[#D60041] border border-rose-100/90">
              {candidates.length} Total
            </span>
          </div>
          <p className="text-[11px] sm:text-xs text-slate-500 font-medium mt-0.5">
            Incoming candidate applications evaluated by Mariwasa automated ATS matching
          </p>
        </div>

        <button
          onClick={() => navigate('/hr/screeningportal')}
          className="group inline-flex items-center gap-1.5 text-xs font-bold text-[#D60041] hover:text-[#b50037] transition-colors cursor-pointer"
        >
          <span>Open Full Screening Queue</span>
          <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
        </button>
      </div>

      {/* Filter, Position, Sort, and Search Controls */}
      <div className="flex flex-col gap-3 mb-5">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-2.5">
          {/* Search Input */}
          <div className="relative w-full lg:w-72">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search candidate, role, skill..."
              className="w-full pl-9 pr-8 py-2.5 bg-slate-50 border border-slate-200/80 rounded-xl text-xs text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1"
              >
                <X size={13} />
              </button>
            )}
          </div>

          {/* Position Filter & Score/Date Sort Dropdowns */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative flex-1 sm:flex-none min-w-[175px]">
              <Filter size={13} className={`absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none ${positionFilter !== 'ALL' ? 'text-[#D60041]' : 'text-slate-400'}`} />
              <select
                data-testid="dashboard-position-filter"
                aria-label="Filter by position"
                value={positionFilter}
                onChange={(e) => setPositionFilter(e.target.value)}
                className={`w-full pl-8 pr-7 py-2.5 border rounded-xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 cursor-pointer transition-all ${positionFilter !== 'ALL'
                    ? 'bg-pink-50/70 border-pink-200 text-[#D60041]'
                    : 'bg-slate-50 border-slate-200/80 text-slate-700'
                  }`}
              >
                <option value="ALL">All Positions ({candidates.length})</option>
                {positionOptions.map((opt) => (
                  <option key={opt.title} value={opt.title}>
                    {opt.title} ({opt.count})
                  </option>
                ))}
              </select>
            </div>

            <div className="relative flex-1 sm:flex-none min-w-[180px]">
              <ArrowUpDown size={13} className={`absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none ${sortBy !== 'date_desc' ? 'text-purple-600' : 'text-slate-400'}`} />
              <select
                data-testid="dashboard-sort-select"
                aria-label="Sort submissions"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className={`w-full pl-8 pr-7 py-2.5 border rounded-xl text-xs font-bold focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 cursor-pointer transition-all ${sortBy !== 'date_desc'
                    ? 'bg-purple-50/70 border-purple-200 text-purple-800'
                    : 'bg-slate-50 border-slate-200/80 text-slate-700'
                  }`}
              >
                <option value="date_desc">Sort: Date (Newest)</option>
                <option value="date_asc">Sort: Date (Oldest)</option>
                <option value="match_desc">Sort: Score (High to Low)</option>
                <option value="match_asc">Sort: Score (Low to High)</option>
              </select>
            </div>

            {hasActiveControls && (
              <button
                type="button"
                onClick={() => {
                  setPositionFilter('ALL');
                  setSelectedFilter('ALL');
                  setSearchTerm('');
                  setSortBy('date_desc');
                }}
                className="inline-flex items-center gap-1 px-2.5 py-2 rounded-xl text-xs font-bold text-[#D60041] hover:bg-rose-50 transition-colors cursor-pointer"
                title="Reset filters and sorting"
              >
                <RotateCcw size={12} />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* Filter Pills with real-time counts */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full scrollbar-hide py-1">
          {[
            { id: 'ALL', label: 'All', count: candidates.length },
            { id: 'HIGH_MATCH', label: '≥80% Match', count: highMatchCount },
            { id: 'PENDING', label: 'Pending', count: pendingCount },
            { id: 'REVIEWED', label: 'Screened', count: reviewedCount },
            { id: 'ACCEPTED', label: 'Accepted', count: acceptedCount },
          ].map(tab => {
            const isActive = selectedFilter === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setSelectedFilter(tab.id)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${isActive
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-slate-50 text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
              >
                <span>{tab.label}</span>
                <span className={`text-[10px] font-black px-1.5 py-0.2 rounded-md ${isActive ? 'bg-slate-800 text-rose-300' : 'bg-slate-200/80 text-slate-600'
                  }`}>
                  {tab.count}
                </span>
              </button>
            );
          })}
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
              className="mt-3 text-xs font-bold text-[#D60041] hover:underline cursor-pointer"
            >
              Clear search filter
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
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

      {/* Footer pagination & view all link */}
      {filteredCandidates.length > 6 && (
        <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 font-medium">
          <span>
            Showing {displayedList.length} of {filteredCandidates.length} applicants
          </span>
          <div className="flex flex-wrap items-center gap-4">
            {displayedList.length < filteredCandidates.length && (
              <button
                type="button"
                onClick={() => {
                  if (!hasActiveControls && !showAllFiltered) {
                    setShowAllFiltered(true);
                    setVisibleLimit(20);
                  } else {
                    setVisibleLimit((prev) => prev + 20);
                  }
                }}
                className="font-bold text-slate-700 hover:text-[#D60041] cursor-pointer"
              >
                {!hasActiveControls && !showAllFiltered
                  ? `Show more (${Math.min(20, filteredCandidates.length)} of ${filteredCandidates.length})`
                  : `Load more (+${Math.min(20, filteredCandidates.length - displayedList.length)})`}
              </button>
            )}
            {(showAllFiltered || displayedList.length > 6) && !hasActiveControls && (
              <button
                type="button"
                onClick={() => {
                  setShowAllFiltered(false);
                  setVisibleLimit(20);
                }}
                className="font-bold text-slate-500 hover:text-slate-900 cursor-pointer"
              >
                Show compact (6)
              </button>
            )}
            <button
              onClick={() => navigate('/hr/screeningportal')}
              className="font-bold text-[#D60041] hover:underline flex items-center gap-1 cursor-pointer"
            >
              <span>View all in Screening Portal</span>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Candidate Inspection Modal */}
      {modalCandidate && (
        <ViewCandidateDetailsModal
          candidate={modalCandidate}
          isOpen={!!modalCandidate}
          onClose={() => setModalCandidate(null)}
          onScheduleInterview={(candidate: RecentCandidate) => {
            setModalCandidate(null);
            setScheduleCandidate(candidate);
          }}
        />
      )}

      {/* Schedule Interview Modal - Now fully functional with NewScheduleModal */}
      {scheduleCandidate && (
        <NewScheduleModal
          initialCandidate={scheduleCandidate}
          isOpen={!!scheduleCandidate}
          onClose={() => setScheduleCandidate(null)}
          onScheduled={(data) => {
            showToast(`Interview scheduled for ${data.candidateName}! Candidate notified.`);
          }}
        />
      )}
    </div>
  );
};

export default RecentSubmissions;
