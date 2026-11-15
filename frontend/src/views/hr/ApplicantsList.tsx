import React, { useState, useMemo } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from '@/utils/navigation';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { useGetApplicationsQuery, useGetJobsQuery } from '../../redux/api/apiSlice';
import HelpTooltip from '../../components/common/HelpTooltip';
import {
  Users,
  Search,
  Filter,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Briefcase,
  FileText,
  Calendar,
  Sparkles,
  Inbox,
  UserCheck,
  Building2,
  Clock,
  Layers,
  CheckCircle2
} from 'lucide-react';

interface GroupedApplicant {
  email: string;
  name: string;
  phone?: string;
  positions: {
    id: number;
    job_id: number;
    job_title: string;
    department?: string;
    status: string;
    match_score?: number | null;
    applied_date: string;
    source: string;
    import_origin?: string;
  }[];
  latestStatus: string;
  bestMatchScore: number | null;
  latestAppliedDate: string;
  source: string;
  import_origin?: string;
}

const ITEMS_PER_PAGE = 12;

const ApplicantsList: React.FC = () => {
  const navigate = useNavigate();
  const { data: rawApps = [], isLoading: isLoadingApps } = useGetApplicationsQuery();
  const { data: rawJobs = [] } = useGetJobsQuery();

  const [search, setSearch] = useState<string>('');
  const [selectedPosition, setSelectedPosition] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedSource, setSelectedSource] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'date_desc' | 'date_asc' | 'score_desc' | 'name_asc'>('date_desc');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Group applications by candidate email to get consolidated applicants
  const applicants: GroupedApplicant[] = useMemo(() => {
    if (!Array.isArray(rawApps)) return [];

    const map = new Map<string, GroupedApplicant>();

    rawApps.forEach((app: any) => {
      const email = (app.candidate_email || '').toLowerCase().trim();
      if (!email) return;

      const appDate = app.created_at || '';
      const appScore = typeof app.match_score === 'number' ? app.match_score : null;
      const appStatus = (app.status || 'SUBMITTED').toUpperCase();
      const appSource = app.source || 'Online';
      const appOrigin = app.import_origin;

      if (!map.has(email)) {
        map.set(email, {
          email,
          name: app.candidate_name || email,
          phone: app.phone,
          positions: [
            {
              id: app.id,
              job_id: app.job_id,
              job_title: app.job_title || app.job?.job_title || 'General Position',
              department: app.job?.department,
              status: app.status || 'Submitted',
              match_score: appScore,
              applied_date: appDate,
              source: appSource,
              import_origin: appOrigin,
            },
          ],
          latestStatus: app.status || 'Submitted',
          bestMatchScore: appScore,
          latestAppliedDate: appDate,
          source: appSource,
          import_origin: appOrigin,
        });
      } else {
        const existing = map.get(email)!;
        existing.positions.push({
          id: app.id,
          job_id: app.job_id,
          job_title: app.job_title || app.job?.job_title || 'General Position',
          department: app.job?.department,
          status: app.status || 'Submitted',
          match_score: appScore,
          applied_date: appDate,
          source: appSource,
          import_origin: appOrigin,
        });

        // Update latest status & best match score
        if (appScore !== null && (existing.bestMatchScore === null || appScore > existing.bestMatchScore)) {
          existing.bestMatchScore = appScore;
        }
        if (appDate > existing.latestAppliedDate) {
          existing.latestAppliedDate = appDate;
          existing.latestStatus = app.status || 'Submitted';
        }
        if (!existing.name || existing.name === email) {
          existing.name = app.candidate_name || email;
        }
      }
    });

    return Array.from(map.values());
  }, [rawApps]);

  // Unique positions for filter dropdown
  const uniquePositions = useMemo(() => {
    const set = new Set<string>();
    applicants.forEach((a) => {
      a.positions.forEach((p) => {
        if (p.job_title) set.add(p.job_title);
      });
    });
    return Array.from(set).sort();
  }, [applicants]);

  // Filtering & Sorting
  const filteredApplicants = useMemo(() => {
    return applicants
      .filter((applicant) => {
        // Search filter
        const matchSearch =
          !search.trim() ||
          applicant.name.toLowerCase().includes(search.toLowerCase()) ||
          applicant.email.toLowerCase().includes(search.toLowerCase()) ||
          applicant.positions.some((p) => p.job_title.toLowerCase().includes(search.toLowerCase()));

        // Position filter
        const matchPosition =
          selectedPosition === 'ALL' ||
          applicant.positions.some((p) => p.job_title.toLowerCase() === selectedPosition.toLowerCase());

        // Status filter
        const matchStatus =
          selectedStatus === 'ALL' ||
          applicant.positions.some(
            (p) => (p.status || '').toUpperCase() === selectedStatus.toUpperCase()
          );

        // Source filter
        const matchSource =
          selectedSource === 'ALL' ||
          (selectedSource === 'Online' && (applicant.source || '').toLowerCase().includes('online')) ||
          (selectedSource === 'Imported' && !(applicant.source || '').toLowerCase().includes('online'));

        return matchSearch && matchPosition && matchStatus && matchSource;
      })
      .sort((a, b) => {
        if (sortBy === 'score_desc') {
          return (b.bestMatchScore || 0) - (a.bestMatchScore || 0);
        }
        if (sortBy === 'name_asc') {
          return a.name.localeCompare(b.name);
        }
        if (sortBy === 'date_asc') {
          return (a.latestAppliedDate || '').localeCompare(b.latestAppliedDate || '');
        }
        // default: date_desc
        return (b.latestAppliedDate || '').localeCompare(a.latestAppliedDate || '');
      });
  }, [applicants, search, selectedPosition, selectedStatus, selectedSource, sortBy]);

  // Pagination
  const totalPages = Math.ceil(filteredApplicants.length / ITEMS_PER_PAGE) || 1;
  const paginatedApplicants = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredApplicants.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredApplicants, currentPage]);

  const handleRowClick = (email: string) => {
    navigate(`/hr/applicant/${encodeURIComponent(email)}`);
  };

  const getStatusBadge = (statusStr: string) => {
    const s = (statusStr || '').toUpperCase();
    if (s.includes('SHORTLIST')) {
      return 'bg-purple-50 text-purple-700 border-purple-200';
    }
    if (s.includes('INTERVIEW SCHEDULED') || s.includes('TECHNICAL INTERVIEW')) {
      return 'bg-blue-50 text-blue-700 border-blue-200';
    }
    if (s.includes('INTERVIEWED') || s.includes('PASSED INITIAL')) {
      return 'bg-amber-50 text-amber-800 border-amber-200';
    }
    if (s.includes('UNDER REVIEW') || s.includes('REVIEWED') || s.includes('SCREENED')) {
      return 'bg-indigo-50 text-indigo-700 border-indigo-200';
    }
    if (s.includes('NOT SELECTED') || s.includes('REJECTED')) {
      return 'bg-rose-50 text-rose-700 border-rose-200';
    }
    return 'bg-slate-100 text-slate-700 border-slate-200';
  };

  return (
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-sans flex flex-col">
      <Helmet>
        <title>Applicants | Mariwasa Recruitment HR Portal</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />

        <div className="flex-1 min-w-0 flex flex-col">
          <main className="w-full max-w-full px-4 sm:px-6 lg:px-8 py-6 space-y-6">
          {/* Top Title Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black text-slate-900 tracking-tight">
                  Applicants Directory
                </h1>
                <HelpTooltip text="Every person who has applied for a role at Mariwasa, online or imported, with consolidated history across all their applications." />
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Showing {filteredApplicants.length} {filteredApplicants.length === 1 ? 'applicant' : 'applicants'} on file
              </p>
            </div>

            {/* Quick Metrics */}
            <div className="flex items-center gap-3">
              <div className="bg-white px-3.5 py-2 rounded-2xl border border-slate-200 shadow-2xs text-center">
                <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Total</span>
                <span className="text-sm font-black text-slate-900">{applicants.length}</span>
              </div>
              <div className="bg-white px-3.5 py-2 rounded-2xl border border-slate-200 shadow-2xs text-center">
                <span className="text-[10px] uppercase font-bold text-purple-500 block tracking-wider">Shortlisted</span>
                <span className="text-sm font-black text-purple-700">
                  {applicants.filter((a) => a.positions.some((p) => (p.status || '').toUpperCase().includes('SHORTLIST'))).length}
                </span>
              </div>
            </div>
          </div>

          {/* Search & Filter Toolbar */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              {/* Search Box */}
              <div className="relative md:col-span-1">
                <Search size={14} className="absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setCurrentPage(1);
                  }}
                  placeholder="Search by name, email or job..."
                  className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:bg-white focus:border-[#D60041] transition-all"
                />
              </div>

              {/* Position Filter */}
              <div>
                <select
                  value={selectedPosition}
                  onChange={(e) => {
                    setSelectedPosition(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:bg-white focus:border-[#D60041] transition-all cursor-pointer text-slate-700"
                >
                  <option value="ALL">All Positions ({uniquePositions.length})</option>
                  {uniquePositions.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              {/* Status Filter */}
              <div>
                <select
                  value={selectedStatus}
                  onChange={(e) => {
                    setSelectedStatus(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:bg-white focus:border-[#D60041] transition-all cursor-pointer text-slate-700"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="SUBMITTED">Submitted</option>
                  <option value="UNDER REVIEW">Under Review</option>
                  <option value="SHORTLISTED">Shortlisted</option>
                  <option value="INTERVIEW SCHEDULED">Interview Scheduled</option>
                  <option value="INTERVIEWED">Interviewed</option>
                  <option value="NOT SELECTED">Not Selected</option>
                </select>
              </div>

              {/* Source & Sort Controls */}
              <div className="flex gap-2">
                <select
                  value={selectedSource}
                  onChange={(e) => {
                    setSelectedSource(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:bg-white focus:border-[#D60041] transition-all cursor-pointer text-slate-700"
                >
                  <option value="ALL">All Sources</option>
                  <option value="Online">Online Website</option>
                  <option value="Imported">Imported Resumes</option>
                </select>

                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:bg-white focus:border-[#D60041] transition-all cursor-pointer text-slate-700"
                >
                  <option value="date_desc">Newest First</option>
                  <option value="date_asc">Oldest First</option>
                  <option value="score_desc">Highest Match %</option>
                  <option value="name_asc">Name (A-Z)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Applicants Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            {isLoadingApps ? (
              <div className="p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-slate-300 border-t-[#D60041] rounded-full animate-spin" />
                <span>Loading applicants...</span>
              </div>
            ) : paginatedApplicants.length === 0 ? (
              <div className="p-12 text-center space-y-2">
                <Users size={32} className="mx-auto text-slate-300" />
                <p className="text-sm font-bold text-slate-700">No applicants match your filters</p>
                <p className="text-xs text-slate-400">Try clearing your search query or changing the filter options.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-100 text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                      <th className="py-3 px-4">Applicant</th>
                      <th className="py-3 px-4">Position(s) Applied</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Match %</th>
                      <th className="py-3 px-4">Source</th>
                      <th className="py-3 px-4">Date Applied</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {paginatedApplicants.map((applicant) => {
                      const isImported = !(applicant.source || '').toLowerCase().includes('online');
                      const initials = applicant.name
                        .split(' ')
                        .map((n) => n[0])
                        .slice(0, 2)
                        .join('')
                        .toUpperCase();

                      return (
                        <tr
                          key={applicant.email}
                          onClick={() => handleRowClick(applicant.email)}
                          className="hover:bg-rose-50/30 cursor-pointer transition-colors group"
                        >
                          {/* Name & Email */}
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-slate-100 to-slate-200 text-slate-700 font-black text-xs flex items-center justify-center shrink-0 border border-slate-200 group-hover:border-rose-200">
                                {initials || 'AP'}
                              </div>
                              <div className="min-w-0">
                                <p className="font-bold text-slate-900 group-hover:text-[#D60041] transition-colors truncate">
                                  {applicant.name}
                                </p>
                                <p className="text-[11px] text-slate-400 truncate">{applicant.email}</p>
                              </div>
                            </div>
                          </td>

                          {/* Positions Applied */}
                          <td className="py-3.5 px-4">
                            <div className="space-y-1">
                              <span className="font-medium text-slate-800 line-clamp-1">
                                {applicant.positions[0]?.job_title || 'Position'}
                              </span>
                              {applicant.positions.length > 1 && (
                                <span className="inline-block text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-purple-50 text-purple-700 border border-purple-200">
                                  +{applicant.positions.length - 1} other {applicant.positions.length === 2 ? 'position' : 'positions'}
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Status */}
                          <td className="py-3.5 px-4">
                            <span
                              className={`inline-block px-2.5 py-1 rounded-full text-[11px] font-bold border ${getStatusBadge(
                                applicant.latestStatus
                              )}`}
                            >
                              {applicant.latestStatus}
                            </span>
                          </td>

                          {/* Match % */}
                          <td className="py-3.5 px-4 font-bold text-slate-800">
                            {applicant.bestMatchScore !== null && applicant.bestMatchScore !== undefined ? (
                              <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold">
                                {Math.round(applicant.bestMatchScore)}%
                              </span>
                            ) : (
                              <span className="text-slate-400">-</span>
                            )}
                          </td>

                          {/* Source Badge */}
                          <td className="py-3.5 px-4">
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                                isImported
                                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                                  : 'bg-slate-100 text-slate-700 border-slate-200'
                              }`}
                              title={isImported ? `Imported: ${applicant.import_origin || 'Walk-in'}` : 'Online website application'}
                            >
                              <span>{isImported ? 'Imported' : 'Online'}</span>
                              {isImported && applicant.import_origin && (
                                <span className="text-[9px] opacity-75">• {applicant.import_origin}</span>
                              )}
                            </span>
                          </td>

                          {/* Date Applied */}
                          <td className="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                            {applicant.latestAppliedDate
                              ? new Date(applicant.latestAppliedDate).toLocaleDateString()
                              : '-'}
                          </td>

                          {/* Actions */}
                          <td className="py-3.5 px-4 text-right">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRowClick(applicant.email);
                              }}
                              className="px-3 py-1.5 bg-slate-100 hover:bg-[#D60041] text-slate-700 hover:text-white rounded-xl text-xs font-bold transition-all inline-flex items-center gap-1 cursor-pointer"
                            >
                              <span>Profile</span>
                              <ExternalLink size={12} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>
                  Page {currentPage} of {totalPages}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
                    aria-label="Previous page"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
                    aria-label="Next page"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  </div>
);
};

export default ApplicantsList;
