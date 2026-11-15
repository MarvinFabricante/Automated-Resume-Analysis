import React, { useState } from 'react';
import { X, Layers, CheckCircle2, AlertCircle, FileText } from 'lucide-react';

interface FinalizeShortlistModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: number | string;
  jobTitle: string;
  candidateIds: (number | string)[];
  onFinalize: (name: string, notes: string) => Promise<void>;
}

const FinalizeShortlistModal: React.FC<FinalizeShortlistModalProps> = ({
  isOpen,
  onClose,
  jobId,
  jobTitle,
  candidateIds,
  onFinalize,
}) => {
  const currentMonthYear = new Date().toLocaleDateString('en-US', {
    month: 'short',
    year: 'numeric',
  });
  const defaultName = `${jobTitle || 'Shortlist'} - ${currentMonthYear}`;

  const [rosterName, setRosterName] = useState<string>(defaultName);
  const [notes, setNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rosterName.trim()) {
      setError('Please provide a name for this shortlist roster.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onFinalize(rosterName.trim(), notes.trim());
      onClose();
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || 'Failed to finalize shortlist roster.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl shadow-2xl max-w-lg w-full p-6 sm:p-7 border border-slate-200 animate-in zoom-in-95 duration-200 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-50 text-purple-700 flex items-center justify-center font-bold">
              <Layers size={20} />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-black text-slate-900 tracking-tight">
                Finalize Shortlist Roster
              </h3>
              <p className="text-xs text-slate-500">
                Save shortlisted candidates for {jobTitle} into a tracked roster.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-700 flex items-center gap-2">
            <AlertCircle size={15} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="bg-purple-50/70 border border-purple-100 rounded-2xl p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-purple-900">Candidates to Shortlist</p>
              <p className="text-xs text-purple-700 mt-0.5">
                All candidates in the Recommended column will be placed in this roster.
              </p>
            </div>
            <span className="text-xl font-black text-purple-800 bg-white px-3 py-1 rounded-xl shadow-2xs border border-purple-200">
              {candidateIds.length}
            </span>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Roster Name
            </label>
            <input
              type="text"
              value={rosterName}
              onChange={(e) => setRosterName(e.target.value)}
              placeholder="e.g. Production Operator - Nov 2026"
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm font-semibold text-slate-800 focus:bg-white focus:border-purple-600 focus:ring-2 focus:ring-purple-600/10 outline-none"
              required
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Notes (Optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Batch for Plant 2 expansion, initial interview slots target for next week."
              rows={3}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm text-slate-800 focus:bg-white focus:border-purple-600 focus:ring-2 focus:ring-purple-600/10 outline-none resize-none"
            />
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start gap-2">
            <CheckCircle2 size={15} className="text-emerald-600 shrink-0 mt-0.5" />
            <span>
              Finalizing will update all included applications to <strong>Shortlisted</strong> and record this transition in their audit history.
            </span>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || candidateIds.length === 0}
              className="px-5 py-2.5 bg-purple-700 hover:bg-purple-800 text-white text-xs sm:text-sm font-bold rounded-xl shadow-md shadow-purple-200 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              <Layers size={14} />
              <span>{isSubmitting ? 'Finalizing...' : 'Finalize Shortlist'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FinalizeShortlistModal;
