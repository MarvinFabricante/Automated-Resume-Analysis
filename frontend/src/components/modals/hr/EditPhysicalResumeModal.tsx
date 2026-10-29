import React, { useState, useEffect } from 'react';
import {
  X,
  FolderArchive,
  User,
  Briefcase,
  Calendar,
  Mail,
  Phone,
  AlertCircle,
  Loader2,
  Tag
} from 'lucide-react';
import { useUpdatePhysicalResumeMutation, useGetJobsQuery } from '../../../redux/api/apiSlice';

interface EditPhysicalResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
  resume: any;
  onSuccess?: (result: any) => void;
}

const PRESET_LOCATIONS = [
  'Cabinet A • Shelf 1',
  'Cabinet A • Shelf 2',
  'Cabinet B • Walk-in Folder',
  'Plant 2 • HR Front Desk',
  'Administration • Box #12',
  'Ceramics Division • Vault',
];

const EditPhysicalResumeModal: React.FC<EditPhysicalResumeModalProps> = ({
  isOpen,
  onClose,
  resume,
  onSuccess,
}) => {
  const [updateResume, { isLoading }] = useUpdatePhysicalResumeMutation();
  const { data: jobs = [] } = useGetJobsQuery();

  const [formData, setFormData] = useState({
    candidate_name: '',
    candidate_email: '',
    candidate_phone: '',
    target_job_id: '',
    target_job_title: '',
    physical_location: '',
    submission_date: '',
    status: 'RECEIVED',
    notes: '',
  });

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (resume) {
      setFormData({
        candidate_name: resume.candidate_name || '',
        candidate_email: resume.candidate_email || '',
        candidate_phone: resume.candidate_phone || '',
        target_job_id: resume.target_job_id ? String(resume.target_job_id) : '',
        target_job_title: resume.target_job_title || '',
        physical_location: resume.physical_location || 'General HR Archive',
        submission_date: resume.submission_date ? resume.submission_date.split('T')[0] : '',
        status: resume.status || 'RECEIVED',
        notes: resume.notes || '',
      });
    }
  }, [resume]);

  if (!isOpen || !resume) return null;

  const handleJobSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (!val) {
      setFormData((prev) => ({ ...prev, target_job_id: '', target_job_title: '' }));
      return;
    }
    const found = jobs.find((j: any) => String(j.id) === String(val));
    setFormData((prev) => ({
      ...prev,
      target_job_id: val,
      target_job_title: found ? found.title || found.job_title : '',
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!formData.candidate_name.trim()) {
      setErrorMessage('Candidate name is required.');
      return;
    }

    try {
      const body: any = {
        candidate_name: formData.candidate_name.trim(),
        candidate_email: formData.candidate_email.trim() || null,
        candidate_phone: formData.candidate_phone.trim() || null,
        target_job_id: formData.target_job_id ? parseInt(formData.target_job_id) : null,
        target_job_title: formData.target_job_title || null,
        physical_location: formData.physical_location.trim(),
        status: formData.status,
        notes: formData.notes.trim() || null,
      };
      if (formData.submission_date) {
        body.submission_date = formData.submission_date;
      }

      const res = await updateResume({ id: resume.id, body }).unwrap();
      if (onSuccess) {
        onSuccess(res);
      }
      onClose();
    } catch (err: any) {
      console.error('Failed to update physical resume:', err);
      setErrorMessage(err?.data?.detail || err?.message || 'Failed to update physical resume.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/75 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl shadow-2xl max-w-xl w-full overflow-hidden border border-slate-200 animate-in zoom-in-95 duration-200">
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50 to-white">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-[#D60041] text-white flex items-center justify-center shadow-xs">
              <FolderArchive size={20} />
            </div>
            <div>
              <h3 className="text-base font-black text-slate-900 tracking-tight">
                Edit Filing Details
              </h3>
              <p className="text-xs text-slate-500 font-medium">
                Update storage location, candidate status, or remarks
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMessage && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-xs text-rose-700 font-semibold">
              <AlertCircle size={15} />
              <span>{errorMessage}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1">
              Candidate Name
            </label>
            <input
              type="text"
              required
              value={formData.candidate_name}
              onChange={(e) => setFormData({ ...formData, candidate_name: e.target.value })}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
            />
          </div>

          <div className="bg-slate-50 p-3.5 rounded-2xl border border-slate-200 space-y-2">
            <label className="block text-xs font-black uppercase tracking-wider text-slate-800">
              Physical Storage Location Ref
            </label>
            <input
              type="text"
              required
              value={formData.physical_location}
              onChange={(e) => setFormData({ ...formData, physical_location: e.target.value })}
              className="w-full px-3.5 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
            />
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              {PRESET_LOCATIONS.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setFormData({ ...formData, physical_location: preset })}
                  className={`text-[10px] font-semibold px-2 py-0.5 rounded-lg border transition-all cursor-pointer ${
                    formData.physical_location === preset
                      ? 'bg-[#D60041] text-white border-[#D60041]'
                      : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                  }`}
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1">
                Filing Status
              </label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
              >
                <option value="RECEIVED">RECEIVED</option>
                <option value="UNDER_REVIEW">UNDER REVIEW</option>
                <option value="SHORTLISTED">SHORTLISTED</option>
                <option value="HIRED">HIRED</option>
                <option value="ARCHIVED">ARCHIVED</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1">
                Submission Date
              </label>
              <input
                type="date"
                value={formData.submission_date}
                onChange={(e) => setFormData({ ...formData, submission_date: e.target.value })}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1">
              Target Requisition
            </label>
            <select
              value={formData.target_job_id}
              onChange={handleJobSelect}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
            >
              <option value="">Unassigned / Open</option>
              {jobs.map((job: any) => (
                <option key={job.id} value={job.id}>
                  {job.title || job.job_title}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={formData.candidate_email}
                onChange={(e) => setFormData({ ...formData, candidate_email: e.target.value })}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
              />
            </div>
            <div>
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1">
                Phone
              </label>
              <input
                type="text"
                value={formData.candidate_phone}
                onChange={(e) => setFormData({ ...formData, candidate_phone: e.target.value })}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1">
              HR Notes
            </label>
            <textarea
              rows={2}
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] resize-none"
            />
          </div>

          <div className="pt-2 border-t border-slate-100 flex items-center justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2 bg-[#D60041] hover:bg-[#B50037] text-white rounded-xl text-xs font-bold shadow-xs transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              {isLoading ? <Loader2 size={14} className="animate-spin" /> : null}
              <span>Save Changes</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditPhysicalResumeModal;
