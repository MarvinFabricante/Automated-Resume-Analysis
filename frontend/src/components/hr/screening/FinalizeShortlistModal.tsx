import React, { useState, useEffect } from 'react';
import { X, Layers, CheckCircle2, AlertCircle, Mail, Users } from 'lucide-react';
import { usePreviewShortlistNonShortlistedMutation } from '../../../redux/api/apiSlice';

export type NonShortlistedAction = 'keep_under_review' | 'notify_on_finalize' | 'decide_later';

interface FinalizeShortlistModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: number | string;
  jobTitle: string;
  candidateIds: (number | string)[];
  onFinalize: (
    name: string,
    notes: string,
    options?: {
      non_shortlisted_action: NonShortlistedAction;
      finalize: boolean;
      confirm_notify_non_shortlisted: boolean;
    }
  ) => Promise<void>;
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
  const [nonShortlistedAction, setNonShortlistedAction] = useState<NonShortlistedAction>('keep_under_review');
  const [finalizeNow, setFinalizeNow] = useState<boolean>(true);
  const [confirmNotify, setConfirmNotify] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<any | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [fetchPreview, { isLoading: isLoadingPreview }] = usePreviewShortlistNonShortlistedMutation();

  useEffect(() => {
    if (!isOpen || !jobId) return;
    setRosterName(`${jobTitle || 'Shortlist'} - ${currentMonthYear}`);
    setConfirmNotify(false);
    fetchPreview({
      job_id: Number(jobId),
      shortlisted_application_ids: candidateIds.map(Number).filter((n) => !Number.isNaN(n)),
    })
      .unwrap()
      .then((res) => setPreviewData(res))
      .catch(() => setPreviewData(null));
  }, [isOpen, jobId, jobTitle, candidateIds, fetchPreview, currentMonthYear]);

  if (!isOpen) return null;

  const affectedCount = Number(previewData?.affected_count ?? 0);
  const requiresExplicitConfirm = finalizeNow && nonShortlistedAction === 'notify_on_finalize';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rosterName.trim()) {
      setError('Please provide a name for this shortlist roster.');
      return;
    }
    if (requiresExplicitConfirm && !confirmNotify) {
      setError('Please review the affected applicant count and message preview, then check the confirmation box before notifying applicants.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onFinalize(rosterName.trim(), notes.trim(), {
        non_shortlisted_action: nonShortlistedAction,
        finalize: finalizeNow,
        confirm_notify_non_shortlisted: confirmNotify,
      });
      onClose();
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || 'Failed to finalize shortlist roster.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl shadow-2xl max-w-2xl w-full p-6 sm:p-7 border border-slate-200 animate-in zoom-in-95 duration-200 space-y-5 max-h-[92vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-50 text-purple-700 flex items-center justify-center font-bold">
              <Layers size={20} />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-black text-slate-900 tracking-tight">
                Shortlist Roster &amp; Non-Shortlisted Applicants
              </h3>
              <p className="text-xs text-slate-500">
                Save shortlisted candidates for {jobTitle} and decide what happens to non-shortlisted applicants.
              </p>
            </div>
          </div>
          <button
            type="button"
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="bg-purple-50/70 border border-purple-100 rounded-2xl p-3.5 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-purple-900">Shortlisted</p>
                <p className="text-[11px] text-purple-700 mt-0.5">Added to this roster</p>
              </div>
              <span className="text-xl font-black text-purple-800 bg-white px-3 py-1 rounded-xl shadow-2xs border border-purple-200">
                {candidateIds.length}
              </span>
            </div>
            <div className="bg-amber-50/70 border border-amber-200/70 rounded-2xl p-3.5 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-amber-900 flex items-center gap-1.5">
                  <Users size={13} />
                  <span>Not Shortlisted (Affected)</span>
                </p>
                <p className="text-[11px] text-amber-800 mt-0.5">
                  {isLoadingPreview ? 'Calculating...' : 'Submitted / Under Review not on a roster'}
                </p>
              </div>
              <span className="text-xl font-black text-amber-900 bg-white px-3 py-1 rounded-xl shadow-2xs border border-amber-200">
                {isLoadingPreview ? '…' : affectedCount}
              </span>
            </div>
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

          {/* Non-Shortlisted Applicants Policy Prompt */}
          <div className="space-y-2 p-4 rounded-2xl bg-slate-50 border border-slate-200">
            <p className="text-xs font-black text-slate-800 uppercase tracking-wider">
              What should happen to applicants who are not shortlisted?
            </p>
            <div className="space-y-2">
              <label className="flex items-start gap-2.5 p-2.5 rounded-xl bg-white border border-slate-200 cursor-pointer hover:border-purple-300">
                <input
                  type="radio"
                  name="nonShortlistedAction"
                  checked={nonShortlistedAction === 'keep_under_review'}
                  onChange={() => {
                    setNonShortlistedAction('keep_under_review');
                    setConfirmNotify(false);
                  }}
                  className="mt-0.5 text-purple-700 focus:ring-purple-600"
                />
                <div className="text-xs">
                  <span className="font-bold text-slate-900">Keep them under review until the job is closed</span>
                  <span className="ml-1.5 px-1.5 py-0.5 text-[10px] font-bold bg-emerald-50 text-emerald-700 rounded border border-emerald-200">Default</span>
                  <p className="text-slate-500 mt-0.5">Non-shortlisted applicants stay Under Review; if the job closes later, they are notified automatically.</p>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-2.5 rounded-xl bg-white border border-slate-200 cursor-pointer hover:border-purple-300">
                <input
                  type="radio"
                  name="nonShortlistedAction"
                  checked={nonShortlistedAction === 'notify_on_finalize'}
                  onChange={() => setNonShortlistedAction('notify_on_finalize')}
                  className="mt-0.5 text-purple-700 focus:ring-purple-600"
                />
                <div className="text-xs">
                  <span className="font-bold text-slate-900">Notify them as Not Selected when the shortlist is finalized</span>
                  <p className="text-slate-500 mt-0.5">
                    Sets {affectedCount} non-shortlisted applicant(s) to <strong>Not Selected</strong> and sends the editable Not Selected notification (feedback report stays viewable).
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-2.5 rounded-xl bg-white border border-slate-200 cursor-pointer hover:border-purple-300">
                <input
                  type="radio"
                  name="nonShortlistedAction"
                  checked={nonShortlistedAction === 'decide_later'}
                  onChange={() => {
                    setNonShortlistedAction('decide_later');
                    setConfirmNotify(false);
                  }}
                  className="mt-0.5 text-purple-700 focus:ring-purple-600"
                />
                <div className="text-xs">
                  <span className="font-bold text-slate-900">Decide later</span>
                  <p className="text-slate-500 mt-0.5">No immediate status change for non-shortlisted applicants. You can update the policy before finalizing.</p>
                </div>
              </label>
            </div>

            <label className="flex items-center gap-2 pt-2 text-xs text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={finalizeNow}
                onChange={(e) => setFinalizeNow(e.target.checked)}
                className="rounded border-slate-300 text-purple-700 focus:ring-purple-600"
              />
              <span>Finalize this shortlist immediately (uncheck to save as draft and change policy before finalizing)</span>
            </label>
          </div>

          {/* Message preview & explicit confirmation before applying Not Selected */}
          {nonShortlistedAction === 'notify_on_finalize' && previewData?.message_preview && (
            <div className="p-4 rounded-2xl bg-rose-50/60 border border-rose-200 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-rose-900 flex items-center gap-1.5">
                  <Mail size={14} />
                  <span>Not Selected Message Preview ({affectedCount} applicant{affectedCount === 1 ? '' : 's'} affected)</span>
                </span>
                <span className="text-[10px] font-semibold text-rose-700">No scores, weights, or formulas</span>
              </div>
              <div className="bg-white rounded-xl border border-rose-100 p-3 text-xs space-y-1">
                <p className="font-bold text-slate-900">Subject: {previewData.message_preview.subject}</p>
                <p className="text-slate-600 whitespace-pre-wrap leading-relaxed">{previewData.message_preview.message}</p>
              </div>
              {finalizeNow && (
                <label className="flex items-start gap-2 text-xs font-semibold text-rose-900 cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={confirmNotify}
                    onChange={(e) => setConfirmNotify(e.target.checked)}
                    className="mt-0.5 rounded border-rose-300 text-rose-600 focus:ring-rose-500"
                  />
                  <span>
                    I confirm setting {affectedCount} non-shortlisted applicant(s) to Not Selected and sending this notification.
                  </span>
                </label>
              )}
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Notes (Optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Batch for Plant 2 expansion, initial interview slots target for next week."
              rows={2}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm text-slate-800 focus:bg-white focus:border-purple-600 focus:ring-2 focus:ring-purple-600/10 outline-none resize-none"
            />
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-start gap-2">
            <CheckCircle2 size={15} className="text-emerald-600 shrink-0 mt-0.5" />
            <span>
              Included applications move to <strong>Shortlisted</strong> and are recorded in status audit history.
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
              disabled={isSubmitting || candidateIds.length === 0 || (requiresExplicitConfirm && !confirmNotify)}
              className="px-5 py-2.5 bg-purple-700 hover:bg-purple-800 text-white text-xs sm:text-sm font-bold rounded-xl shadow-md shadow-purple-200 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              <Layers size={14} />
              <span>{isSubmitting ? 'Saving...' : finalizeNow ? 'Finalize Shortlist' : 'Save Draft Shortlist'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FinalizeShortlistModal;
