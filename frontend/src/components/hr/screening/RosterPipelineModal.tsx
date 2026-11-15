import React, { useState, useMemo } from 'react';
import {
  X,
  Layers,
  Calendar,
  CheckCircle2,
  Clock,
  Sparkles,
  Phone,
  Mail,
  User,
  ArrowRight,
  Filter,
  Search,
  AlertCircle,
  MoreVertical,
  Trash2,
  Check,
  XCircle,
  FileText
} from 'lucide-react';
import {
  useGetShortlistRosterByIdQuery,
  useUpdateRosterStageMutation,
  useRemoveCandidateFromRosterMutation,
} from '../../../redux/api/apiSlice';

interface RosterPipelineModalProps {
  rosterId: number | string;
  isOpen: boolean;
  onClose: () => void;
  onScheduleInterview: (candidate: any) => void;
  onOpenDetails: (candidate: any) => void;
}

const STAGES = [
  { id: 'Shortlisted', label: 'Shortlisted', color: 'border-purple-200 bg-purple-50/50' },
  { id: 'Interview Scheduled', label: 'Interview Scheduled', color: 'border-blue-200 bg-blue-50/50' },
  { id: 'Interviewed', label: 'Interviewed', color: 'border-amber-200 bg-amber-50/50' },
  { id: 'Outcome', label: 'Outcome (Passed / Not Selected)', color: 'border-emerald-200 bg-emerald-50/50' },
];

const RosterPipelineModal: React.FC<RosterPipelineModalProps> = ({
  rosterId,
  isOpen,
  onClose,
  onScheduleInterview,
  onOpenDetails,
}) => {
  const { data: roster, isLoading, refetch } = useGetShortlistRosterByIdQuery(rosterId, {
    skip: !isOpen || !rosterId,
  });

  const [updateStage] = useUpdateRosterStageMutation();
  const [removeCandidate] = useRemoveCandidateFromRosterMutation();

  const [search, setSearch] = useState<string>('');
  const [stageFilter, setStageFilter] = useState<string>('All');
  const [reminderPrompt, setReminderPrompt] = useState<any | null>(null);

  if (!isOpen) return null;

  const items = roster?.items || [];

  const filteredItems = items.filter((item: any) => {
    const matchSearch =
      !search.trim() ||
      (item.candidate_name || '').toLowerCase().includes(search.toLowerCase()) ||
      (item.candidate_email || '').toLowerCase().includes(search.toLowerCase());
    const matchStage = stageFilter === 'All' || item.stage === stageFilter;
    return matchSearch && matchStage;
  });

  const handleSetStage = async (applicationId: number | string, stage: string) => {
    try {
      await updateStage({
        rosterId,
        applicationId,
        stage,
      }).unwrap();
      refetch();
    } catch (err) {
      console.error('Failed to update stage:', err);
    }
  };

  const handleRemove = async (applicationId: number | string) => {
    if (!window.confirm('Remove this applicant from this shortlist roster? Their status will return to Under Review unless they are in another roster.')) {
      return;
    }
    try {
      await removeCandidate({
        rosterId,
        applicationId,
      }).unwrap();
      refetch();
    } catch (err) {
      console.error('Failed to remove applicant from roster:', err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-y-auto animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl shadow-2xl max-w-6xl w-full max-h-[92vh] flex flex-col overflow-hidden border border-slate-200 animate-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-slate-50 to-white shrink-0">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2.5 py-0.5 rounded-full border border-purple-200">
                {roster?.job_title || 'Shortlist'}
              </span>
              <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                {roster?.name || 'Roster Pipeline'}
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Created {roster?.created_at ? new Date(roster.created_at).toLocaleDateString() : ''} • {items.length} {items.length === 1 ? 'candidate' : 'candidates'} in this pipeline
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative w-48 sm:w-64">
              <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search candidate..."
                className="w-full pl-8 pr-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs outline-none focus:border-purple-600"
              />
            </div>

            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Reminder Prompt Banner (if a scheduled interview time passed) */}
        {reminderPrompt && (
          <div className="bg-amber-50 border-b border-amber-200 px-6 py-3 flex items-center justify-between gap-4 animate-in slide-in-from-top duration-150">
            <div className="flex items-center gap-2 text-xs text-amber-900">
              <Clock size={16} className="text-amber-600 shrink-0" />
              <span>
                Interview scheduled time for <strong>{reminderPrompt.candidate_name}</strong> has passed. Did the candidate attend the initial interview?
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  handleSetStage(reminderPrompt.application_id, 'Interviewed');
                  setReminderPrompt(null);
                }}
                className="px-3 py-1 bg-amber-600 text-white rounded-lg text-xs font-bold hover:bg-amber-700 transition-colors cursor-pointer"
              >
                Mark as Interviewed
              </button>
              <button
                onClick={() => setReminderPrompt(null)}
                className="px-2 py-1 text-xs text-amber-700 hover:text-amber-900"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* ─── PIPELINE STAGES BOARD ─── */}
        <div className="flex-1 overflow-x-auto p-6 bg-slate-50/50">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 min-w-[900px] h-full items-start">
            {STAGES.map((st) => {
              const stageItems = filteredItems.filter((i: any) => {
                if (st.id === 'Outcome') {
                  return i.stage === 'Passed initial interview' || i.stage === 'Not selected';
                }
                return i.stage === st.id;
              });

              return (
                <div
                  key={st.id}
                  className={`rounded-2xl border ${st.color} p-4 flex flex-col max-h-[68vh] shadow-2xs`}
                >
                  {/* Column Stage Header */}
                  <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-200/80">
                    <h3 className="text-xs font-black text-slate-800 uppercase tracking-wider">
                      {st.label}
                    </h3>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-white text-slate-700 border border-slate-200">
                      {stageItems.length}
                    </span>
                  </div>

                  {/* Stage Items */}
                  <div className="space-y-3 overflow-y-auto flex-1 pr-1">
                    {stageItems.length === 0 ? (
                      <p className="text-xs text-slate-400 italic text-center py-8">
                        No candidates at this stage.
                      </p>
                    ) : (
                      stageItems.map((item: any) => {
                        const rawName = (item.candidate_name || item.application?.candidate_name || item.name || item.fullname || '').trim();
                        const rawEmail = (item.candidate_email || item.application?.candidate_email || item.email || '').trim();
                        const candName = rawName || rawEmail || `Candidate #${item.application_id || item.id || 'N/A'}`;
                        const candEmail = rawEmail;
                        const candScore = item.match_score ?? item.application?.match_score;
                        const isImported = (item.source && !item.source.toLowerCase().includes('online')) || (item.application?.source && !item.application.source.toLowerCase().includes('online'));

                        return (
                          <div
                            key={item.id}
                            className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-2xs space-y-2 hover:border-purple-300 transition-colors"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <h4 className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                                    {candName}
                                  </h4>
                                  {isImported && (
                                    <span className="text-[9px] font-bold px-1.5 py-0.2 rounded-md bg-amber-50 text-amber-800 border border-amber-200">
                                      Imported
                                    </span>
                                  )}
                                </div>
                                <p className="text-[11px] text-slate-500 truncate">{candEmail}</p>
                              </div>
                              <span className="text-[11px] font-bold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
                                {candScore !== null && candScore !== undefined ? `${Math.round(candScore)}%` : '-'}
                              </span>
                            </div>

                            {/* Outcome Badge if in Outcome stage */}
                            {(item.stage === 'Passed initial interview' || item.stage === 'Not selected' || item.stage === 'Not Selected') && (
                              <div className="pt-1">
                                {item.stage === 'Passed initial interview' ? (
                                  <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 border border-emerald-200">
                                    <Check size={11} />
                                    <span>Passed Initial Interview</span>
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-rose-100 text-rose-800 border border-rose-200">
                                    <XCircle size={11} />
                                    <span>Not Selected</span>
                                  </span>
                                )}
                              </div>
                            )}

                            {/* Quick Stage Controls */}
                            <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5 justify-between">
                              <button
                                type="button"
                                onClick={() => onOpenDetails({ id: item.application_id, name: candName, email: candEmail })}
                                className="text-[11px] font-semibold text-slate-500 hover:text-slate-800 cursor-pointer"
                              >
                                Details
                              </button>

                              <div className="flex items-center gap-1 flex-wrap">
                                {item.stage === 'Shortlisted' && (
                                  <button
                                    type="button"
                                    onClick={() => onScheduleInterview({
                                      id: item.application_id,
                                      name: candName,
                                      email: candEmail,
                                      job_id: roster?.job_id,
                                      job_title: roster?.job_title
                                    })}
                                    className="text-[10px] font-bold px-2 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-lg transition-colors cursor-pointer"
                                  >
                                    Schedule
                                  </button>
                                )}

                                {(item.stage === 'Interview Scheduled' || item.stage === 'Shortlisted') && (
                                  <button
                                    type="button"
                                    onClick={() => handleSetStage(item.application_id, 'Interviewed')}
                                    className="text-[10px] font-bold px-2 py-1 bg-amber-50 text-amber-800 hover:bg-amber-100 rounded-lg transition-colors cursor-pointer"
                                    title="Mark interview completed"
                                  >
                                    Interviewed
                                  </button>
                                )}

                                {item.stage === 'Interviewed' && (
                                  <>
                                    <button
                                      type="button"
                                      onClick={() => handleSetStage(item.application_id, 'Passed initial interview')}
                                      className="text-[10px] font-bold px-2 py-1 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg transition-colors cursor-pointer"
                                    >
                                      Passed
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        if (window.confirm(`Are you sure you want to mark ${candName} as Not Selected? This will update their application status to Not Selected.`)) {
                                          handleSetStage(item.application_id, 'Not selected');
                                        }
                                      }}
                                      className="text-[10px] font-bold px-2 py-1 bg-rose-50 text-rose-700 hover:bg-rose-100 rounded-lg transition-colors cursor-pointer"
                                    >
                                      Not Selected
                                    </button>
                                  </>
                                )}

                                {(item.stage === 'Passed initial interview' || item.stage === 'Not selected' || item.stage === 'Not Selected') && (
                                  <button
                                    type="button"
                                    onClick={() => handleSetStage(item.application_id, 'Interviewed')}
                                    className="text-[10px] font-bold px-2 py-1 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
                                    title="Revert outcome back to Interviewed stage"
                                  >
                                    Undo
                                  </button>
                                )}

                                <button
                                  type="button"
                                  onClick={() => handleRemove(item.application_id)}
                                  title="Remove from shortlist"
                                  aria-label="Remove from shortlist"
                                  className="p-1 text-slate-300 hover:text-rose-600 rounded transition-colors cursor-pointer"
                                >
                                  <Trash2 size={12} />
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RosterPipelineModal;
