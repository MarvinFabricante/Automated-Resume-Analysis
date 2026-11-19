import React, { useEffect, useState } from 'react';
import {
  X,
  Calendar,
  Clock,
  User,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RotateCcw,
} from 'lucide-react';
import {
  useGetAvailableSlotsMutation,
  useCandidateRescheduleInterviewMutation,
} from '../../../redux/api/apiSlice';

export function isInterviewMissed(interview: any): boolean {
  if (!interview) return false;
  const statusUpper = String(interview.status || '').toUpperCase();
  if (statusUpper === 'COMPLETED' || statusUpper === 'CANCELED' || statusUpper === 'CANCELLED') {
    return false;
  }
  if (interview.is_missed || statusUpper === 'MISSED' || statusUpper === 'NO_SHOW') {
    return true;
  }
  const endRef = interview.end_time || interview.start_time;
  if (!endRef) return false;
  return new Date(endRef).getTime() < Date.now();
}

function toLocalDateStr(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getNextWeekdayDateStr(): string {
  const d = new Date();
  if (d.getHours() >= 16) {
    d.setDate(d.getDate() + 1);
  }
  while (d.getDay() === 0 || d.getDay() === 6) {
    d.setDate(d.getDate() + 1);
  }
  return toLocalDateStr(d);
}

function isWeekday(dateStr: string): boolean {
  if (!dateStr) return false;
  const d = new Date(`${dateStr}T00:00:00`);
  const day = d.getDay();
  return day !== 0 && day !== 6;
}

function formatSlotTime(isoStr: string): string {
  return new Date(isoStr).toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

function toNaiveLocalIso(isoOrDate: string): string {
  const d = new Date(isoOrDate);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}T${hh}:${min}:00`;
}

interface CandidateRescheduleModalProps {
  isOpen: boolean;
  onClose: () => void;
  interview: any;
  onSuccess?: () => void;
}

const CandidateRescheduleModal: React.FC<CandidateRescheduleModalProps> = ({
  isOpen,
  onClose,
  interview,
  onSuccess,
}) => {
  const [selectedDate, setSelectedDate] = useState<string>(getNextWeekdayDateStr);
  const [availableSlots, setAvailableSlots] = useState<Array<{ start_time: string; end_time: string }>>([]);
  const [alternativeDates, setAlternativeDates] = useState<string[]>([]);
  const [availabilityMessage, setAvailabilityMessage] = useState<string>('');
  const [selectedSlot, setSelectedSlot] = useState<{ start_time: string; end_time: string } | null>(null);
  const [reason, setReason] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');

  const [getAvailableSlots, { isLoading: isLoadingSlots }] = useGetAvailableSlotsMutation();
  const [rescheduleInterview, { isLoading: isSubmitting }] = useCandidateRescheduleInterviewMutation();

  const todayStr = toLocalDateStr(new Date());

  useEffect(() => {
    if (!isOpen) return;
    setSelectedDate(getNextWeekdayDateStr());
    setSelectedSlot(null);
    setReason('');
    setErrorMsg('');
    setSuccessMsg('');
  }, [isOpen, interview?.id]);

  useEffect(() => {
    if (!isOpen || !interview || !selectedDate) return;
    if (!isWeekday(selectedDate)) {
      setAvailableSlots([]);
      setAlternativeDates([]);
      setAvailabilityMessage('Interviews are only held on weekdays (Monday – Friday).');
      setSelectedSlot(null);
      return;
    }

    let cancelled = false;
    const fetchAvailability = async () => {
      setErrorMsg('');
      setSelectedSlot(null);
      try {
        const res = await getAvailableSlots({
          start_date: `${selectedDate}T09:00:00`,
          end_date: `${selectedDate}T17:00:00`,
          hr_id: interview.interviewer_id || undefined,
        }).unwrap();

        if (cancelled) return;

        const rawSlots = Array.isArray(res) ? res : res?.slots || [];
        const nowMs = Date.now();
        const futureSlots = rawSlots.filter(
          (slot: any) => new Date(slot.start_time).getTime() > nowMs
        );
        setAvailableSlots(futureSlots);
        setAlternativeDates(!Array.isArray(res) && Array.isArray(res?.alternative_dates) ? res.alternative_dates : []);
        setAvailabilityMessage(
          futureSlots.length === 0
            ? (!Array.isArray(res) && res?.message) || 'No open slots left on this date.'
            : ''
        );
      } catch (err: any) {
        if (!cancelled) {
          setAvailableSlots([]);
          setAvailabilityMessage(err?.data?.detail || 'Could not load interviewer availability.');
        }
      }
    };

    fetchAvailability();
    return () => {
      cancelled = true;
    };
  }, [isOpen, interview, selectedDate, getAvailableSlots]);

  if (!isOpen || !interview) return null;

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSlot) {
      setErrorMsg('Please choose an available time slot.');
      return;
    }
    setErrorMsg('');
    try {
      await rescheduleInterview({
        interviewId: interview.id,
        start_time: toNaiveLocalIso(selectedSlot.start_time),
        end_time: toNaiveLocalIso(selectedSlot.end_time),
        reason: reason.trim() || undefined,
      }).unwrap();

      setSuccessMsg('Interview rescheduled! Your Recruitment Journey has been updated.');
      setTimeout(() => {
        if (onSuccess) onSuccess();
        onClose();
      }, 1200);
    } catch (err: any) {
      setErrorMsg(err?.data?.detail || 'Failed to reschedule interview. Please choose another available slot.');
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="candidate-reschedule-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center shrink-0">
              <RotateCcw size={18} />
            </div>
            <div>
              <h2 id="candidate-reschedule-title" className="text-base sm:text-lg font-black text-slate-900">
                Reschedule Missed Interview
              </h2>
              <p className="text-xs text-slate-500 font-medium">
                Select an open slot from the interviewer’s availability
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close reschedule modal"
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleConfirm} className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {/* Interview Summary */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/70 space-y-1.5">
            <p className="text-sm font-black text-slate-900">{interview.title}</p>
            {interview.interviewer_name && (
              <p className="text-xs text-slate-600 font-semibold flex items-center gap-1.5">
                <User size={13} className="text-[#D10043]" />
                <span>Interviewer: <strong>{interview.interviewer_name}</strong></span>
              </p>
            )}
            <p className="text-xs text-amber-700 font-semibold flex items-center gap-1.5">
              <Clock size={13} />
              <span>Missed schedule: {new Date(interview.start_time).toLocaleString()}</span>
            </p>
          </div>

          {successMsg && (
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold flex items-center gap-2">
              <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {errorMsg && (
            <div role="alert" className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold flex items-center gap-2">
              <AlertCircle size={16} className="shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Date Picker */}
          <div>
            <label htmlFor="reschedule-date" className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-2">
              Preferred Date (Weekdays Only)
            </label>
            <div className="relative">
              <Calendar size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              <input
                id="reschedule-date"
                type="date"
                min={todayStr}
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                required
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white text-sm font-semibold text-slate-800 focus:outline-none focus:border-[#D10043] focus:ring-2 focus:ring-[#D10043]/15"
              />
            </div>
          </div>

          {/* Available Slots */}
          <div>
            <span className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-2">
              Interviewer’s Available Slots
            </span>

            {isLoadingSlots ? (
              <div className="py-6 flex items-center justify-center gap-2 text-xs font-semibold text-slate-500 bg-slate-50 rounded-2xl border border-slate-100">
                <Loader2 size={16} className="animate-spin text-[#D10043]" />
                <span>Checking interviewer’s calendar availability...</span>
              </div>
            ) : availableSlots.length > 0 ? (
              <div className="grid grid-cols-2 gap-2">
                {availableSlots.map((slot) => {
                  const isSelected = selectedSlot?.start_time === slot.start_time;
                  return (
                    <button
                      key={slot.start_time}
                      type="button"
                      onClick={() => setSelectedSlot(slot)}
                      className={`px-3 py-2.5 rounded-xl border text-xs font-bold transition-all cursor-pointer text-center ${
                        isSelected
                          ? 'bg-[#D10043] text-white border-[#D10043] shadow-sm shadow-[#D10043]/25'
                          : 'bg-white text-slate-700 border-slate-200 hover:border-[#D10043]/50 hover:bg-rose-50/40'
                      }`}
                    >
                      {formatSlotTime(slot.start_time)} – {formatSlotTime(slot.end_time)}
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200/70 space-y-3">
                <p className="text-xs font-semibold text-amber-800">
                  {availabilityMessage || 'No available slots on this date.'}
                </p>
                {alternativeDates.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold text-slate-600 block">
                      Next available dates:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {alternativeDates.map((altDate) => (
                        <button
                          key={altDate}
                          type="button"
                          onClick={() => setSelectedDate(altDate)}
                          className="px-2.5 py-1 rounded-lg bg-white border border-amber-300 text-xs font-bold text-amber-900 hover:bg-amber-100 cursor-pointer"
                        >
                          {new Date(`${altDate}T00:00:00`).toLocaleDateString('en-US', {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Optional Reason */}
          <div>
            <label htmlFor="reschedule-reason" className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
              Note / Reason (Optional)
            </label>
            <input
              id="reschedule-reason"
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Missed previous call/time, available at this slot"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white text-xs sm:text-sm text-slate-800 focus:outline-none focus:border-[#D10043]"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !selectedSlot || Boolean(successMsg)}
              className="px-5 py-2.5 rounded-xl bg-[#D10043] hover:bg-[#b00038] text-white text-xs font-black uppercase tracking-wider flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shadow-sm"
            >
              {isSubmitting && <Loader2 size={14} className="animate-spin" />}
              <span>Confirm Reschedule</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CandidateRescheduleModal;
