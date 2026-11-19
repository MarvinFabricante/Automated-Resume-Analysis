import React, { useState } from 'react';
import { Sliders, RefreshCw, ChevronDown, ChevronUp, AlertTriangle, HelpCircle } from 'lucide-react';
import { JobScoringWeights, DEFAULT_JOB_SCORING_WEIGHTS } from '../../../types';

export const MIN_WEIGHT_PCT = 5;
export const MAX_WEIGHT_PCT = 70;
export const WEIGHT_STEP_PCT = 5;

interface WeightFieldMeta {
  key: keyof JobScoringWeights;
  label: string;
  shortLabel: string;
  defaultPct: number;
  tooltip: string;
  color: string;
}

export const WEIGHT_FIELDS: WeightFieldMeta[] = [
  {
    key: 'skills_weight',
    label: 'Skills Match',
    shortLabel: 'Skills',
    defaultPct: 40,
    tooltip: 'How closely the candidate’s technical and transferable skills match the job requirements.',
    color: 'bg-rose-500',
  },
  {
    key: 'experience_weight',
    label: 'Work Experience Relevance',
    shortLabel: 'Experience',
    defaultPct: 30,
    tooltip: 'How relevant their past roles, responsibilities, and years of experience are to this job.',
    color: 'bg-blue-500',
  },
  {
    key: 'education_weight',
    label: 'Educational Background',
    shortLabel: 'Education',
    defaultPct: 15,
    tooltip: 'Whether their degree level and field of study meet what this role asks for.',
    color: 'bg-emerald-500',
  },
  {
    key: 'certifications_weight',
    label: 'Certifications & Trainings',
    shortLabel: 'Certifications',
    defaultPct: 10,
    tooltip: 'Required or preferred licenses, industry certifications, and specialized trainings.',
    color: 'bg-purple-500',
  },
  {
    key: 'completeness_weight',
    label: 'Resume Completeness',
    shortLabel: 'Completeness',
    defaultPct: 5,
    tooltip: 'How complete the candidate’s profile and submitted application sections are.',
    color: 'bg-amber-500',
  },
];

export const WEIGHT_PRESETS: Array<{ label: string; weights: JobScoringWeights }> = [
  {
    label: 'Balanced (default)',
    weights: { ...DEFAULT_JOB_SCORING_WEIGHTS },
  },
  {
    label: 'Skills first',
    weights: {
      skills_weight: 0.55,
      experience_weight: 0.20,
      education_weight: 0.10,
      certifications_weight: 0.10,
      completeness_weight: 0.05,
    },
  },
  {
    label: 'Experience first',
    weights: {
      skills_weight: 0.25,
      experience_weight: 0.50,
      education_weight: 0.10,
      certifications_weight: 0.10,
      completeness_weight: 0.05,
    },
  },
  {
    label: 'Certifications first',
    weights: {
      skills_weight: 0.25,
      experience_weight: 0.20,
      education_weight: 0.10,
      certifications_weight: 0.40,
      completeness_weight: 0.05,
    },
  },
  {
    label: 'Education first',
    weights: {
      skills_weight: 0.25,
      experience_weight: 0.20,
      education_weight: 0.40,
      certifications_weight: 0.10,
      completeness_weight: 0.05,
    },
  },
];

export function getWeightsTotalPct(weights: JobScoringWeights): number {
  return WEIGHT_FIELDS.reduce((sum, f) => sum + Math.round((weights[f.key] ?? 0) * 100), 0);
}

export function isWeightsBalanced(weights: JobScoringWeights): boolean {
  const allInRange = WEIGHT_FIELDS.every(({ key }) => {
    const pct = Math.round((weights[key] ?? 0) * 100);
    return pct >= MIN_WEIGHT_PCT && pct <= MAX_WEIGHT_PCT;
  });
  return allInRange && getWeightsTotalPct(weights) === 100;
}

export function areWeightsEqual(a: JobScoringWeights, b: JobScoringWeights): boolean {
  return WEIGHT_FIELDS.every(
    ({ key }) => Math.round((a[key] ?? 0) * 100) === Math.round((b[key] ?? 0) * 100)
  );
}

export function formatPrioritySummary(weights?: JobScoringWeights | null): string {
  if (!weights || areWeightsEqual(weights, DEFAULT_JOB_SCORING_WEIGHTS)) {
    return 'Default priorities';
  }
  const topTwo = [...WEIGHT_FIELDS]
    .sort((a, b) => (weights[b.key] ?? 0) - (weights[a.key] ?? 0))
    .slice(0, 2)
    .map((f) => `${f.shortLabel} ${Math.round((weights[f.key] ?? 0) * 100)}%`);
  return `Priority: ${topTwo.join(', ')}`;
}

interface HelpTooltipProps {
  text: string;
  label: string;
}

const HelpTooltip: React.FC<HelpTooltipProps> = ({ text, label }) => {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        aria-label={label}
        className="w-4 h-4 rounded-full bg-gray-200 hover:bg-gray-300 text-gray-600 inline-flex items-center justify-center text-[10px] font-bold focus:outline-none focus:ring-2 focus:ring-[#d81159] cursor-pointer"
      >
        <HelpCircle size={12} aria-hidden="true" />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-60 p-2.5 rounded-xl bg-gray-900 text-white text-[11px] font-medium leading-snug shadow-lg z-30 pointer-events-none"
        >
          {text}
        </span>
      )}
    </span>
  );
};

interface JobScoringWeightsEditorProps {
  weights: JobScoringWeights;
  defaultWeights?: JobScoringWeights;
  onChange: (next: JobScoringWeights) => void;
  defaultExpanded?: boolean;
  readOnly?: boolean;
  error?: string | null;
}

const JobScoringWeightsEditor: React.FC<JobScoringWeightsEditorProps> = ({
  weights,
  defaultWeights = DEFAULT_JOB_SCORING_WEIGHTS,
  onChange,
  defaultExpanded = false,
  readOnly = false,
  error = null,
}) => {
  const [expanded, setExpanded] = useState<boolean>(defaultExpanded);

  const totalPct = getWeightsTotalPct(weights);
  const balanced = totalPct === 100;
  const allInRange = WEIGHT_FIELDS.every(({ key }) => {
    const pct = Math.round((weights[key] ?? 0) * 100);
    return pct >= MIN_WEIGHT_PCT && pct <= MAX_WEIGHT_PCT;
  });
  const isCustom = !areWeightsEqual(weights, defaultWeights);

  const handlePercentChange = (key: keyof JobScoringWeights, rawPct: string) => {
    const parsed = Number(rawPct);
    const snapped = Number.isFinite(parsed)
      ? Math.round(parsed / WEIGHT_STEP_PCT) * WEIGHT_STEP_PCT
      : MIN_WEIGHT_PCT;
    const clampedPct = Math.max(MIN_WEIGHT_PCT, Math.min(MAX_WEIGHT_PCT, snapped));
    onChange({
      ...weights,
      [key]: clampedPct / 100,
    });
  };

  const handleReset = () => {
    onChange({ ...defaultWeights });
  };

  return (
    <section
      aria-label="Matching priorities"
      className={`rounded-2xl border transition-all ${
        error || !balanced || !allInRange
          ? 'border-amber-300 bg-amber-50/30'
          : 'border-gray-200 bg-gray-50/50'
      }`}
    >
      {/* Header / Toggle */}
      <div className="px-4 py-3.5 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => setExpanded((prev) => !prev)}
          aria-expanded={expanded}
          className="flex-1 flex items-center gap-2.5 min-w-0 text-left cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#d81159] rounded-xl"
        >
          <div className="w-8 h-8 rounded-xl bg-pink-50 text-[#d81159] flex items-center justify-center shrink-0">
            <Sliders size={15} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Matching priorities
              </span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                  isCustom
                    ? 'bg-pink-50 text-[#d81159] border-pink-200'
                    : 'bg-gray-100 text-gray-600 border-gray-200'
                }`}
              >
                {isCustom ? 'Custom' : 'Default (40/30/15/10/5)'}
              </span>
              <span
                aria-live="polite"
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                  balanced
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : 'bg-amber-50 text-amber-800 border-amber-300'
                }`}
              >
                Total: {totalPct}%
              </span>
            </div>
            <p className="text-[11px] text-gray-500 mt-0.5 truncate">
              {WEIGHT_FIELDS.map((f) => `${f.shortLabel} ${Math.round(weights[f.key] * 100)}%`).join(' • ')}
            </p>
          </div>
        </button>

        <div className="flex items-center gap-2 shrink-0">
          <HelpTooltip
            label="About matching priorities"
            text="Choose what matters most for this job. A higher percentage means that part counts more in the match score."
          />
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            aria-label={expanded ? 'Collapse matching priorities' : 'Expand matching priorities'}
            className="text-gray-400 hover:text-gray-600 p-1 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-[#d81159] cursor-pointer"
          >
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
        </div>
      </div>

      {/* Expandable Body */}
      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-200/70 space-y-4">
          {/* Quick Presets */}
          {!readOnly && (
            <div>
              <span className="block text-[11px] font-bold text-slate-600 mb-2">
                Quick presets
              </span>
              <div className="flex flex-wrap gap-1.5">
                {WEIGHT_PRESETS.map((preset) => {
                  const active = areWeightsEqual(weights, preset.weights);
                  return (
                    <button
                      key={preset.label}
                      type="button"
                      onClick={() => onChange({ ...preset.weights })}
                      className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold border transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#d81159] ${
                        active
                          ? 'bg-[#d81159] text-white border-[#d81159] shadow-xs'
                          : 'bg-white text-gray-700 border-gray-200 hover:border-pink-200 hover:bg-pink-50/40'
                      }`}
                    >
                      {preset.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Visual Stacked Bar */}
          <div className="bg-gray-200/80 h-2 rounded-full overflow-hidden flex" aria-hidden="true">
            {WEIGHT_FIELDS.map((field) => {
              const pct = Math.round((weights[field.key] ?? 0) * 100);
              const share = totalPct > 0 ? (pct / totalPct) * 100 : 0;
              return (
                <div
                  key={field.key}
                  style={{ width: `${share}%` }}
                  className={`${field.color} transition-all duration-200 h-full`}
                  title={`${field.label}: ${pct}%`}
                />
              );
            })}
          </div>

          {!balanced && (
            <div
              role="alert"
              className="flex items-center justify-between gap-2 bg-amber-50 border border-amber-300 rounded-xl px-3 py-2 text-xs text-amber-900"
            >
              <div className="flex items-center gap-2">
                <AlertTriangle size={14} className="text-amber-600 shrink-0" aria-hidden="true" />
                <span>
                  <strong>Total must be 100%</strong> (currently {totalPct}%). Adjust sliders to enable saving.
                </span>
              </div>
            </div>
          )}

          {error && (
            <p role="alert" className="text-xs font-bold text-red-600">{error}</p>
          )}

          {/* Sliders */}
          <div className="space-y-3">
            {WEIGHT_FIELDS.map((field) => {
              const pct = Math.round((weights[field.key] ?? 0) * 100);
              const sliderId = `weight-slider-${field.key}`;
              const inputId = `weight-input-${field.key}`;
              return (
                <div key={field.key} className="bg-white p-3 rounded-xl border border-gray-100">
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <label
                      htmlFor={sliderId}
                      className="text-xs font-bold text-gray-800 flex items-center gap-2"
                    >
                      <span className={`w-2.5 h-2.5 rounded-full ${field.color}`} aria-hidden="true" />
                      <span>{field.label}</span>
                      <HelpTooltip label={`About ${field.label}`} text={field.tooltip} />
                    </label>
                    <div className="flex items-center gap-1">
                      <input
                        id={inputId}
                        type="number"
                        min={MIN_WEIGHT_PCT}
                        max={MAX_WEIGHT_PCT}
                        step={WEIGHT_STEP_PCT}
                        disabled={readOnly}
                        value={pct}
                        onChange={(e) => handlePercentChange(field.key, e.target.value)}
                        aria-label={`${field.label} percentage`}
                        className="w-16 px-2 py-1 text-right text-xs font-extrabold text-[#d81159] bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#d81159] disabled:opacity-60"
                      />
                      <span className="text-xs font-bold text-gray-400" aria-hidden="true">%</span>
                    </div>
                  </div>
                  <input
                    id={sliderId}
                    type="range"
                    min={MIN_WEIGHT_PCT}
                    max={MAX_WEIGHT_PCT}
                    step={WEIGHT_STEP_PCT}
                    disabled={readOnly}
                    value={pct}
                    onChange={(e) => handlePercentChange(field.key, e.target.value)}
                    aria-label={`${field.label} slider (${pct}%)`}
                    className="w-full accent-[#d81159] cursor-pointer disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-[#d81159]"
                  />
                  <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                    <span>{MIN_WEIGHT_PCT}% min</span>
                    <span>Default {field.defaultPct}%</span>
                    <span>{MAX_WEIGHT_PCT}% max</span>
                  </div>
                </div>
              );
            })}
          </div>

          {!readOnly && (
            <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
              <span className="text-[11px] text-gray-500">
                Allowed range: {MIN_WEIGHT_PCT}%–{MAX_WEIGHT_PCT}% per criterion in {WEIGHT_STEP_PCT}% steps.
              </span>
              <button
                type="button"
                onClick={handleReset}
                className="px-3 py-1.5 rounded-xl border border-gray-200 bg-white text-gray-700 font-semibold text-xs hover:bg-gray-50 transition-all cursor-pointer flex items-center gap-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#d81159]"
              >
                <RefreshCw size={13} className="text-gray-500" aria-hidden="true" /> Reset to default
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default JobScoringWeightsEditor;
