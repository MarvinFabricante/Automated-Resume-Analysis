import React, { useState, useMemo } from 'react';
import {
  Layers,
  Search,
  Filter,
  Calendar,
  Users,
  ChevronRight,
  Briefcase,
  CheckCircle2,
  Clock,
  Sparkles,
  ArrowRight,
  TrendingUp,
  Archive,
  RotateCcw,
  Trash2
} from 'lucide-react';
import {
  useGetShortlistRostersQuery,
  useArchiveShortlistRosterMutation,
  useDeleteShortlistRosterMutation
} from '../../../redux/api/apiSlice';

interface ShortlistRostersListProps {
  onOpenRoster: (roster: any) => void;
  onStartScreening: () => void;
}

const ShortlistRostersList: React.FC<ShortlistRostersListProps> = ({
  onOpenRoster,
  onStartScreening,
}) => {
  const { data: rosters = [], isLoading, refetch } = useGetShortlistRostersQuery();
  const [archiveRoster] = useArchiveShortlistRosterMutation();
  const [deleteRoster] = useDeleteShortlistRosterMutation();

  const [search, setSearch] = useState<string>('');
  const [positionFilter, setPositionFilter] = useState<string>('All');
  const [viewTab, setViewTab] = useState<'active' | 'archived'>('active');

  // Extract unique job positions for filtering
  const positions = useMemo(() => {
    const list = rosters.map((r: any) => r.job_title).filter(Boolean);
    return ['All', ...Array.from(new Set(list))];
  }, [rosters]);

  const filteredRosters = useMemo(() => {
    return rosters.filter((r: any) => {
      const isArchived = Boolean(r.is_archived);
      if (viewTab === 'active' && isArchived) return false;
      if (viewTab === 'archived' && !isArchived) return false;

      const matchPos = positionFilter === 'All' || r.job_title === positionFilter;
      const matchSearch =
        !search.trim() ||
        (r.name || '').toLowerCase().includes(search.toLowerCase()) ||
        (r.job_title || '').toLowerCase().includes(search.toLowerCase());
      return matchPos && matchSearch;
    });
  }, [rosters, viewTab, positionFilter, search]);

  const handleToggleArchive = async (e: React.MouseEvent, rosterId: number, currentlyArchived: boolean) => {
    e.stopPropagation();
    const action = currentlyArchived ? 'restore' : 'archive';
    if (!window.confirm(`Are you sure you want to ${action} this shortlist roster?`)) return;
    try {
      await archiveRoster({ rosterId, archived: !currentlyArchived }).unwrap();
      refetch();
    } catch (err) {
      console.error('Failed to toggle archive roster:', err);
    }
  };

  const handleDelete = async (e: React.MouseEvent, rosterId: number, rosterName: string) => {
    e.stopPropagation();
    if (
      !window.confirm(
        `Are you sure you want to permanently delete the roster "${rosterName}"?\n\nCandidates not in another roster for this position will return to Under Review status.`
      )
    ) {
      return;
    }
    try {
      await deleteRoster(rosterId).unwrap();
      refetch();
    } catch (err) {
      console.error('Failed to delete roster:', err);
    }
  };

  const activeCount = rosters.filter((r: any) => !r.is_archived).length;
  const archivedCount = rosters.filter((r: any) => r.is_archived).length;
  const autoRemovedNotices = useMemo(() => {
    const notes: string[] = [];
    rosters.forEach((r: any) => {
      if (Array.isArray(r.auto_removed_withdrawn) && r.auto_removed_withdrawn.length > 0) {
        r.auto_removed_withdrawn.forEach((n: any) => {
          if (n?.message) notes.push(n.message);
        });
      } else if (r.cleanup_notice) {
        notes.push(r.cleanup_notice);
      }
    });
    return notes;
  }, [rosters]);

  return (
    <div className="space-y-6">
      {autoRemovedNotices.length > 0 && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-1">
          <p className="font-black">Withdrawn applicant(s) were automatically removed from shortlist rosters:</p>
          {autoRemovedNotices.map((msg, i) => (
            <p key={i} className="font-medium">{msg}</p>
          ))}
        </div>
      )}
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2.5">
            <span>Shortlist Rosters</span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
              {activeCount} Active
            </span>
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Manage batches of shortlisted candidates through initial interviews and outcomes.
          </p>
        </div>

        <button
          type="button"
          onClick={onStartScreening}
          className="px-4 py-2.5 bg-[#D60041] hover:bg-[#b50037] text-white text-xs sm:text-sm font-bold rounded-xl shadow-md shadow-rose-200 transition-all flex items-center gap-2 cursor-pointer shrink-0"
        >
          <Sparkles size={14} />
          <span>New Shortlist Screening</span>
        </button>
      </div>

      {/* Tabs & Filter Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Tab switcher: Active vs Archived */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl">
          <button
            type="button"
            onClick={() => setViewTab('active')}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${viewTab === 'active'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
              }`}
          >
            Active Rosters ({activeCount})
          </button>
          <button
            type="button"
            onClick={() => setViewTab('archived')}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${viewTab === 'archived'
                ? 'bg-white text-purple-700 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
              }`}
          >
            <Archive size={12} />
            <span>Archived ({archivedCount})</span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search roster or job..."
              className="w-full pl-8 pr-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:outline-none focus:border-[#D60041]"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <select
              value={positionFilter}
              onChange={(e) => setPositionFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 focus:outline-none focus:border-[#D60041]"
            >
              {positions.map((p: any) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Rosters Cards Grid */}
      {filteredRosters.length === 0 ? (
        <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center space-y-3">
          <Layers size={40} className="mx-auto text-slate-300" />
          <h3 className="text-base font-bold text-slate-800">
            {viewTab === 'archived' ? 'No Archived Rosters' : 'No Shortlist Rosters Found'}
          </h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            {search.trim() || positionFilter !== 'All'
              ? 'No rosters match your current filters. Try adjusting your search keywords.'
              : viewTab === 'archived'
                ? 'Archived rosters will appear here when you archive completed pipelines.'
                : 'You haven\'t created any shortlist rosters yet. Start a screening session to build your first candidate roster.'}
          </p>
          {viewTab === 'active' && (
            <button
              type="button"
              onClick={onStartScreening}
              className="mt-4 px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-xl hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Start Screening
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredRosters.map((roster: any) => {
            const total = roster.total_candidates || 0;
            const shortlisted = roster.shortlisted_count ?? roster.stage_counts?.['Shortlisted'] ?? 0;
            const scheduled = roster.interview_scheduled_count ?? roster.stage_counts?.['Interview Scheduled'] ?? 0;
            const interviewed = roster.interviewed_count ?? roster.stage_counts?.['Interviewed'] ?? 0;
            const passed = roster.passed_count ?? roster.stage_counts?.['Passed initial interview'] ?? 0;
            const notSelected = roster.not_selected_count ?? roster.stage_counts?.['Not selected'] ?? 0;
            const completedCount = interviewed + passed + notSelected;
            const progressPct = total > 0 ? Math.round((completedCount / total) * 100) : 0;
            const isArchived = Boolean(roster.is_archived);

            return (
              <div
                key={roster.id}
                onClick={() => onOpenRoster(roster)}
                className={`bg-white rounded-3xl border p-5 sm:p-6 shadow-xs hover:shadow-md transition-all cursor-pointer flex flex-col justify-between group ${isArchived ? 'border-dashed border-slate-300 opacity-90' : 'border-slate-200/90 hover:border-purple-300'
                  }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-100">
                          {roster.job_title}
                        </span>
                        {isArchived && (
                          <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded-md">
                            Archived
                          </span>
                        )}
                      </div>
                      <h3 className="text-base font-black text-slate-900 tracking-tight group-hover:text-purple-700 transition-colors truncate">
                        {roster.name}
                      </h3>
                    </div>
                    <span className="text-xs font-black text-purple-900 bg-purple-50 px-2.5 py-1 rounded-xl border border-purple-100 shrink-0">
                      {total} {total === 1 ? 'Candidate' : 'Candidates'}
                    </span>
                  </div>

                  <p className="text-xs text-slate-500 line-clamp-2">
                    {roster.notes || `Candidate shortlist batch for ${roster.job_title}.`}
                  </p>

                  {/* Stage Counts Chips */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-slate-100 text-slate-700">
                      Shortlisted: {shortlisted}
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-blue-50 text-blue-700">
                      Scheduled: {scheduled}
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-amber-50 text-amber-800">
                      Interviewed: {interviewed}
                    </span>
                    {passed > 0 && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-emerald-50 text-emerald-700">
                        Passed: {passed}
                      </span>
                    )}
                    {notSelected > 0 && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-rose-50 text-rose-700">
                        Not Selected: {notSelected}
                      </span>
                    )}
                  </div>

                  {/* Progress Bar */}
                  <div className="space-y-1 pt-2">
                    <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                      <span>Interview Progress</span>
                      <span className="text-slate-800 font-bold">{progressPct}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-purple-600 h-full rounded-full transition-all duration-500"
                        style={{ width: `${progressPct}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Card Footer with Archive & Delete buttons */}
                <div className="flex items-center justify-between pt-4 mt-4 border-t border-slate-100 text-xs text-slate-400">
                  <div className="flex items-center gap-1">
                    <Calendar size={13} />
                    <span>{roster.created_at ? new Date(roster.created_at).toLocaleDateString() : ''}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Archive / Restore Button */}
                    <button
                      type="button"
                      onClick={(e) => handleToggleArchive(e, roster.id, isArchived)}
                      title={isArchived ? 'Restore to active rosters' : 'Archive this roster'}
                      className="p-1 text-slate-400 hover:text-purple-700 rounded transition-colors cursor-pointer"
                    >
                      {isArchived ? <RotateCcw size={14} /> : <Archive size={14} />}
                    </button>

                    {/* Delete Button */}
                    <button
                      type="button"
                      onClick={(e) => handleDelete(e, roster.id, roster.name)}
                      title="Delete roster permanently"
                      className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors cursor-pointer"
                    >
                      <Trash2 size={14} />
                    </button>

                    <span className="text-purple-700 font-bold flex items-center gap-0.5 group-hover:translate-x-1 transition-transform ml-1">
                      <span>Open</span>
                      <ChevronRight size={14} />
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ShortlistRostersList;
