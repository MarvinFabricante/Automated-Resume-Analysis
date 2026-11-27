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
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Check,
  Building2,
  MapPin,
  GraduationCap,
  Award,
  AlertTriangle,
  HelpCircle
} from 'lucide-react';
import { useUploadPhysicalResumeMutation, useGetJobsQuery, useLazyCheckImportDuplicateQuery } from '../../../redux/api/apiSlice';
import { API_BASE_URL } from '../../../services/api';
import HelpTooltip from '../../common/HelpTooltip';
import { SelectWithOther, MultiSelectDropdownWithOther } from '../../common/SelectWithOther';
import {
  PH_LOCATIONS,
  DEGREE_OPTIONS,
  EXPERIENCE_LEVEL_OPTIONS,
  SKILL_OPTIONS,
  CERTIFICATION_OPTIONS,
  PHYSICAL_ARCHIVE_LOCATIONS,
} from '../../../data/formOptions';

interface UploadPhysicalResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: any) => void;
}

const splitCsvItems = (raw: string): string[] =>
  raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

const ALLOWED_EXTS = ['.pdf', '.docx', '.doc', '.txt'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const STEPS = [
  { step: 1, title: 'Upload', desc: 'Choose file' },
  { step: 2, title: 'Review Details', desc: 'Verify info' },
  { step: 3, title: 'Application Info', desc: 'Role & origin' },
  { step: 4, title: 'Confirm', desc: 'Finish import' },
];

const UploadPhysicalResumeModal: React.FC<UploadPhysicalResumeModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [uploadResume, { isLoading: isUploading }] = useUploadPhysicalResumeMutation();
  const [triggerCheckDuplicate] = useLazyCheckImportDuplicateQuery();
  const { data: rawJobs = [] } = useGetJobsQuery();

  // Active jobs only
  const activeJobs = React.useMemo(() => {
    return (rawJobs || []).filter((j: any) => j.is_active !== false);
  }, [rawJobs]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);

  // Form State
  const [formData, setFormData] = useState({
    candidate_name: '',
    candidate_email: '',
    candidate_phone: '',
    location: '',
    education: '',
    experience: '',
    skills: '',
    certifications: '',
    target_job_id: '',
    target_job_title: '',
    import_origin: 'Walk-in',
    physical_location: 'Cabinet A • Shelf 1',
    submission_date: new Date().toISOString().split('T')[0],
    notes: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleReset = () => {
    setCurrentStep(1);
    setSelectedFile(null);
    setFormData({
      candidate_name: '',
      candidate_email: '',
      candidate_phone: '',
      location: '',
      education: '',
      experience: '',
      skills: '',
      certifications: '',
      target_job_id: '',
      target_job_title: '',
      import_origin: 'Walk-in',
      physical_location: 'Cabinet A • Shelf 1',
      submission_date: new Date().toISOString().split('T')[0],
      notes: '',
    });
    setErrors({});
    setErrorMessage(null);
    setDuplicateWarning(null);
    setIsExtracting(false);
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };

  // Step 1: File selection & auto-extraction
  const handleFileSelected = async (file: File) => {
    setErrorMessage(null);
    setErrors({});

    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      setErrorMessage(`Unsupported file format '${ext}'. Please choose a PDF, DOCX, or TXT file.`);
      return;
    }

    if (file.size === 0) {
      setErrorMessage('The selected file is blank (0 bytes). Please choose a valid resume document.');
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setErrorMessage(`File is too large (${(file.size / (1024 * 1024)).toFixed(1)} MB). The maximum allowed size is 10 MB.`);
      return;
    }

    setSelectedFile(file);
    setIsExtracting(true);

    try {
      const parseData = new FormData();
      parseData.append('file', file);

      const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
      const res = await fetch(`${API_BASE_URL}/candidate/parse-resume`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: parseData,
      });

      if (!res.ok) {
        let detailMsg =
          'Only resume or CV documents are accepted. Please upload a valid resume file (PDF, DOCX, DOC, or TXT).';
        try {
          const errPayload = await res.json();
          if (typeof errPayload?.detail === 'string' && errPayload.detail.trim()) {
            detailMsg = errPayload.detail;
          } else if (typeof errPayload?.message === 'string' && errPayload.message.trim()) {
            detailMsg = errPayload.message;
          }
        } catch {
          // keep fallback message
        }
        setSelectedFile(null);
        setFormData((prev) => ({
          ...prev,
          candidate_name: '',
          candidate_email: '',
          candidate_phone: '',
          location: '',
          education: '',
          experience: '',
          skills: '',
          certifications: '',
        }));
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        setErrorMessage(detailMsg);
        setErrors({ file: detailMsg });
        return;
      }

      const parsed = await res.json();
      const extractedName = parsed.fullname || parsed.name || parsed.candidate_name || '';
      const extractedEmail = parsed.email || parsed.candidate_email || '';
      const extractedPhone = parsed.phone || parsed.candidate_phone || '';
      const extractedLocation = parsed.location || '';
      const extractedDegree = parsed.degree || parsed.highest_degree || parsed.education || '';
      const extractedExp = parsed.job_title
        ? `${parsed.job_title}${parsed.company ? ` at ${parsed.company}` : ''}`
        : parsed.experience || '';
      const extractedSkills = Array.isArray(parsed.skills_list)
        ? parsed.skills_list.join(', ')
        : Array.isArray(parsed.skills)
          ? parsed.skills.join(', ')
          : parsed.skills || '';
      const extractedCerts = parsed.certifications || parsed.candidate_certifications || '';

      setFormData((prev) => ({
        ...prev,
        candidate_name: extractedName,
        candidate_email: extractedEmail,
        candidate_phone: extractedPhone,
        location: extractedLocation,
        education: extractedDegree,
        experience: extractedExp,
        skills: extractedSkills,
        certifications: extractedCerts,
      }));
    } catch (parseErr) {
      console.warn('Resume validation/pre-parsing failed:', parseErr);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      const msg = 'Could not verify the uploaded file as a resume. Please check the file and try again.';
      setErrorMessage(msg);
      setErrors({ file: msg });
    } finally {
      setIsExtracting(false);
    }
  };

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

  // Step 1 -> Step 2 validation
  const handleProceedToStep2 = () => {
    if (!selectedFile) {
      setErrors({ file: 'Please select a resume file (PDF, DOCX, or TXT) to continue.' });
      return;
    }
    setErrors({});
    setCurrentStep(2);
  };

  // Step 2 -> Step 3 validation
  const handleProceedToStep3 = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.candidate_name.trim()) {
      newErrors.candidate_name = 'Candidate full name is required.';
    }
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    setErrors({});
    setCurrentStep(3);
  };

  // Step 3: Check duplicate on job/email change
  const handleJobSelect = async (jobId: string) => {
    const selected = activeJobs.find((j: any) => String(j.id) === String(jobId));
    setFormData((prev) => ({
      ...prev,
      target_job_id: jobId,
      target_job_title: selected?.job_title || selected?.title || '',
    }));

    if (formData.candidate_email && jobId) {
      try {
        const res = await triggerCheckDuplicate({ email: formData.candidate_email, jobId }).unwrap();
        if (res?.duplicate) {
          setDuplicateWarning(res.message || 'A candidate with this email has already applied for this position.');
        } else {
          setDuplicateWarning(null);
        }
      } catch {
        setDuplicateWarning(null);
      }
    }
  };

  // Step 3 -> Step 4 validation
  const handleProceedToStep4 = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.target_job_id) {
      newErrors.target_job_id = 'Please choose the position the applicant is applying for.';
    }
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    setErrors({});
    setCurrentStep(4);
  };

  // Final submission in Step 4
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!selectedFile) {
      setErrorMessage('Resume file is missing. Please restart from Step 1.');
      return;
    }

    try {
      const uploadPayload = new FormData();
      uploadPayload.append('file', selectedFile);
      uploadPayload.append('candidate_name', formData.candidate_name.trim());
      if (formData.candidate_email.trim()) {
        uploadPayload.append('candidate_email', formData.candidate_email.trim());
      }
      if (formData.candidate_phone.trim()) {
        uploadPayload.append('candidate_phone', formData.candidate_phone.trim());
      }
      if (formData.target_job_id) {
        uploadPayload.append('target_job_id', formData.target_job_id);
      }
      if (formData.target_job_title) {
        uploadPayload.append('target_job_title', formData.target_job_title);
      }
      uploadPayload.append('import_origin', formData.import_origin || 'Walk-in');
      uploadPayload.append('physical_location', formData.physical_location.trim() || 'General HR Archive');
      if (formData.submission_date) {
        uploadPayload.append('submission_date', formData.submission_date);
      }
      uploadPayload.append('status_val', 'SUBMITTED');

      if (formData.location) uploadPayload.append('location', formData.location.trim());
      if (formData.education) uploadPayload.append('education', formData.education.trim());
      if (formData.experience) uploadPayload.append('experience', formData.experience.trim());
      if (formData.skills) uploadPayload.append('skills', formData.skills.trim());
      if (formData.certifications) uploadPayload.append('certifications', formData.certifications.trim());
      if (formData.notes) uploadPayload.append('notes', formData.notes.trim());

      const res = await uploadResume(uploadPayload).unwrap();
      if (onSuccess) {
        onSuccess(res);
      }
      handleClose();
    } catch (err: any) {
      console.error('Failed to import resume:', err);
      setErrorMessage(err?.data?.detail || err?.message || 'Failed to import resume. Please try again.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/75 backdrop-blur-xs flex items-center justify-center p-2.5 sm:p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl sm:rounded-3xl shadow-2xl max-w-2xl w-full max-h-[92vh] flex flex-col overflow-hidden border border-slate-200 animate-in zoom-in-95 duration-200">

        {/* MODAL HEADER */}
        <div className="px-5 sm:px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50 to-white shrink-0">
          <div className="flex items-center space-x-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#D60041] to-[#B50037] text-white flex items-center justify-center shadow-xs shrink-0">
              <FolderArchive size={20} />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <h3 className="text-sm sm:text-base font-black text-slate-900 tracking-tight truncate">
                  Import Resumes
                </h3>
                <HelpTooltip text="Add resumes that did not come through this website, such as resumes from other job sites, emails or walk-ins, so they can be screened with the others." />
              </div>
              <p className="text-[11px] sm:text-xs text-slate-500 font-medium truncate">
                Screen walk-in, emailed, or job board applicants with the same automated matching.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1.5 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer shrink-0 ml-2"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* STEP PROGRESS INDICATOR */}
        <div className="bg-slate-50/80 px-6 py-3 border-b border-slate-100 shrink-0">
          <div className="flex items-center justify-between">
            {STEPS.map((s, idx) => {
              const isPassed = currentStep > s.step;
              const isCurrent = currentStep === s.step;
              return (
                <React.Fragment key={s.step}>
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-black transition-all ${isPassed
                        ? 'bg-emerald-500 text-white shadow-xs'
                        : isCurrent
                          ? 'bg-[#D60041] text-white ring-4 ring-[#D60041]/20 shadow-xs'
                          : 'bg-slate-200 text-slate-500'
                        }`}
                    >
                      {isPassed ? <Check size={14} strokeWidth={3} /> : s.step}
                    </div>
                    <div className="hidden sm:block text-left">
                      <p className={`text-[11px] font-bold leading-tight ${isCurrent ? 'text-slate-900' : 'text-slate-400'}`}>
                        {s.title}
                      </p>
                      <p className="text-[9px] text-slate-400 font-medium">{s.desc}</p>
                    </div>
                  </div>
                  {idx < STEPS.length - 1 && (
                    <div
                      className={`flex-1 mx-2 sm:mx-3 h-0.5 rounded transition-all ${currentStep > s.step ? 'bg-emerald-500' : 'bg-slate-200'
                        }`}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* MODAL BODY: ONLY CURRENT STEP CONTENT */}
        <div className="p-5 sm:p-6 overflow-y-auto flex-1 custom-scrollbar">
          {errorMessage && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-2xl flex items-start gap-2.5 text-xs text-rose-700 font-semibold animate-in shake duration-300">
              <AlertCircle size={16} className="shrink-0 text-rose-600 mt-0.5" />
              <div>
                {/wrong document detected/i.test(errorMessage) && (
                  <p className="font-black text-rose-900 mb-0.5">Wrong Document Detected</p>
                )}
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          {/* ══════ STEP 1: UPLOAD ══════ */}
          {currentStep === 1 && (
            <div className="space-y-5 animate-in fade-in duration-200">
              <div>
                <h4 className="text-sm sm:text-base font-black text-slate-900">Step 1: Choose Resume File</h4>
                <p className="text-xs text-slate-500 font-medium mt-0.5">
                  Attach a PDF, Word document (.docx), or plain text (.txt) file up to 10 MB.
                </p>
              </div>

              {/* Upload Drop Zone */}
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-3xl p-6 sm:p-8 text-center transition-all cursor-pointer relative ${dragActive
                  ? 'border-[#D60041] bg-pink-50/50 scale-[0.99]'
                  : selectedFile
                    ? 'border-emerald-300 bg-emerald-50/30'
                    : 'border-slate-200 hover:border-slate-300 bg-slate-50/50 hover:bg-slate-50'
                  }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileSelected(e.target.files[0]);
                    }
                    e.target.value = '';
                  }}
                  className="hidden"
                />

                {isExtracting ? (
                  <div className="flex flex-col items-center justify-center py-4 space-y-3">
                    <Loader2 size={32} className="animate-spin text-[#D60041]" />
                    <p className="text-xs font-bold text-slate-700">Reading and extracting candidate details...</p>
                    <p className="text-[11px] text-slate-400">Looking up name, email, phone, education, and skills.</p>
                  </div>
                ) : selectedFile ? (
                  <div className="flex flex-col items-center justify-center space-y-2.5">
                    <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center shadow-xs">
                      <CheckCircle2 size={24} />
                    </div>
                    <div className="min-w-0 max-w-full">
                      <p className="text-xs font-black text-slate-900 truncate">{selectedFile.name}</p>
                      <p className="text-[11px] text-slate-500 font-semibold mt-0.5">
                        {(selectedFile.size / 1024).toFixed(1)} KB • Ready for review
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        fileInputRef.current?.click();
                      }}
                      className="text-[11px] font-bold text-[#D60041] hover:underline pt-1"
                    >
                      Choose a different file
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center space-y-3">
                    <div className="w-12 h-12 rounded-2xl bg-white border border-slate-200 text-slate-600 flex items-center justify-center shadow-xs">
                      <Upload size={22} className="text-[#D60041]" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-700">
                        Drag and drop your resume here, or <span className="text-[#D60041] underline">browse files</span>
                      </p>
                      <p className="text-[11px] text-slate-400 font-medium mt-1">
                        Supports PDF, DOCX, and TXT files up to 10 MB
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {errors.file && (
                <p className="text-xs font-bold text-rose-600 flex items-center gap-1.5">
                  <AlertCircle size={14} />
                  <span>{errors.file}</span>
                </p>
              )}
            </div>
          )}

          {/* ══════ STEP 2: REVIEW DETAILS ══════ */}
          {currentStep === 2 && (
            <div className="space-y-4 sm:space-y-5 animate-in fade-in duration-200">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm sm:text-base font-black text-slate-900">Step 2: Review Extracted Details</h4>
                  <p className="text-xs text-slate-500 font-medium mt-0.5">
                    We automatically filled in details from the resume. Edit any fields below if needed.
                  </p>
                </div>
                <HelpTooltip text="Please verify the candidate's personal information. Yellow badges mark items that may need a quick double-check." />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 sm:gap-4">
                {/* Full Name */}
                <div className="space-y-1 sm:col-span-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                      <User size={13} className="text-[#D60041]" />
                      Full Name <span className="text-rose-500">*</span>
                    </label>
                    {!formData.candidate_name && (
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                        Please check
                      </span>
                    )}
                  </div>
                  <input
                    type="text"
                    required
                    value={formData.candidate_name}
                    onChange={(e) => setFormData({ ...formData, candidate_name: e.target.value })}
                    placeholder="e.g. John Paul T. Basagre"
                    className="w-full h-10 px-3 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-[#D60041] focus:ring-1 focus:ring-[#D60041]"
                  />
                  {errors.candidate_name && (
                    <p className="text-[11px] font-bold text-rose-600">{errors.candidate_name}</p>
                  )}
                </div>

                {/* Email */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                      <Mail size={13} className="text-slate-400" />
                      Email Address
                    </label>
                    {!formData.candidate_email && (
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                        Please check
                      </span>
                    )}
                  </div>
                  <input
                    type="email"
                    value={formData.candidate_email}
                    onChange={(e) => setFormData({ ...formData, candidate_email: e.target.value })}
                    placeholder="e.g. johnny.basagre@gmail.com"
                    className="w-full h-10 px-3 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-[#D60041] focus:ring-1 focus:ring-[#D60041]"
                  />
                </div>

                {/* Phone */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                      <Phone size={13} className="text-slate-400" />
                      Contact Number
                    </label>
                    {!formData.candidate_phone && (
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                        Please check
                      </span>
                    )}
                  </div>
                  <input
                    type="text"
                    value={formData.candidate_phone}
                    onChange={(e) => setFormData({ ...formData, candidate_phone: e.target.value })}
                    placeholder="e.g. 0917-123-4567"
                    className="w-full h-10 px-3 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-[#D60041] focus:ring-1 focus:ring-[#D60041]"
                  />
                </div>

                {/* Location / Address */}
                <div className="space-y-1 sm:col-span-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                      <MapPin size={13} className="text-slate-400" />
                      Address / City
                    </label>
                    {!formData.location && (
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                        Please check
                      </span>
                    )}
                  </div>
                  <SelectWithOther
                    value={formData.location}
                    onChange={(val) => setFormData({ ...formData, location: val })}
                    options={PH_LOCATIONS}
                    placeholder="Select city / province..."
                    otherPlaceholder="Enter address or city..."
                    selectClassName="w-full h-10 appearance-none px-3 pr-9 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 bg-white focus:outline-none focus:border-[#D60041] focus:ring-1 focus:ring-[#D60041] cursor-pointer"
                  />
                </div>

                {/* Education */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                      <GraduationCap size={13} className="text-slate-400" />
                      Highest Education / Degree
                    </label>
                    {!formData.education && (
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                        Please check
                      </span>
                    )}
                  </div>
                  <SelectWithOther
                    value={formData.education}
                    onChange={(val) => setFormData({ ...formData, education: val })}
                    options={DEGREE_OPTIONS}
                    placeholder="Select degree / education..."
                    otherPlaceholder="Enter specific degree..."
                    selectClassName="w-full h-10 appearance-none px-3 pr-9 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 bg-white focus:outline-none focus:border-[#D60041] focus:ring-1 focus:ring-[#D60041] cursor-pointer"
                  />
                </div>

                {/* Experience */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                      <Briefcase size={13} className="text-slate-400" />
                      Recent Work Experience
                    </label>
                    {!formData.experience && (
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                        Please check
                      </span>
                    )}
                  </div>
                  <SelectWithOther
                    value={formData.experience}
                    onChange={(val) => setFormData({ ...formData, experience: val })}
                    options={EXPERIENCE_LEVEL_OPTIONS}
                    placeholder="Select experience level..."
                    otherPlaceholder="e.g. Machine Operator (2 years)"
                    selectClassName="w-full h-10 appearance-none px-3 pr-9 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 bg-white focus:outline-none focus:border-[#D60041] focus:ring-1 focus:ring-[#D60041] cursor-pointer"
                  />
                </div>

                {/* Skills */}
                <div className="space-y-1 sm:col-span-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                      <Sparkles size={13} className="text-slate-400" />
                      Key Skills
                    </label>
                    {!formData.skills && (
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                        Please check
                      </span>
                    )}
                  </div>
                  <MultiSelectDropdownWithOther
                    selectedItems={splitCsvItems(formData.skills)}
                    onChange={(items) => setFormData({ ...formData, skills: items.join(', ') })}
                    options={SKILL_OPTIONS}
                    placeholder="Select skills from dropdown..."
                    otherPlaceholder="Enter custom skill and click Add..."
                    emptyStateText="No skills selected yet."
                    selectClassName="w-full h-10 appearance-none px-3 pr-9 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 bg-white focus:outline-none focus:border-[#D60041] focus:ring-1 focus:ring-[#D60041] cursor-pointer"
                  />
                </div>

                {/* Certifications */}
                <div className="space-y-1 sm:col-span-2">
                  <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <Award size={13} className="text-slate-400" />
                    Licenses & Certifications (optional)
                  </label>
                  <MultiSelectDropdownWithOther
                    selectedItems={splitCsvItems(formData.certifications)}
                    onChange={(items) => setFormData({ ...formData, certifications: items.join(', ') })}
                    options={CERTIFICATION_OPTIONS}
                    placeholder="Select licenses or certifications..."
                    otherPlaceholder="Enter custom certification and click Add..."
                    emptyStateText="No certifications selected."
                    selectClassName="w-full h-10 appearance-none px-3 pr-9 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 bg-white focus:outline-none focus:border-[#D60041] focus:ring-1 focus:ring-[#D60041] cursor-pointer"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ══════ STEP 3: APPLICATION INFO ══════ */}
          {currentStep === 3 && (
            <div className="space-y-4 sm:space-y-5 animate-in fade-in duration-200">
              <div>
                <h4 className="text-sm sm:text-base font-black text-slate-900">Step 3: Position & Source Info</h4>
                <p className="text-xs text-slate-500 font-medium mt-0.5">
                  Select which active job this candidate is applying for and where the resume was received.
                </p>
              </div>

              {/* Duplicate Warning */}
              {duplicateWarning && (
                <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-2xl flex items-start gap-2.5 text-xs text-amber-800 font-semibold animate-in shake duration-200">
                  <AlertTriangle size={18} className="text-amber-600 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-bold">Possible duplicate application detected</p>
                    <p className="text-[11px] font-normal mt-0.5 text-amber-700">{duplicateWarning}</p>
                    <p className="text-[11px] font-bold text-amber-800 mt-1">
                      You can continue to import a newer version or choose a different position.
                    </p>
                  </div>
                </div>
              )}

              {/* Position Applied For */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <Briefcase size={14} className="text-[#D60041]" />
                    Position Applied For <span className="text-rose-500">*</span>
                  </label>
                  <HelpTooltip text="Assigns this candidate to an active job opening so the system can compute match scores and add them to screening." />
                </div>
                <select
                  required
                  value={formData.target_job_id}
                  onChange={(e) => handleJobSelect(e.target.value)}
                  className="w-full h-11 px-3 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-[#D60041] bg-white cursor-pointer"
                >
                  <option value="">-- Choose an active position --</option>
                  {activeJobs.map((job: any) => (
                    <option key={job.id} value={job.id}>
                      {job.job_title || job.title} ({job.department || 'General'})
                    </option>
                  ))}
                </select>
                {errors.target_job_id && (
                  <p className="text-[11px] font-bold text-rose-600">{errors.target_job_id}</p>
                )}
              </div>

              {/* Source Origin */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    Where did this resume come from? <span className="text-rose-500">*</span>
                  </label>
                  <HelpTooltip text="Tracks the hiring channel for analytics and source tags." />
                </div>
                <select
                  value={formData.import_origin}
                  onChange={(e) => setFormData({ ...formData, import_origin: e.target.value })}
                  className="w-full h-11 px-3 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 focus:outline-none focus:border-[#D60041] bg-white cursor-pointer"
                >
                  <option value="Walk-in">Walk-in (Plant Front Desk / Office)</option>
                  <option value="Email">Email submission</option>
                  <option value="Job site">Job site (JobStreet / Indeed / LinkedIn)</option>
                  <option value="Other">Other referral / agency</option>
                </select>
              </div>

              {/* Physical Storage Reference (optional) */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                  Filing & Archive Reference (optional)
                </label>
                <SelectWithOther
                  value={formData.physical_location}
                  onChange={(val) => setFormData({ ...formData, physical_location: val })}
                  options={PHYSICAL_ARCHIVE_LOCATIONS}
                  placeholder="Select archive location..."
                  otherPlaceholder="e.g. Cabinet A • Shelf 1 • Folder #14"
                  selectClassName="w-full h-11 appearance-none px-3 pr-9 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 bg-white focus:outline-none focus:border-[#D60041] cursor-pointer"
                />
              </div>

              {/* Notes */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Internal HR Notes (optional)</label>
                <textarea
                  rows={2}
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="e.g. Recommended by Production supervisor; available immediately."
                  className="w-full p-2.5 rounded-xl border border-slate-200 text-xs font-medium text-slate-800 focus:outline-none focus:border-[#D60041]"
                />
              </div>
            </div>
          )}

          {/* ══════ STEP 4: CONFIRM ══════ */}
          {currentStep === 4 && (
            <div className="space-y-4 sm:space-y-5 animate-in fade-in duration-200">
              <div>
                <h4 className="text-sm sm:text-base font-black text-slate-900">Step 4: Confirm & Import</h4>
                <p className="text-xs text-slate-500 font-medium mt-0.5">
                  Please review the application summary before adding to the candidate pool.
                </p>
              </div>

              {/* Summary Card */}
              <div className="bg-slate-50/80 rounded-2xl p-4 sm:p-5 border border-slate-200/80 space-y-3.5">
                <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-pink-100 text-[#D60041] flex items-center justify-center font-black text-base">
                      {formData.candidate_name.charAt(0) || 'C'}
                    </div>
                    <div>
                      <h5 className="text-sm font-black text-slate-900">{formData.candidate_name}</h5>
                      <p className="text-[11px] text-slate-500 font-medium">{formData.candidate_email || 'No email provided'}</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-pink-50 text-[#D60041] border border-pink-200">
                    Imported • {formData.import_origin}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Target Job</span>
                    <p className="font-bold text-slate-800 mt-0.5">{formData.target_job_title || 'Position'}</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Contact Phone</span>
                    <p className="font-bold text-slate-800 mt-0.5">{formData.candidate_phone || 'None'}</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Education</span>
                    <p className="font-semibold text-slate-700 mt-0.5 truncate">{formData.education || 'Not listed'}</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Experience</span>
                    <p className="font-semibold text-slate-700 mt-0.5 truncate">{formData.experience || 'Not listed'}</p>
                  </div>
                </div>

                {formData.skills && (
                  <div className="pt-2 border-t border-slate-200/60">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Key Skills</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {formData.skills.split(',').slice(0, 8).map((sk, idx) => (
                        <span key={idx} className="px-2 py-0.5 rounded-lg bg-white border border-slate-200 text-[11px] font-medium text-slate-700">
                          {sk.trim()}
                        </span>
                      ))}
                      {formData.skills.split(',').length > 8 && (
                        <span className="text-[10px] text-slate-400 self-center">
                          +{formData.skills.split(',').length - 8} more
                        </span>
                      )}
                    </div>
                  </div>
                )}

                <div className="pt-2 border-t border-slate-200/60 text-[11px] text-slate-500 flex items-center justify-between">
                  <span className="flex items-center gap-1.5 truncate">
                    <FileText size={13} className="text-slate-400 shrink-0" />
                    <span className="truncate">{selectedFile?.name}</span>
                  </span>
                  <span className="shrink-0 font-medium">Status: Submitted</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* MODAL FOOTER: NAVIGATION BUTTONS */}
        <div className="px-5 sm:px-6 py-3.5 sm:py-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between shrink-0">
          {currentStep > 1 ? (
            <button
              type="button"
              onClick={() => setCurrentStep((prev) => prev - 1)}
              disabled={isUploading}
              className="px-4 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 text-slate-700 text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 rounded-xl text-slate-500 hover:text-slate-800 text-xs font-bold transition-all cursor-pointer"
            >
              Cancel
            </button>
          )}

          {currentStep === 1 && (
            <button
              type="button"
              onClick={handleProceedToStep2}
              disabled={!selectedFile || isExtracting}
              className="px-5 py-2.5 rounded-xl bg-[#D60041] hover:bg-[#B50037] text-white text-xs font-bold transition-all shadow-xs hover:shadow-md flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>Next: Review Details</span>
              <ArrowRight size={14} />
            </button>
          )}

          {currentStep === 2 && (
            <button
              type="button"
              onClick={handleProceedToStep3}
              className="px-5 py-2.5 rounded-xl bg-[#D60041] hover:bg-[#B50037] text-white text-xs font-bold transition-all shadow-xs hover:shadow-md flex items-center gap-2 cursor-pointer"
            >
              <span>Next: Application Info</span>
              <ArrowRight size={14} />
            </button>
          )}

          {currentStep === 3 && (
            <button
              type="button"
              onClick={handleProceedToStep4}
              className="px-5 py-2.5 rounded-xl bg-[#D60041] hover:bg-[#B50037] text-white text-xs font-bold transition-all shadow-xs hover:shadow-md flex items-center gap-2 cursor-pointer"
            >
              <span>Next: Confirm</span>
              <ArrowRight size={14} />
            </button>
          )}

          {currentStep === 4 && (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isUploading}
              className="px-6 py-2.5 rounded-xl bg-[#D60041] hover:bg-[#B50037] text-white text-xs font-black uppercase tracking-wider transition-all shadow-xs hover:shadow-md flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {isUploading ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  <span>Importing...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 size={16} />
                  <span>Import Resume</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default UploadPhysicalResumeModal;
