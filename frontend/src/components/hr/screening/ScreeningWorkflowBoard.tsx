import React, { useState, useMemo } from 'react';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Users,
  Search,
  Filter,
  CheckSquare,
  Square,
  Eye,
  Sliders,
  Layers,
  Phone,
  Mail,
  Briefcase,
  HelpCircle,
  FileText
} from 'lucide-react';
import { getAssetUrl } from '../../../services/api';

interface ScreeningWorkflowBoardProps {
  jobTitle: string;
  jobId: number | string;
  minThreshold: number;
  candidates: any[];
  onOpenDetails: (candidate: any) => void;
  onOpenFinalize: (recommendedIds: (number | string)[]) => void;
  onChangeParams: () => void;
}

const ScreeningWorkflowBoard: React.FC<ScreeningWorkflowBoardProps> = ({
  jobTitle,
  jobId,
  minThreshold,
  candidates = [],
  onOpenDetails,
  onOpenFinalize,
  onChangeParams,
}) => {
  // Manual overrides mapping: candidateId -> 'recommended' | 'below'
  const [columnOverrides, setColumnOverrides] = useState<Record<string, 'recommended' | 'below'>>({});
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [draggedCandidateId, setDraggedCandidateId] = useState<string | null>(null);

  // Filter candidates relevant to this job
  const jobCandidates = useMemo(() => {
    return candidates.filter((c) => {
      const cJobId = c.job?.id || c.job_id || c.job?.job_id;
      const cJobTitle = (c.preferredJob || c.job_title || c.job?.job_title || '').toLowerCase();
      if (jobId && cJobId) {
        return String(cJobId) === String(jobId);
      }
      return cJobTitle === (jobTitle || '').toLowerCase();
    });
  }, [candidates, jobId, jobTitle]);

  // Split into Recommended and Below Threshold
  const { recommended, belowThreshold } = useMemo(() => {
    const rec: any[] = [];
    const below: any[] = [];

    for (const c of jobCandidates) {
      const idStr = String(c.id);
      const score = Math.round(c.matchScore ?? c.match_score ?? 0);

      // Check for manual override first
      const override = columnOverrides[idStr];
      if (override === 'recommended') {
        rec.push(c);
      } else if (override === 'below') {
        below.push(c);
      } else if (score >= minThreshold) {
        rec.push(c);
      } else {
        below.push(c);
      }
    }

    // Sort recommended high-to-low by match score
    rec.sort((a, b) => {
      const scoreA = Number(a.matchScore ?? a.match_score ?? 0);
      const scoreB = Number(b.matchScore ?? b.match_score ?? 0);
      return scoreB - scoreA;
    });

    // Sort below threshold high-to-low as well
    below.sort((a, b) => {
      const scoreA = Number(a.matchScore ?? a.match_score ?? 0);
      const scoreB = Number(b.matchScore ?? b.match_score ?? 0);
      return scoreB - scoreA;
    });

    return { recommended: rec, belowThreshold: below };
  }, [jobCandidates, minThreshold, columnOverrides]);

  // Apply search query filter
  const filterList = (list: any[]) => {
    if (!searchFilter.trim()) return list;
    const q = searchFilter.toLowerCase();
    return list.filter((c) => {
      const name = (c.name || c.candidate_name || '').toLowerCase();
      const email = (c.email || c.candidate_email || '').toLowerCase();
      const skills = Array.isArray(c.skills) ? c.skills.join(' ').toLowerCase() : '';
      return name.includes(q) || email.includes(q) || skills.includes(q);
    });
  };

  const displayedRecommended = filterList(recommended);
  const displayedBelow = filterList(belowThreshold);

  // Move candidate to other column
  const moveCandidate = (id: string | number, targetCol: 'recommended' | 'below') => {
    const idStr = String(id);
    setColumnOverrides((prev) => ({
      ...prev,
      [idStr]: targetCol,
    }));
  };

  // Bulk move
  const handleBulkMove = (targetCol: 'recommended' | 'below') => {
    if (selectedIds.length === 0) return;
    setColumnOverrides((prev) => {
      const updated = { ...prev };
      for (const id of selectedIds) {
        updated[id] = targetCol;
      }
      return updated;
    });
    setSelectedIds([]);
  };

  const toggleSelect = (id: string | number) => {
    const idStr = String(id);
    setSelectedIds((prev) =>
      prev.includes(idStr) ? prev.filter((i) => i !== idStr) : [...prev, idStr]
    );
  };

  const selectAllInColumn = (list: any[]) => {
    const ids = list.map((c) => String(c.id));
    const allSelected = ids.every((id) => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds((prev) => prev.filter((id) => !ids.includes(id)));
    } else {
      setSelectedIds((prev) => Array.from(new Set([...prev, ...ids])));
    }
  };

  // Drag and Drop handlers
  const handleDragStart = (e: React.DragEvent, id: string | number) => {
    setDraggedCandidateId(String(id));
    e.dataTransfer.setData('text/plain', String(id));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, targetCol: 'recommended' | 'below') => {
    e.preventDefault();
    const id = e.dataTransfer.getData('text/plain') || draggedCandidateId;
    if (id) {
      moveCandidate(id, targetCol);
      setDraggedCandidateId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Active Screening Session Bar */}
      <div className="bg-white rounded-3xl p-5 sm:p-6 border border-slate-200/90 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-[#D60041] border border-rose-100">
              Active Screening
            </span>
            <h2 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">
              {jobTitle}
            </h2>
          </div>
          <p className="text-xs text-slate-500">
            Threshold: <strong>{minThreshold}%</strong> • Total Applicants: <strong>{jobCandidates.length}</strong> • Recommended: <strong className="text-emerald-700">{recommended.length}</strong> • Talent Pool: <strong>{belowThreshold.length}</strong>
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0 flex-wrap">
          <button
            type="button"
            onClick={onChangeParams}
            className="px-3.5 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-bold rounded-xl transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <Sliders size={14} />
            <span>Adjust Parameters</span>
          </button>

          <button
            type="button"
            onClick={() => onOpenFinalize(recommended.map((c) => c.id))}
            disabled={recommended.length === 0}
            className="px-5 py-2.5 bg-gradient-to-r from-purple-700 to-indigo-700 hover:from-purple-800 hover:to-indigo-800 text-white text-xs sm:text-sm font-bold rounded-xl shadow-md shadow-purple-200 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <Layers size={15} />
            <span>Finalize Shortlist ({recommended.length})</span>
          </button>
        </div>
      </div>

      {/* Filter and Bulk Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search size={15} className="absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Filter candidates by name or skill..."
            className="w-full pl-9 pr-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:outline-none focus:border-[#D60041]"
          />
        </div>

        {selectedIds.length > 0 && (
          <div className="flex items-center gap-2 bg-slate-100 px-3 py-1.5 rounded-xl text-xs font-bold text-slate-700">
            <span>{selectedIds.length} selected</span>
            <button
              onClick={() => handleBulkMove('recommended')}
              className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors cursor-pointer"
            >
              Move to Recommended
            </button>
            <button
              onClick={() => handleBulkMove('below')}
              className="px-2.5 py-1 bg-slate-700 hover:bg-slate-800 text-white rounded-lg transition-colors cursor-pointer"
            >
              Move to Talent Pool
            </button>
            <button
              onClick={() => setSelectedIds([])}
              className="px-2 py-1 text-slate-500 hover:text-slate-800 cursor-pointer"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {/* ─── TWO COLUMNS SCREENING BOARD ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Column 1: Recommended */}
        <div
          onDragOver={handleDragOver}
          onDrop={(e) => handleDrop(e, 'recommended')}
          className="bg-emerald-50/40 rounded-3xl p-5 border-2 border-dashed border-emerald-200/90 flex flex-col min-h-[500px]"
        >
          {/* Column Header */}
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-emerald-100">
            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => selectAllInColumn(displayedRecommended)}
                className="text-emerald-700 hover:text-emerald-900"
              >
                {displayedRecommended.length > 0 &&
                displayedRecommended.every((c) => selectedIds.includes(String(c.id))) ? (
                  <CheckSquare size={16} />
                ) : (
                  <Square size={16} />
                )}
              </button>
              <h3 className="text-sm font-black text-emerald-950 uppercase tracking-wider flex items-center gap-2">
                <span>Recommended for Shortlist</span>
                <span className="text-xs bg-emerald-200/80 text-emerald-900 px-2 py-0.5 rounded-full font-bold">
                  {displayedRecommended.length}
                </span>
              </h3>
            </div>
            <span className="text-xs font-semibold text-emerald-800">≥ {minThreshold}% match</span>
          </div>

          {/* Cards List */}
          {displayedRecommended.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
              <Users size={32} className="mb-2 text-emerald-300" />
              <p className="text-xs font-bold text-slate-600">No candidates in Recommended</p>
              <p className="text-[11px] text-slate-400 mt-1 max-w-xs">
                Drag candidates here or click "Move to Shortlist" to add them to this roster.
              </p>
            </div>
          ) : (
            <div className="space-y-3 flex-1 overflow-y-auto pr-1">
              {displayedRecommended.map((candidate) => {
                const id = candidate.id;
                const isSelected = selectedIds.includes(String(id));
                const score = Math.round(candidate.matchScore ?? candidate.match_score ?? 0);
                const name = candidate.name || candidate.candidate_name || 'Candidate';
                const email = candidate.email || candidate.candidate_email;
                const source = candidate.source || 'Online';

                return (
                  <div
                    key={id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, id)}
                    className={`bg-white rounded-2xl p-4 border transition-all cursor-grab active:cursor-grabbing shadow-xs ${
                      isSelected
                        ? 'border-emerald-500 ring-2 ring-emerald-500/20'
                        : 'border-emerald-100 hover:border-emerald-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3 min-w-0">
                        <button
                          type="button"
                          onClick={() => toggleSelect(id)}
                          className="mt-0.5 text-slate-400 hover:text-emerald-700 shrink-0"
                        >
                          {isSelected ? (
                            <CheckSquare size={16} className="text-emerald-600" />
                          ) : (
                            <Square size={16} />
                          )}
                        </button>
                        <div className="min-w-0">
                          <h4 className="text-sm font-bold text-slate-900 truncate">{name}</h4>
                          <p className="text-xs text-slate-500 truncate">{email}</p>
                          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                !source.toLowerCase().includes('online')
                                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                                  : 'bg-slate-100 text-slate-600 border-slate-200'
                              }`}
                              title={!source.toLowerCase().includes('online') ? `Imported: ${candidate.import_origin || 'Walk-in'}` : 'Online website application'}
                            >
                              {!source.toLowerCase().includes('online') ? (candidate.import_origin ? `Imported: ${candidate.import_origin}` : 'Imported') : 'Online'}
                            </span>
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                              {candidate.status || 'Submitted'}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-col items-end gap-2 shrink-0">
                        <span className="text-xs font-black px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {score}% Match
                        </span>
                      </div>
                    </div>

                    {/* Quick Action Buttons */}
                    <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-100">
                      <button
                        type="button"
                        onClick={() => onOpenDetails(candidate)}
                        className="text-xs font-bold text-slate-600 hover:text-slate-900 flex items-center gap-1 cursor-pointer"
                      >
                        <Eye size={13} />
                        <span>View Details</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => moveCandidate(id, 'below')}
                        className="text-xs font-bold text-slate-500 hover:text-slate-800 flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                        title="Move back to talent pool"
                      >
                        <span>Move to Pool</span>
                        <ArrowRight size={13} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Column 2: Below Threshold / Talent Pool */}
        <div
          onDragOver={handleDragOver}
          onDrop={(e) => handleDrop(e, 'below')}
          className="bg-slate-50/80 rounded-3xl p-5 border-2 border-dashed border-slate-200 flex flex-col min-h-[500px]"
        >
          {/* Column Header */}
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-200/80">
            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => selectAllInColumn(displayedBelow)}
                className="text-slate-500 hover:text-slate-800"
              >
                {displayedBelow.length > 0 &&
                displayedBelow.every((c) => selectedIds.includes(String(c.id))) ? (
                  <CheckSquare size={16} />
                ) : (
                  <Square size={16} />
                )}
              </button>
              <h3 className="text-sm font-black text-slate-700 uppercase tracking-wider flex items-center gap-2">
                <span>Below Threshold / Talent Pool</span>
                <span className="text-xs bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full font-bold">
                  {displayedBelow.length}
                </span>
              </h3>
            </div>
            <span className="text-[11px] font-medium text-slate-500">Never auto-rejected</span>
          </div>

          {/* Cards List */}
          {displayedBelow.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
              <CheckCircle2 size={32} className="mb-2 text-slate-300" />
              <p className="text-xs font-bold text-slate-600">No candidates below threshold</p>
              <p className="text-[11px] text-slate-400 mt-1 max-w-xs">
                All evaluated candidates meet or exceed the {minThreshold}% match criteria.
              </p>
            </div>
          ) : (
            <div className="space-y-3 flex-1 overflow-y-auto pr-1">
              {displayedBelow.map((candidate) => {
                const id = candidate.id;
                const isSelected = selectedIds.includes(String(id));
                const score = Math.round(candidate.matchScore ?? candidate.match_score ?? 0);
                const name = candidate.name || candidate.candidate_name || 'Candidate';
                const email = candidate.email || candidate.candidate_email;
                const source = candidate.source || 'Online';

                return (
                  <div
                    key={id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, id)}
                    className={`bg-white rounded-2xl p-4 border transition-all cursor-grab active:cursor-grabbing shadow-xs ${
                      isSelected
                        ? 'border-purple-500 ring-2 ring-purple-500/20'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3 min-w-0">
                        <button
                          type="button"
                          onClick={() => toggleSelect(id)}
                          className="mt-0.5 text-slate-400 hover:text-slate-700 shrink-0"
                        >
                          {isSelected ? (
                            <CheckSquare size={16} className="text-purple-600" />
                          ) : (
                            <Square size={16} />
                          )}
                        </button>
                        <div className="min-w-0">
                          <h4 className="text-sm font-bold text-slate-900 truncate">{name}</h4>
                          <p className="text-xs text-slate-500 truncate">{email}</p>
                          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                !source.toLowerCase().includes('online')
                                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                                  : 'bg-slate-100 text-slate-600 border-slate-200'
                              }`}
                              title={!source.toLowerCase().includes('online') ? `Imported: ${candidate.import_origin || 'Walk-in'}` : 'Online website application'}
                            >
                              {!source.toLowerCase().includes('online') ? (candidate.import_origin ? `Imported: ${candidate.import_origin}` : 'Imported') : 'Online'}
                            </span>
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                              {candidate.status || 'Submitted'}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-col items-end gap-2 shrink-0">
                        <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                          {score}% Match
                        </span>
                      </div>
                    </div>

                    {/* Quick Action Buttons */}
                    <div className="flex items-center justify-between pt-3 mt-3 border-t border-slate-100">
                      <button
                        type="button"
                        onClick={() => onOpenDetails(candidate)}
                        className="text-xs font-bold text-slate-600 hover:text-slate-900 flex items-center gap-1 cursor-pointer"
                      >
                        <Eye size={13} />
                        <span>View Details</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => moveCandidate(id, 'recommended')}
                        className="text-xs font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 transition-colors cursor-pointer"
                        title="Move to recommended shortlist"
                      >
                        <ArrowLeft size={13} />
                        <span>Move to Shortlist</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ScreeningWorkflowBoard;
