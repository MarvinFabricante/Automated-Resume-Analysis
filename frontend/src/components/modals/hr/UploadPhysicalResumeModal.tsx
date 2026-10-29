import React, { useState, useRef } from 'react';
import {
  X,
  Upload,
  FileText,
  FolderArchive,
  User,
  Briefcase,
  Calendar,
  Mail,
  Phone,
  Info,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  Tag
} from 'lucide-react';
import { useUploadPhysicalResumeMutation, useGetJobsQuery } from '../../../redux/api/apiSlice';

interface UploadPhysicalResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
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

const UploadPhysicalResumeModal: React.FC<UploadPhysicalResumeModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [uploadResume, { isLoading }] = useUploadPhysicalResumeMutation();
  const { data: jobs = [] } = useGetJobsQuery();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);

  const [formData, setFormData] = useState({
    candidate_name: '',
    candidate_email: '',
    candidate_phone: '',
    target_job_id: '',
    target_job_title: '',
    physical_location: 'Cabinet A • Shelf 1',
    submission_date: new Date().toISOString().split('T')[0],
    status_val: 'RECEIVED',
    notes: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file: File) => {
    setSelectedFile(file);
    setErrors((prev) => ({ ...prev, file: '' }));

    // Pre-fill candidate name if empty and filename looks like a name
    if (!formData.candidate_name) {
      const cleanName = file.name
        .replace(/\.[^/.]+$/, '')
        .replace(/[-_]/g, ' ')
        .replace(/(resume|cv|physical|scan)/gi, '')
        .trim();
      if (cleanName.length > 2) {
        setFormData((prev) => ({ ...prev, candidate_name: cleanName }));
      }
    }
  };

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

    const newErrors: Record<string, string> = {};
    if (!selectedFile) {
      newErrors.file = 'Please upload or select the scanned resume file.';
    }
    if (!formData.candidate_name.trim()) {
      newErrors.candidate_name = 'Candidate full name is required.';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    try {
      const data = new FormData();
      if (selectedFile) {
        data.append('file', selectedFile);
      }
      data.append('candidate_name', formData.candidate_name.trim());
      if (formData.candidate_email.trim()) {
        data.append('candidate_email', formData.candidate_email.trim());
      }
      if (formData.candidate_phone.trim()) {
        data.append('candidate_phone', formData.candidate_phone.trim());
      }
      if (formData.target_job_id) {
        data.append('target_job_id', formData.target_job_id);
      }
      if (formData.target_job_title) {
        data.append('target_job_title', formData.target_job_title);
      }
      data.append('physical_location', formData.physical_location.trim() || 'General HR Archive');
      if (formData.submission_date) {
        data.append('submission_date', formData.submission_date);
      }
      data.append('status_val', formData.status_val);
      if (formData.notes.trim()) {
        data.append('notes', formData.notes.trim());
      }

      const res = await uploadResume(data).unwrap();
      if (onSuccess) {
        onSuccess(res);
      }
      onClose();
    } catch (err: any) {
      console.error('Failed to upload physical resume:', err);
      setErrorMessage(err?.data?.detail || err?.message || 'Failed to upload physical resume. Please try again.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/75 backdrop-blur-xs flex items-center justify-center p-2.5 sm:p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl sm:rounded-3xl shadow-2xl max-w-2xl w-full max-h-[92vh] flex flex-col overflow-hidden border border-slate-200 animate-in zoom-in-95 duration-200">
        {/* HEADER */}
        <div className="px-4 sm:px-6 py-4 sm:py-5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50 to-white shrink-0">
          <div className="flex items-center space-x-3 min-w-0">
            <div className="w-10 h-10 rounded-xl sm:rounded-2xl bg-gradient-to-br from-[#D60041] to-[#B50037] text-white flex items-center justify-center shadow-xs shrink-0">
              <FolderArchive size={20} />
            </div>
            <div className="min-w-0">
              <h3 className="text-sm sm:text-base font-black text-slate-900 tracking-tight truncate">
                Store Physical Resume
              </h3>
              <p className="text-[11px] sm:text-xs text-slate-500 font-medium truncate">
                Upload paper / walk-in scanned resume and assign storage filing location
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer shrink-0 ml-2"
          >
            <X size={18} />
          </button>
        </div>

        {/* FORM */}
        <form onSubmit={handleSubmit} className="p-4 sm:p-6 space-y-4 sm:space-y-5 overflow-y-auto flex-1 custom-scrollbar">
          {errorMessage && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-2xl flex items-center gap-2.5 text-xs text-rose-700 font-semibold animate-in shake duration-300">
              <AlertCircle size={16} className="shrink-0 text-rose-600" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* FILE UPLOAD DROPZONE */}
          <div>
            <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-2">
              Scanned Resume Document <span className="text-[#D60041]">*</span>
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.png,.jpg,.jpeg,.webp"
              onChange={handleFileChange}
              className="hidden"
            />

            {!selectedFile ? (
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center transition-all cursor-pointer flex flex-col items-center justify-center ${
                  dragActive
                    ? 'border-[#D60041] bg-pink-50/50'
                    : 'border-slate-200 hover:border-[#D60041] hover:bg-slate-50/80 bg-slate-50/40'
                }`}
              >
                <div className="w-12 h-12 rounded-2xl bg-white shadow-xs border border-slate-200 text-[#D60041] flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <Upload size={22} />
                </div>
                <p className="text-xs sm:text-sm font-bold text-slate-900 mb-1">
                  Click to select scan or drag & drop here
                </p>
                <p className="text-[11px] text-slate-500 font-medium max-w-sm">
                  Supports PDF, Scanned Photos (PNG, JPG, WEBP), and Word Documents (DOCX) up to 25MB
                </p>
              </div>
            ) : (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-between gap-3">
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-pink-100 text-[#D60041] flex items-center justify-center shrink-0">
                    <FileText size={20} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-black text-slate-900 truncate">{selectedFile.name}</p>
                    <p className="text-[11px] text-slate-500 font-medium">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to archive
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedFile(null)}
                  className="px-2.5 py-1 text-xs font-bold text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                >
                  Change
                </button>
              </div>
            )}
            {errors.file && <p className="text-xs text-rose-600 font-medium mt-1">{errors.file}</p>}
          </div>

          {/* CANDIDATE NAME & TARGET REQUISITION */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
                Candidate Full Name <span className="text-[#D60041]">*</span>
              </label>
              <div className="relative">
                <input
                  type="text"
                  required
                  placeholder="e.g. Juan dela Cruz"
                  value={formData.candidate_name}
                  onChange={(e) => {
                    setFormData({ ...formData, candidate_name: e.target.value });
                    setErrors({ ...errors, candidate_name: '' });
                  }}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all"
                />
                <User size={15} className="absolute right-3.5 top-3 text-slate-400 pointer-events-none" />
              </div>
              {errors.candidate_name && (
                <p className="text-xs text-rose-600 font-medium mt-1">{errors.candidate_name}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
                Target Requisition / Position
              </label>
              <div className="relative">
                <select
                  value={formData.target_job_id}
                  onChange={handleJobSelect}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all appearance-none cursor-pointer"
                >
                  <option value="">Select active job vacancy (Optional)</option>
                  {jobs.map((job: any) => (
                    <option key={job.id} value={job.id}>
                      {job.title || job.job_title} ({job.department || 'General'})
                    </option>
                  ))}
                </select>
                <Briefcase size={15} className="absolute right-3.5 top-3 text-slate-400 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* PHYSICAL FILING LOCATION (Core Feature) */}
          <div className="bg-slate-50/80 p-4 rounded-2xl border border-slate-200 space-y-2.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-black uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                <FolderArchive size={14} className="text-[#D60041]" />
                Physical Filing Location / Reference Code <span className="text-[#D60041]">*</span>
              </label>
              <span className="text-[10px] text-slate-500 font-bold uppercase">Paper Vault Ref</span>
            </div>
            <input
              type="text"
              required
              placeholder="e.g. Cabinet A • Shelf 2 • Folder 14"
              value={formData.physical_location}
              onChange={(e) => setFormData({ ...formData, physical_location: e.target.value })}
              className="w-full px-3.5 py-2.5 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all"
            />
            {/* Quick Preset Tags */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1 mr-1">
                <Tag size={10} /> Quick Select:
              </span>
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

          {/* SUBMISSION DATE & STATUS */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
                Physical Hand-in Date
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={formData.submission_date}
                  onChange={(e) => setFormData({ ...formData, submission_date: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all"
                />
                <Calendar size={15} className="absolute right-3.5 top-3 text-slate-400 pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
                Initial Status
              </label>
              <select
                value={formData.status_val}
                onChange={(e) => setFormData({ ...formData, status_val: e.target.value })}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all cursor-pointer"
              >
                <option value="RECEIVED">RECEIVED (Archived)</option>
                <option value="UNDER_REVIEW">UNDER REVIEW</option>
                <option value="SHORTLISTED">SHORTLISTED</option>
                <option value="HIRED">HIRED</option>
                <option value="ARCHIVED">ARCHIVED</option>
              </select>
            </div>
          </div>

          {/* OPTIONAL CONTACT DETAILS */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
                Candidate Email (Optional)
              </label>
              <div className="relative">
                <input
                  type="email"
                  placeholder="juan@example.com"
                  value={formData.candidate_email}
                  onChange={(e) => setFormData({ ...formData, candidate_email: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all"
                />
                <Mail size={15} className="absolute right-3.5 top-3 text-slate-400 pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
                Phone Number (Optional)
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="+63 912 345 6789"
                  value={formData.candidate_phone}
                  onChange={(e) => setFormData({ ...formData, candidate_phone: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all"
                />
                <Phone size={15} className="absolute right-3.5 top-3 text-slate-400 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* HR STAFF NOTES */}
          <div>
            <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
              Receiving HR Remarks & Submission Context
            </label>
            <textarea
              rows={2}
              placeholder="e.g. Walk-in applicant handed resume personally at Plant 2 gate. Experienced in tile press operations."
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all resize-none"
            />
          </div>

          {/* ACTION BUTTONS (Sticky footer with backdrop blur) */}
          <div className="sticky bottom-0 bg-white/95 backdrop-blur-xs pt-3 pb-1 border-t border-slate-100 flex items-center justify-end space-x-3 -mx-4 sm:-mx-6 px-4 sm:px-6 mt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2.5 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2.5 bg-[#D60041] hover:bg-[#B50037] text-white rounded-xl text-xs font-bold shadow-xs hover:shadow-md hover:shadow-pink-500/25 active:scale-95 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  <span>Archiving Resume...</span>
                </>
              ) : (
                <>
                  <FolderArchive size={15} />
                  <span>Store Physical Resume</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UploadPhysicalResumeModal;
