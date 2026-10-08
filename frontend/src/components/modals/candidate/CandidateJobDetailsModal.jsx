import React, { useEffect, useState } from 'react';
import {
  X,
  Briefcase,
  MapPin,
  Building2,
  Clock,
  Sparkles,
  ArrowRight,
  GraduationCap,
  Award,
  Calendar,
  Share2,
  Bookmark,
  Check,
  ShieldCheck,
  CheckCircle2,
  Coins,
  ChevronRight,
  Heart
} from 'lucide-react';

const DetailCard = ({ icon: Icon, label, value, colorClass = "text-rose-500", bgClass = "bg-rose-50" }) => (
  <div className="flex items-center gap-3.5 p-3.5 sm:p-4 rounded-2xl bg-slate-50/80 border border-slate-100 hover:bg-white hover:shadow-md hover:border-slate-200 transition-all duration-200">
    <div className={`w-11 h-11 sm:w-12 sm:h-12 rounded-xl ${bgClass} ${colorClass} flex items-center justify-center shrink-0`}>
      <Icon size={20} className="sm:w-[22px] sm:h-[22px]" />
    </div>
    <div className="min-w-0 flex-1">
      <span className="block text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 truncate">
        {label}
      </span>
      <span className="block text-sm sm:text-base font-black text-slate-900 truncate mt-0.5">
        {value || 'Not specified'}
      </span>
    </div>
  </div>
);

const CandidateJobDetailsModal = ({
  isOpen,
  onClose,
  job,
  onApply,
  isBookmarked = false,
  onToggleBookmark
}) => {
  const [copied, setCopied] = useState(false);

  // Close on Escape key and prevent background scroll
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !job) return null;

  const handleShare = async () => {
    try {
      const shareUrl = window.location.href;
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(shareUrl);
        setCopied(true);
        setTimeout(() => setCopied(false), 2200);
      }
    } catch {
      // Fallback
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    }
  };

  // Parse skills string into array
  const skillsArray = typeof job.skills_requirements === 'string'
    ? job.skills_requirements
        .split(/[,;\n•]+/)
        .map(s => s.trim())
        .filter(Boolean)
    : Array.isArray(job.skills_requirements)
    ? job.skills_requirements
    : [];

  // Parse description paragraphs
  const descriptionParagraphs = job.description
    ? job.description.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean)
    : [];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="job-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 md:p-8 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white w-full max-w-4xl max-h-[92vh] sm:max-h-[88vh] rounded-[28px] sm:rounded-[36px] shadow-2xl border border-slate-100 flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        
        {/* MODAL HEADER */}
        <div className="relative px-6 sm:px-10 py-6 sm:py-8 border-b border-slate-100 bg-white/95 backdrop-blur-md shrink-0">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              {/* Badges & Meta */}
              <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2.5">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.2em] bg-[#D10043]/10 text-[#D10043]">
                  <Sparkles size={12} />
                  {job.department || 'General'}
                </span>

                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                  job.is_active
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/60'
                    : 'bg-slate-100 text-slate-500 border border-slate-200'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${job.is_active ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
                  {job.is_active ? 'Actively Hiring' : 'Closed'}
                </span>

                {job.job_type && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-500 bg-slate-100/80 px-2.5 py-1 rounded-full">
                    <Clock size={12} className="text-slate-400" />
                    {job.job_type}
                  </span>
                )}
              </div>

              {/* Title */}
              <h2
                id="job-modal-title"
                className="text-2xl sm:text-3xl md:text-4xl font-black text-slate-900 tracking-tight leading-tight"
              >
                {job.title || job.job_title}
              </h2>
              
              <div className="flex items-center gap-2 mt-2 text-xs sm:text-sm text-slate-500 font-medium">
                <span className="font-bold text-slate-700">Mariwasa Siam Ceramics</span>
                <span>•</span>
                <span className="flex items-center gap-1 text-slate-500">
                  <MapPin size={13} className="text-[#D10043]" />
                  {job.location || 'Remote'}
                </span>
                {job.id && (
                  <>
                    <span className="hidden sm:inline">•</span>
                    <span className="hidden sm:inline font-mono text-[11px] text-slate-400 bg-slate-50 px-2 py-0.5 rounded-md border border-slate-100">
                      ID: {job.id}
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Quick Action Buttons (Share, Bookmark, Close) */}
            <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
              <button
                type="button"
                onClick={handleShare}
                title={copied ? "Link Copied!" : "Share job"}
                className={`p-2.5 sm:p-3 rounded-2xl border transition-all duration-200 ${
                  copied
                    ? 'bg-emerald-50 text-emerald-600 border-emerald-200 shadow-sm'
                    : 'text-slate-400 hover:text-slate-700 hover:bg-slate-50 border-slate-200/80'
                }`}
              >
                {copied ? <Check size={18} className="text-emerald-600" /> : <Share2 size={18} />}
              </button>

              {onToggleBookmark && (
                <button
                  type="button"
                  onClick={() => onToggleBookmark(job.id)}
                  title={isBookmarked ? "Remove Bookmark" : "Save Job"}
                  className={`p-2.5 sm:p-3 rounded-2xl border transition-all duration-200 ${
                    isBookmarked
                      ? 'bg-pink-50 text-[#D10043] border-pink-200 shadow-sm'
                      : 'text-slate-400 hover:text-[#D10043] hover:bg-pink-50/50 border-slate-200/80'
                  }`}
                >
                  <Bookmark size={18} className={isBookmarked ? "fill-[#D10043]" : ""} />
                </button>
              )}

              <button
                type="button"
                onClick={onClose}
                title="Close"
                className="p-2.5 sm:p-3 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-2xl border border-slate-200/80 transition-all duration-200 active:scale-95"
              >
                <X size={20} />
              </button>
            </div>
          </div>
        </div>

        {/* MODAL BODY (Scrollable) */}
        <div className="flex-1 overflow-y-auto px-6 sm:px-10 py-6 sm:py-8 space-y-8">
          
          {/* Key Attribute Cards Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <DetailCard
              icon={Building2}
              label="Department"
              value={job.department}
              colorClass="text-blue-600"
              bgClass="bg-blue-50"
            />
            <DetailCard
              icon={Clock}
              label="Employment"
              value={job.job_type}
              colorClass="text-purple-600"
              bgClass="bg-purple-50"
            />
            <DetailCard
              icon={MapPin}
              label="Workplace"
              value={job.location}
              colorClass="text-emerald-600"
              bgClass="bg-emerald-50"
            />
            <DetailCard
              icon={Coins}
              label="Compensation"
              value={job.salary_range}
              colorClass="text-[#D10043]"
              bgClass="bg-pink-50"
            />
          </div>

          {/* Job Overview / Description */}
          <section className="space-y-3.5">
            <div className="flex items-center gap-2 text-slate-900">
              <div className="w-8 h-8 rounded-xl bg-[#D10043]/10 text-[#D10043] flex items-center justify-center">
                <Briefcase size={16} />
              </div>
              <h3 className="text-lg sm:text-xl font-black tracking-tight">Role Overview & Responsibilities</h3>
            </div>
            
            <div className="bg-slate-50/70 border border-slate-100 rounded-3xl p-5 sm:p-7 space-y-3">
              {descriptionParagraphs.length > 0 ? (
                descriptionParagraphs.map((paragraph, index) => (
                  <p key={index} className="text-slate-600 text-sm sm:text-base leading-relaxed font-normal">
                    {paragraph}
                  </p>
                ))
              ) : job.description ? (
                <p className="text-slate-600 text-sm sm:text-base leading-relaxed whitespace-pre-line">
                  {job.description}
                </p>
              ) : (
                <p className="text-slate-400 italic text-sm">
                  Mariwasa is actively recruiting for this position. Detailed responsibilities will be discussed during the initial screening.
                </p>
              )}
            </div>
          </section>

          {/* Required Skills & Competencies */}
          <section className="space-y-3.5">
            <div className="flex items-center gap-2 text-slate-900">
              <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
                <Sparkles size={16} />
              </div>
              <h3 className="text-lg sm:text-xl font-black tracking-tight">Key Skills & Requirements</h3>
            </div>

            <div className="bg-white border border-slate-100 rounded-3xl p-5 sm:p-7 shadow-xs">
              {skillsArray.length > 0 ? (
                <div className="flex flex-wrap gap-2 sm:gap-2.5">
                  {skillsArray.map((skill, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold bg-slate-50 hover:bg-pink-50 hover:text-[#D10043] border border-slate-200/80 text-slate-700 transition-colors"
                    >
                      <CheckCircle2 size={13} className="text-[#D10043]" />
                      {skill}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 text-sm">
                  {job.skills_requirements || 'Standard qualifications for this discipline apply.'}
                </p>
              )}
            </div>
          </section>

          {/* Experience, Education & Certifications */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Experience Card */}
            <div className="p-5 sm:p-6 rounded-3xl bg-amber-50/50 border border-amber-100/70 space-y-2">
              <div className="flex items-center gap-2 text-amber-800">
                <Calendar size={18} className="text-amber-600" />
                <h4 className="text-xs font-black uppercase tracking-wider">Experience Level</h4>
              </div>
              <p className="text-sm sm:text-base font-bold text-slate-900">
                {job.experience_requirements || 'Open to all experience levels (Entry to Experienced)'}
              </p>
            </div>

            {/* Education Card */}
            <div className="p-5 sm:p-6 rounded-3xl bg-blue-50/50 border border-blue-100/70 space-y-2">
              <div className="flex items-center gap-2 text-blue-800">
                <GraduationCap size={18} className="text-blue-600" />
                <h4 className="text-xs font-black uppercase tracking-wider">Education & Credentials</h4>
              </div>
              <p className="text-sm sm:text-base font-bold text-slate-900">
                {job.education_requirements || 'Degree or vocational qualification in related discipline'}
              </p>
              {job.certifications_requirements && (
                <div className="pt-2 border-t border-blue-100 flex items-start gap-2 text-xs text-blue-700 font-semibold">
                  <Award size={14} className="shrink-0 mt-0.5" />
                  <span>{job.certifications_requirements}</span>
                </div>
              )}
            </div>
          </div>

          {/* About Mariwasa Callout */}
          <section className="p-6 sm:p-7 rounded-3xl bg-gradient-to-br from-slate-900 to-slate-800 text-white relative overflow-hidden">
            <div className="absolute -right-8 -bottom-8 w-40 h-40 bg-[#D10043]/20 rounded-full blur-2xl pointer-events-none" />
            
            <div className="relative z-10 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black uppercase tracking-[0.25em] text-[#D10043]">
                  Why Join Mariwasa
                </span>
              </div>
              <h4 className="text-lg sm:text-xl font-black tracking-tight">
                Build a Thriving Career with the Industry Leader
              </h4>
              <p className="text-slate-300 text-xs sm:text-sm font-normal leading-relaxed max-w-2xl">
                Founded in 1963, Mariwasa is the premier ceramic tile manufacturer in the Philippines. Join our talented workforce with robust health benefits, competitive performance incentives, and comprehensive skill development paths.
              </p>
            </div>
          </section>

        </div>

        {/* MODAL FOOTER (Sticky) */}
        <div className="px-6 sm:px-10 py-4 sm:py-5 border-t border-slate-100 bg-slate-50/60 flex flex-col-reverse sm:flex-row items-center justify-between gap-3 sm:gap-4 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto px-6 py-3.5 rounded-2xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs sm:text-sm font-bold uppercase tracking-wider transition-all"
          >
            Close
          </button>

          <div className="w-full sm:w-auto flex items-center gap-3">
            <button
              type="button"
              onClick={() => onApply(job.id)}
              disabled={!job.is_active}
              className={`w-full sm:w-auto px-8 py-3.5 rounded-2xl font-black text-xs sm:text-sm uppercase tracking-wider flex items-center justify-center gap-2.5 transition-all shadow-xl ${
                job.is_active
                  ? 'bg-[#D10043] text-white shadow-[#D10043]/20 hover:bg-slate-900 active:scale-[0.98]'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
              }`}
            >
              {job.is_active ? (
                <>
                  Apply for this Position
                  <ArrowRight size={16} />
                </>
              ) : (
                'Applications Closed'
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

export default CandidateJobDetailsModal;
