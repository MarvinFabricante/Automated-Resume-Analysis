import React, { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  Settings2, 
  Sliders, 
  Save, 
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Sparkles,
  Scale,
  ShieldCheck,
  Target,
  Percent,
  SlidersHorizontal
} from 'lucide-react';
import toast from 'react-hot-toast';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { 
  useGetMatchingConfigQuery,
  useUpdateMatchingWeightsMutation,
  useUpdateMatchingThresholdsMutation,
  useRecalculateMatchingScoresMutation
} from '../../redux/api/apiSlice';

interface MatchingWeights {
  skills_weight: number;
  experience_weight: number;
  education_weight: number;
  certifications_weight: number;
  location_weight: number;
}

interface MatchingThresholds {
  fuzzy_match_threshold: number;
  minimum_match_score: number;
  transferable_skills_cap: number;
  ai_score_weight?: number;
  rule_score_weight?: number;
}

interface MatchingConfig {
  weights: MatchingWeights;
  thresholds: MatchingThresholds;
}

const DEFAULT_WEIGHTS: MatchingWeights = {
  skills_weight: 0.45,
  experience_weight: 0.25,
  education_weight: 0.15,
  certifications_weight: 0.10,
  location_weight: 0.05
};

const DEFAULT_THRESHOLDS: MatchingThresholds = {
  fuzzy_match_threshold: 0.75,
  minimum_match_score: 30.0,
  transferable_skills_cap: 2
};

const SystemSettings: React.FC = () => {
  const { data: config, isLoading, refetch } = useGetMatchingConfigQuery() as {
    data: MatchingConfig | undefined;
    isLoading: boolean;
    refetch: () => void;
  };

  const [updateWeights] = useUpdateMatchingWeightsMutation();
  const [updateThresholds] = useUpdateMatchingThresholdsMutation();
  const [recalculateScores, { isLoading: isRecalculating }] = useRecalculateMatchingScoresMutation();

  const [weights, setWeights] = useState<MatchingWeights>(DEFAULT_WEIGHTS);
  const [thresholds, setThresholds] = useState<MatchingThresholds>(DEFAULT_THRESHOLDS);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [showRecalcConfirm, setShowRecalcConfirm] = useState<boolean>(false);

  useEffect(() => {
    if (config) {
      if (config.weights) {
        setWeights({
          skills_weight: config.weights.skills_weight ?? DEFAULT_WEIGHTS.skills_weight,
          experience_weight: config.weights.experience_weight ?? DEFAULT_WEIGHTS.experience_weight,
          education_weight: config.weights.education_weight ?? DEFAULT_WEIGHTS.education_weight,
          certifications_weight: config.weights.certifications_weight ?? DEFAULT_WEIGHTS.certifications_weight,
          location_weight: config.weights.location_weight ?? DEFAULT_WEIGHTS.location_weight,
        });
      }
      if (config.thresholds) {
        setThresholds({
          fuzzy_match_threshold: config.thresholds.fuzzy_match_threshold ?? DEFAULT_THRESHOLDS.fuzzy_match_threshold,
          minimum_match_score: config.thresholds.minimum_match_score ?? DEFAULT_THRESHOLDS.minimum_match_score,
          transferable_skills_cap: config.thresholds.transferable_skills_cap ?? DEFAULT_THRESHOLDS.transferable_skills_cap,
        });
      }
    }
  }, [config]);

  const handleWeightChange = (key: keyof MatchingWeights, rawValue: string) => {
    const val = parseFloat(rawValue) || 0;
    setWeights(prev => ({ ...prev, [key]: Math.max(0, Math.min(1, val)) }));
  };

  const handleThresholdChange = (key: keyof MatchingThresholds, rawValue: string) => {
    const val = parseFloat(rawValue) || 0;
    setThresholds(prev => ({ ...prev, [key]: val }));
  };

  // Auto-normalize weights so they sum to exactly 1.0 (100%)
  const handleAutoBalance = () => {
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    if (total <= 0) {
      setWeights(DEFAULT_WEIGHTS);
      toast.success("Reset weights to standard default distribution.");
      return;
    }
    const factor = 1.0 / total;
    setWeights({
      skills_weight: Math.round(weights.skills_weight * factor * 100) / 100,
      experience_weight: Math.round(weights.experience_weight * factor * 100) / 100,
      education_weight: Math.round(weights.education_weight * factor * 100) / 100,
      certifications_weight: Math.round(weights.certifications_weight * factor * 100) / 100,
      location_weight: Math.round(weights.location_weight * factor * 100) / 100,
    });
    toast.success("Weights automatically balanced to sum to 100%.");
  };

  const handleResetDefaults = () => {
    setWeights(DEFAULT_WEIGHTS);
    setThresholds(DEFAULT_THRESHOLDS);
    toast.success("Restored system settings to recommended defaults.");
  };

  const handleDiscard = () => {
    if (config) {
      if (config.weights) setWeights(config.weights);
      if (config.thresholds) setThresholds(config.thresholds);
      toast("Changes discarded, restored to saved server configuration.", { icon: "↩️" });
    } else {
      setWeights(DEFAULT_WEIGHTS);
      setThresholds(DEFAULT_THRESHOLDS);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateWeights(weights).unwrap();
      await updateThresholds(thresholds).unwrap();
      toast.success("System configuration saved successfully!");
      refetch();
    } catch (err: any) {
      console.error("Failed to save matching parameters:", err);
      toast.error(err?.data?.detail || "Failed to save configuration. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleRecalculateApplications = async () => {
    setShowRecalcConfirm(false);
    try {
      const res = await recalculateScores().unwrap();
      const updatedCount = res?.updated_applications ?? 0;
      toast.success(`Successfully re-evaluated ${updatedCount} candidate applications with active parameters!`);
    } catch (err: any) {
      console.error("Failed to recalculate scores:", err);
      toast.error(err?.data?.detail || "Failed to recalculate application scores.");
    }
  };

  const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0);
  const totalWeightPct = Math.round(totalWeight * 100);
  const isBalanced = Math.abs(totalWeight - 1.0) <= 0.01;

  const weightFields: Array<{
    key: keyof MatchingWeights;
    label: string;
    description: string;
    color: string;
  }> = [
    { 
      key: 'skills_weight', 
      label: 'Skills & Keywords', 
      description: 'Direct and semantic alignment of candidate technical skills against required competencies.',
      color: 'bg-rose-500' 
    },
    { 
      key: 'experience_weight', 
      label: 'Experience Relevance', 
      description: 'Domain alignment, responsibilities matching via NLP verb-object analysis, and career years.',
      color: 'bg-blue-500' 
    },
    { 
      key: 'education_weight', 
      label: 'Education & Degree', 
      description: 'Degree level comparison according to the educational hierarchy and relevant majors.',
      color: 'bg-emerald-500' 
    },
    { 
      key: 'certifications_weight', 
      label: 'Certifications', 
      description: 'Presence of mandatory and preferred industry certifications and accreditations.',
      color: 'bg-purple-500' 
    },
    { 
      key: 'location_weight', 
      label: 'Location Match', 
      description: 'Geographic proximity or willingness to relocate to the specified job facility/plant.',
      color: 'bg-amber-500' 
    },
  ];

  return (
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
      <Helmet>
        <title>System Settings - Matching Algorithm | Mariwasa ARA</title>
      </Helmet>
      
      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        
        <main className="flex-1 max-w-[1400px] mx-auto px-6 lg:px-10 py-10">
          
          {/* Header section */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
            <div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-red-50 text-[#D10043] flex items-center justify-center shadow-sm">
                  <Settings2 size={22} />
                </div>
                <div>
                  <h1 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-gray-900">
                    System Settings
                  </h1>
                  <p className="text-xs text-gray-500 font-medium mt-0.5">
                    Configure matching algorithm weights, similarity thresholds, and qualification cutoffs.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200/60 text-emerald-700 text-xs font-semibold">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Local spaCy NLP Engine Active
              </span>
            </div>
          </div>

          {isLoading ? (
            <div className="py-24 text-center">
              <div className="w-10 h-10 border-3 border-[#D10043] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-sm font-semibold text-gray-500">Loading system configuration...</p>
            </div>
          ) : (
            <div className="space-y-8 animate-in fade-in duration-300">
              
              {/* Weight balance status notice */}
              {!isBalanced && (
                <div className="bg-amber-50/90 border border-amber-200 text-amber-900 px-5 py-4 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={20} className="text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-bold text-sm">Weights sum to {totalWeightPct}% (Target: 100%)</h4>
                      <p className="text-xs text-amber-700 mt-0.5">
                        The matching algorithm automatically normalizes weights proportionally, but balancing to 100% ensures exact intuitive breakdowns.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleAutoBalance}
                    className="self-start sm:self-center px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold transition-all shadow-xs shrink-0 cursor-pointer flex items-center gap-1.5"
                  >
                    <Scale size={14} /> Auto-Balance to 100%
                  </button>
                </div>
              )}

              {/* Main 2-column Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                
                {/* Left Column: Algorithm Weights (7 cols) */}
                <div className="lg:col-span-7 bg-white border border-gray-100 rounded-3xl p-6 lg:p-8 shadow-xs">
                  <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-red-50 text-[#D10043] flex items-center justify-center">
                        <Sliders size={18} />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-gray-900">Base Algorithm Component Weights</h2>
                        <p className="text-xs text-gray-400">Relative contribution of each dimension to candidate composite scores</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                        isBalanced 
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                          : 'bg-amber-50 text-amber-700 border-amber-200'
                      }`}>
                        Total: {totalWeightPct}%
                      </span>
                    </div>
                  </div>

                  {/* Total Weight Visual Bar */}
                  <div className="mb-6 bg-gray-100 h-2.5 rounded-full overflow-hidden flex">
                    {weightFields.map(field => {
                      const share = totalWeight > 0 ? (weights[field.key] / totalWeight) * 100 : 0;
                      return (
                        <div
                          key={field.key}
                          style={{ width: `${share}%` }}
                          className={`${field.color} transition-all duration-300 h-full`}
                          title={`${field.label}: ${Math.round(weights[field.key] * 100)}%`}
                        />
                      );
                    })}
                  </div>

                  {/* Sliders list */}
                  <div className="space-y-6">
                    {weightFields.map(item => {
                      const pct = Math.round(weights[item.key] * 100);
                      return (
                        <div key={item.key} className="bg-gray-50/70 hover:bg-gray-50 transition-colors p-4 rounded-2xl border border-gray-100">
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-xs font-bold text-gray-900 flex items-center gap-2">
                              <span className={`w-2.5 h-2.5 rounded-full ${item.color}`}></span>
                              {item.label}
                            </span>
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-extrabold text-[#D10043] bg-white px-2.5 py-0.5 rounded-lg border border-gray-200 shadow-2xs">
                                {pct}%
                              </span>
                            </div>
                          </div>
                          <p className="text-[11px] text-gray-500 mb-3 leading-relaxed">
                            {item.description}
                          </p>
                          <div className="flex items-center gap-3">
                            <input 
                              type="range" 
                              min="0" 
                              max="1" 
                              step="0.01" 
                              value={weights[item.key]}
                              onChange={(e) => handleWeightChange(item.key, e.target.value)}
                              className="w-full accent-[#D10043] cursor-pointer"
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Weight Quick Actions */}
                  <div className="mt-6 pt-4 border-t border-gray-100 flex flex-wrap gap-2 justify-end">
                    <button
                      type="button"
                      onClick={handleAutoBalance}
                      className="px-3.5 py-1.5 rounded-xl border border-gray-200 text-gray-700 font-semibold text-xs hover:bg-gray-50 transition-all cursor-pointer flex items-center gap-1.5"
                    >
                      <Scale size={13} className="text-gray-500" /> Auto-Normalize
                    </button>
                    <button
                      type="button"
                      onClick={handleResetDefaults}
                      className="px-3.5 py-1.5 rounded-xl border border-gray-200 text-gray-700 font-semibold text-xs hover:bg-gray-50 transition-all cursor-pointer flex items-center gap-1.5"
                    >
                      <RefreshCw size={13} className="text-gray-500" /> Standard ATS Defaults
                    </button>
                  </div>
                </div>

                {/* Right Column: Thresholds & Sensitivity (5 cols) */}
                <div className="lg:col-span-5 space-y-6">
                  
                  {/* Thresholds Card */}
                  <div className="bg-white border border-gray-100 rounded-3xl p-6 lg:p-8 shadow-xs">
                    <div className="flex items-center gap-2.5 mb-6 pb-4 border-b border-gray-100">
                      <div className="w-8 h-8 rounded-xl bg-red-50 text-[#D10043] flex items-center justify-center">
                        <SlidersHorizontal size={18} />
                      </div>
                      <div>
                        <h2 className="text-base font-bold text-gray-900">Algorithm Sensitivity & Limits</h2>
                        <p className="text-xs text-gray-400">Similarity cutoffs and qualification rules</p>
                      </div>
                    </div>

                    <div className="space-y-6">
                      
                      {/* Fuzzy Match Threshold */}
                      <div className="p-4 rounded-2xl bg-gray-50/70 border border-gray-100">
                        <div className="flex justify-between items-center mb-1.5">
                          <label className="text-xs font-bold text-gray-900 flex items-center gap-1.5">
                            <Target size={14} className="text-[#D10043]" /> Fuzzy Match Threshold
                          </label>
                          <span className="text-xs font-extrabold text-gray-800 bg-white px-2 py-0.5 rounded-md border border-gray-200">
                            {Math.round(thresholds.fuzzy_match_threshold * 100)}%
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-500 mb-3 leading-relaxed">
                          Minimum character/token sequence similarity required to recognize variations and typos in skill and certification keywords.
                        </p>
                        <input 
                          type="range" 
                          min="0.50" 
                          max="1.00" 
                          step="0.05" 
                          value={thresholds.fuzzy_match_threshold}
                          onChange={(e) => handleThresholdChange('fuzzy_match_threshold', e.target.value)}
                          className="w-full accent-[#D10043] cursor-pointer"
                        />
                        <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                          <span>0.50 (Loose)</span>
                          <span>0.75 (Recommended)</span>
                          <span>1.00 (Strict)</span>
                        </div>
                      </div>

                      {/* Minimum Match Score */}
                      <div className="p-4 rounded-2xl bg-gray-50/70 border border-gray-100">
                        <div className="flex justify-between items-center mb-1.5">
                          <label className="text-xs font-bold text-gray-900 flex items-center gap-1.5">
                            <Percent size={14} className="text-[#D10043]" /> Minimum Qualification Score
                          </label>
                          <span className="text-xs font-extrabold text-gray-800 bg-white px-2 py-0.5 rounded-md border border-gray-200">
                            {thresholds.minimum_match_score}%
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-500 mb-3 leading-relaxed">
                          Overall score percentage cutoff required for candidate applications to be flagged as qualified for job positions.
                        </p>
                        <input 
                          type="range" 
                          min="10" 
                          max="80" 
                          step="5" 
                          value={thresholds.minimum_match_score}
                          onChange={(e) => handleThresholdChange('minimum_match_score', e.target.value)}
                          className="w-full accent-[#D10043] cursor-pointer"
                        />
                        <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                          <span>10% (Permissive)</span>
                          <span>30% (Standard)</span>
                          <span>80% (Strict)</span>
                        </div>
                      </div>

                      {/* Transferable Skills Cap */}
                      <div className="p-4 rounded-2xl bg-gray-50/70 border border-gray-100">
                        <div className="flex justify-between items-center mb-1.5">
                          <label className="text-xs font-bold text-gray-900 flex items-center gap-1.5">
                            <ShieldCheck size={14} className="text-[#D10043]" /> Transferable Skills Cap
                          </label>
                          <span className="text-xs font-extrabold text-gray-800 bg-white px-2 py-0.5 rounded-md border border-gray-200">
                            {thresholds.transferable_skills_cap} pts max
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-500 mb-3 leading-relaxed">
                          Maximum points awarded for cross-domain soft or transferable skills when candidate lacks direct technical alignment.
                        </p>
                        <div className="flex items-center gap-3">
                          {[0, 1, 2, 3, 4, 5].map(cap => (
                            <button
                              key={cap}
                              type="button"
                              onClick={() => handleThresholdChange('transferable_skills_cap', cap.toString())}
                              className={`flex-1 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                                thresholds.transferable_skills_cap === cap
                                  ? 'bg-[#D10043] text-white shadow-xs'
                                  : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-100'
                              }`}
                            >
                              {cap}
                            </button>
                          ))}
                        </div>
                      </div>

                    </div>
                  </div>

                  {/* Applications Re-evaluation Card */}
                  <div className="bg-linear-to-br from-red-50/60 to-rose-50/30 border border-red-100 rounded-3xl p-6 shadow-xs">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-xl bg-white text-[#D10043] flex items-center justify-center shrink-0 shadow-2xs">
                        <Sparkles size={16} />
                      </div>
                      <div>
                        <h3 className="text-xs font-bold text-gray-900">Synchronize Existing Applications</h3>
                        <p className="text-[11px] text-gray-600 mt-1 leading-relaxed">
                          Re-score all existing candidate applications in the database using the updated algorithm weights and threshold rules.
                        </p>
                        <button
                          type="button"
                          onClick={() => setShowRecalcConfirm(true)}
                          disabled={isRecalculating}
                          className="mt-3.5 px-4 py-2 bg-white hover:bg-gray-50 text-[#D10043] border border-red-200 rounded-xl font-bold text-xs transition-all shadow-2xs hover:shadow-xs flex items-center gap-2 cursor-pointer disabled:opacity-60"
                        >
                          <RefreshCw size={13} className={isRecalculating ? "animate-spin" : ""} />
                          {isRecalculating ? "Re-evaluating..." : "Re-evaluate All Applications"}
                        </button>
                      </div>
                    </div>
                  </div>

                </div>

              </div>

              {/* Bottom Sticky Action Bar */}
              <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <CheckCircle2 size={16} className="text-emerald-500" />
                  <span>Changes take effect immediately across all candidate matching workflows and Celery background workers.</span>
                </div>

                <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                  <button 
                    type="button"
                    onClick={handleDiscard}
                    className="px-4 py-2.5 rounded-xl border border-gray-200 text-gray-700 font-bold text-xs hover:bg-gray-50 flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <RotateCcw size={14} /> Discard Changes
                  </button>

                  <button 
                    type="button"
                    onClick={handleSave}
                    disabled={isSaving}
                    className="bg-[#D10043] text-white px-6 py-2.5 rounded-xl font-bold text-xs hover:bg-[#b00038] flex items-center gap-2 transition-all disabled:opacity-70 shadow-md shadow-red-200 cursor-pointer"
                  >
                    <Save size={14} />
                    {isSaving ? 'Saving Changes...' : 'Save Configuration'}
                  </button>
                </div>
              </div>

            </div>
          )}

        </main>
      </div>

      {/* Recalculate Confirmation Modal */}
      {showRecalcConfirm && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-gray-100 animate-in fade-in zoom-in-95 duration-200">
            <div className="w-12 h-12 rounded-2xl bg-red-50 text-[#D10043] flex items-center justify-center mb-4">
              <RefreshCw size={24} />
            </div>
            <h3 className="text-lg font-extrabold text-gray-900">Re-evaluate Candidate Scores?</h3>
            <p className="text-xs text-gray-500 mt-2 leading-relaxed">
              This will recompute the ATS match percentage, skill breakdowns, and explanations for all existing job applications using your currently active configuration.
            </p>
            <p className="text-xs font-semibold text-gray-700 mt-2 bg-gray-50 p-2.5 rounded-xl">
              Make sure you have saved your desired weights before proceeding.
            </p>

            <div className="flex gap-3 mt-6">
              <button
                type="button"
                onClick={() => setShowRecalcConfirm(false)}
                className="flex-1 py-2.5 rounded-xl border border-gray-200 text-gray-700 font-bold text-xs hover:bg-gray-50 transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRecalculateApplications}
                className="flex-1 py-2.5 rounded-xl bg-[#D10043] hover:bg-[#b00038] text-white font-bold text-xs transition-all shadow-md shadow-red-100 cursor-pointer"
              >
                Start Re-evaluation
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default SystemSettings;
