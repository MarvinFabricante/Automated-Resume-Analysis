import React, { useState, useEffect, useMemo } from 'react';
import {
  ChevronDown,
  ChevronUp,
  FileText,
  Download,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  ListChecks,
} from 'lucide-react';
import api, { API_BASE_URL } from '../../services/api';
import HelpTooltip from './HelpTooltip';

export interface ReadabilityWarning {
  code:
    | 'password_protected'
    | 'low_text'
    | 'multi_column'
    | 'missing_headings'
    | 'missing_contact'
    | 'missing_dates'
    | string;
  title: string;
  message: string;
  suggestion: string;
}

export interface ReadabilityCheckResult {
  status: 'ok' | 'warning';
  summary: string;
  warnings: ReadabilityWarning[];
}

export interface ResumeTipsConfig {
  title: string;
  tooltip: string;
  intro: string;
  bullets: string[];
  honesty_reminder: string;
  apply_skills_reminder: string;
}

export const DEFAULT_RESUME_TIPS: ResumeTipsConfig = {
  title: 'Tips for a better match',
  tooltip:
    'Clear formatting helps our system read your resume accurately so your match reflects your actual experience.',
  intro: 'A clean, easy-to-read resume helps the system read your details accurately.',
  bullets: [
    'Use a simple one-column layout with clear headings: Education, Skills, Work Experience, Certifications.',
    'Upload a text-based PDF or DOCX, not a photo or scanned image.',
    'Use standard fonts and avoid text inside images, tables, text boxes, headers and footers.',
    'Write dates and job titles clearly, for example "Customer Service Representative, June 2023 - Present".',
    'List your skills and tools by name (for example Excel, Shopify, data entry) and use the same words as in the job posting when they truly apply to you.',
    'Include your certifications and trainings, and keep the resume up to date.',
  ],
  honesty_reminder: 'Only include what is true.',
  apply_skills_reminder:
    'Review the required skills for this position and make sure your resume mentions the skills and matching experience you actually have.',
};

const FILIPINO_RESUME_TIPS: ResumeTipsConfig = {
  title: 'Mga gabay para sa mas maayos na pagbasa ng resume',
  tooltip:
    'Nakakatulong ang malinaw na format upang mabasa nang tama ang iyong resume at karanasan.',
  intro:
    'Ang malinaw at madaling basahing resume ay tumutulong upang maitugma nang tama ang iyong karanasan sa trabaho.',
  bullets: [
    'Gumamit ng simpleng isang-kolum (one-column) na layout na may malinaw na pamagat: Education, Skills, Work Experience, Certifications.',
    'Mag-upload ng text-based na PDF o DOCX, hindi larawan o scanned image.',
    'Gumamit ng karaniwang font at iwasan ang teksto sa loob ng larawan, table, text box, header, at footer.',
    'Isulat nang malinaw ang mga petsa at posisyon, halimbawa "Customer Service Representative, June 2023 - Present".',
    'Ilista ang iyong mga kasanayan at gamit na tools (halimbawa Excel, Shopify, data entry) at gamitin ang kaparehong salita sa job posting kung totoo itong naaangkop sa iyo.',
    'Isama ang iyong mga sertipikasyon at training, at panatilihing updated ang resume.',
  ],
  honesty_reminder: 'Isama lamang ang totoo.',
  apply_skills_reminder:
    'Basahin ang mga kailangang kasanayan para sa posisyong ito at tiyaking nakasaad sa iyong resume ang mga kasanayan at karanasang totoong taglay mo.',
};

let cachedTipsPromise: Promise<ResumeTipsConfig> | null = null;

export function clearResumeTipsCache() {
  cachedTipsPromise = null;
}

export async function fetchResumeTipsConfig(): Promise<ResumeTipsConfig> {
  if (!cachedTipsPromise) {
    cachedTipsPromise = api
      .get<ResumeTipsConfig>('/system-config/resume-tips')
      .then((res) => {
        const d = res.data;
        if (d && Array.isArray(d.bullets) && d.bullets.length > 0) {
          return {
            ...DEFAULT_RESUME_TIPS,
            ...d,
          };
        }
        return DEFAULT_RESUME_TIPS;
      })
      .catch(() => DEFAULT_RESUME_TIPS);
  }
  return cachedTipsPromise;
}

function getUserStorageKey(): string {
  if (typeof localStorage === 'undefined') return 'guest';
  const uid = localStorage.getItem('user_id') || localStorage.getItem('userId');
  const email = localStorage.getItem('saved_email');
  return uid || email || 'guest';
}

interface ResumeTipsPanelProps {
  /**
   * When true (on an upload screen starting a new upload), the panel starts open
   * even if the user collapsed it previously, while still remembering when they close it.
   */
  isNewUploadStep?: boolean;
  /** Increment or change when a new file is selected to show tips again on a new upload. */
  uploadResetKey?: string | number;
  className?: string;
}

export const ResumeTipsPanel: React.FC<ResumeTipsPanelProps> = ({
  isNewUploadStep = false,
  uploadResetKey,
  className = '',
}) => {
  const storageKey = useMemo(() => `resume_tips_collapsed_${getUserStorageKey()}`, []);

  const [isOpen, setIsOpen] = useState<boolean>(() => {
    if (isNewUploadStep) return true;
    if (typeof localStorage === 'undefined') return true;
    return localStorage.getItem(storageKey) !== 'true';
  });

  const [tips, setTips] = useState<ResumeTipsConfig>(DEFAULT_RESUME_TIPS);
  const [lang, setLang] = useState<'en' | 'fil'>('en');

  useEffect(() => {
    let active = true;
    fetchResumeTipsConfig().then((cfg) => {
      if (active) setTips(cfg);
    });
    return () => {
      active = false;
    };
  }, []);

  // Always show on a new upload reset if provided
  useEffect(() => {
    if (uploadResetKey !== undefined && uploadResetKey !== '') {
      setIsOpen(true);
    }
  }, [uploadResetKey]);

  const handleToggle = () => {
    setIsOpen((prev) => {
      const next = !prev;
      if (typeof localStorage !== 'undefined') {
        try {
          localStorage.setItem(storageKey, next ? 'false' : 'true');
        } catch {
          // ignore storage quota errors
        }
      }
      return next;
    });
  };

  const activeCopy = lang === 'fil' ? FILIPINO_RESUME_TIPS : tips;
  const templateDownloadUrl = `${API_BASE_URL.replace(/\/$/, '')}/resumes/ats-template`;

  return (
    <div
      className={`bg-white border border-slate-200/90 rounded-2xl shadow-2xs overflow-hidden ${className}`}
    >
      <div className="px-4 py-3 sm:px-5 sm:py-3.5 bg-slate-50/80 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200/80 text-amber-600 flex items-center justify-center shrink-0">
            <Lightbulb size={15} />
          </div>
          <button
            type="button"
            onClick={handleToggle}
            className="text-left text-xs sm:text-sm font-bold text-slate-900 hover:text-[#D10043] transition-colors truncate cursor-pointer"
          >
            {activeCopy.title}
          </button>
          <HelpTooltip content={activeCopy.tooltip} />
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isOpen && (
            <div className="inline-flex items-center rounded-lg border border-slate-200 bg-white p-0.5 text-[10px] font-bold">
              <button
                type="button"
                onClick={() => setLang('en')}
                className={`px-1.5 py-0.5 rounded-md cursor-pointer transition-colors ${
                  lang === 'en' ? 'bg-slate-900 text-white' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLang('fil')}
                className={`px-1.5 py-0.5 rounded-md cursor-pointer transition-colors ${
                  lang === 'fil' ? 'bg-slate-900 text-white' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                FIL
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={handleToggle}
            aria-expanded={isOpen}
            className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-500 hover:text-slate-900 px-2 py-1 rounded-lg hover:bg-slate-200/60 transition-colors cursor-pointer"
          >
            <span>{isOpen ? 'Hide' : 'Show'}</span>
            {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="px-4 py-3.5 sm:px-5 sm:py-4 space-y-3 border-t border-slate-100">
          {activeCopy.intro && (
            <p className="text-xs text-slate-600 leading-relaxed">{activeCopy.intro}</p>
          )}

          <ul className="space-y-1.5 text-xs text-slate-700 leading-relaxed list-disc pl-5">
            {activeCopy.bullets.map((bullet, idx) => (
              <li key={idx}>{bullet}</li>
            ))}
          </ul>

          <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
            <p className="text-xs font-bold text-slate-800">{activeCopy.honesty_reminder}</p>

            <a
              href={templateDownloadUrl}
              download="ATS_Friendly_Resume_Guide_Template.docx"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-[#D10043] hover:text-slate-900 bg-rose-50 hover:bg-rose-100 border border-rose-200/80 px-3 py-1.5 rounded-xl transition-colors self-start sm:self-auto"
            >
              <FileText size={13} />
              <span>Download ATS-friendly resume template (.docx)</span>
              <Download size={12} />
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

interface ResumeReadabilityBannerProps {
  readabilityCheck?: ReadabilityCheckResult | null;
  className?: string;
}

export const ResumeReadabilityBanner: React.FC<ResumeReadabilityBannerProps> = ({
  readabilityCheck,
  className = '',
}) => {
  if (!readabilityCheck) return null;

  const warnings = Array.isArray(readabilityCheck.warnings) ? readabilityCheck.warnings : [];

  if (readabilityCheck.status === 'ok' && warnings.length === 0) {
    return (
      <div
        role="status"
        className={`flex items-center gap-2.5 px-4 py-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 ${className}`}
      >
        <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />
        <div className="text-xs sm:text-sm">
          <span className="font-bold">Looks readable</span>
          <span className="text-emerald-800 ml-1.5">
            — Your resume text, headings, contact info, and dates were read clearly. You can still review and edit any details on the next step.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      role="status"
      className={`p-4 sm:p-5 rounded-2xl bg-amber-50/90 border border-amber-200 text-amber-950 space-y-3 ${className}`}
    >
      <div className="flex items-start gap-2.5">
        <AlertTriangle size={18} className="text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <h4 className="text-xs sm:text-sm font-bold text-amber-950">
            Resume readability check (optional to fix)
          </h4>
          <p className="text-xs text-amber-900 leading-relaxed">
            {readabilityCheck.summary ||
              'We noticed a few things that may make parts of your resume harder to read. You can still continue and review or correct your details on the next step.'}
          </p>
        </div>
      </div>

      <ul className="space-y-2 pl-1">
        {warnings.map((w, idx) => (
          <li
            key={w.code || idx}
            className="bg-white/80 border border-amber-200/70 rounded-xl p-3 text-xs space-y-1"
          >
            <p className="font-bold text-slate-900">{w.title}</p>
            <p className="text-slate-700">{w.message}</p>
            <p className="text-amber-900 font-medium">What to do: {w.suggestion}</p>
          </li>
        ))}
      </ul>

      <p className="text-[11px] text-amber-800 font-medium">
        This check is only here to help you—it never blocks your application and is not shared as a penalty.
      </p>
    </div>
  );
};

interface ApplySkillsReminderProps {
  requiredSkills?: string | string[] | null;
  jobTitle?: string;
  className?: string;
}

export const ApplySkillsReminder: React.FC<ApplySkillsReminderProps> = ({
  requiredSkills,
  jobTitle,
  className = '',
}) => {
  const [reminderText, setReminderText] = useState<string>(
    DEFAULT_RESUME_TIPS.apply_skills_reminder
  );

  useEffect(() => {
    let active = true;
    fetchResumeTipsConfig().then((cfg) => {
      if (active && cfg.apply_skills_reminder) {
        setReminderText(cfg.apply_skills_reminder);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const skillItems = useMemo(() => {
    if (!requiredSkills) return [];
    const list = Array.isArray(requiredSkills)
      ? requiredSkills
      : String(requiredSkills)
          .split(/[,;\n•|]+/)
          .map((s) => s.trim());
    return list.filter(Boolean).slice(0, 10);
  }, [requiredSkills]);

  return (
    <div
      className={`p-4 rounded-2xl bg-sky-50/70 border border-sky-200/80 text-slate-800 space-y-2 ${className}`}
    >
      <div className="flex items-start gap-2.5">
        <ListChecks size={17} className="text-sky-700 shrink-0 mt-0.5" />
        <div className="space-y-1 min-w-0">
          <p className="text-xs font-bold text-slate-900">
            Before you upload{jobTitle ? ` for ${jobTitle}` : ''}
          </p>
          <p className="text-xs text-slate-700 leading-relaxed">{reminderText}</p>
        </div>
      </div>

      {skillItems.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pl-6">
          {skillItems.map((skill, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 rounded-lg bg-white border border-sky-200 text-[11px] font-semibold text-sky-900"
            >
              {skill}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default ResumeTipsPanel;
