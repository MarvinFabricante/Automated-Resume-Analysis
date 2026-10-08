import React from 'react';
import { ShieldCheck, CheckCircle2, ChevronRight, Sparkles, Award } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const ProfileStrength = () => {
  const navigate = useNavigate();

  const completionPercentage = 85;

  const CHECKLIST = [
    { label: "Personal Details & Contact", completed: true },
    { label: "Primary Resume Uploaded", completed: true },
    { label: "Work History & Education", completed: true },
    { label: "Certifications & Licensure", completed: false }
  ];

  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-[32px] p-6 sm:p-8 shadow-md relative overflow-hidden space-y-6">
      {/* Decorative ambient gradient */}
      <div className="absolute -top-12 -right-12 w-44 h-44 bg-[#D10043]/20 rounded-full blur-2xl pointer-events-none" />

      <div className="relative z-10 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center text-[#D10043]">
            <Sparkles size={16} />
          </div>
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-300">
            Profile Readiness
          </span>
        </div>
        <span className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
          <ShieldCheck size={12} />
          Verified
        </span>
      </div>

      {/* Progress & Headline */}
      <div className="relative z-10 space-y-2">
        <div className="flex items-baseline justify-between">
          <h4 className="text-xl font-black tracking-tight text-white">Profile Strength</h4>
          <span className="text-2xl font-black text-[#D10043] font-mono">{completionPercentage}%</span>
        </div>
        
        {/* Progress Bar */}
        <div className="w-full bg-slate-700/60 h-2.5 rounded-full overflow-hidden p-0.5 border border-slate-700">
          <div
            style={{ width: `${completionPercentage}%` }}
            className="h-full bg-gradient-to-r from-rose-500 to-[#D10043] rounded-full transition-all duration-700"
          />
        </div>
        
        <p className="text-xs text-slate-400 font-medium leading-relaxed pt-1">
          A high completeness score improves automated job matching accuracy and recruiter visibility by up to 40%.
        </p>
      </div>

      {/* Checklist items */}
      <div className="relative z-10 space-y-2.5 pt-2 border-t border-slate-700/60">
        {CHECKLIST.map((item, idx) => (
          <div key={idx} className="flex items-center justify-between text-xs">
            <span className={`font-medium ${item.completed ? 'text-slate-300' : 'text-slate-400'}`}>
              {item.label}
            </span>
            {item.completed ? (
              <CheckCircle2 size={15} className="text-emerald-400 shrink-0" />
            ) : (
              <span className="text-[10px] font-bold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-md border border-amber-400/20">
                +15%
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Action Button */}
      <button
        type="button"
        onClick={() => navigate('/candidate/settings')}
        className="w-full py-3 px-4 rounded-xl bg-white hover:bg-slate-100 text-slate-900 font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-sm active:scale-[0.98]"
      >
        Complete Profile Details
        <ChevronRight size={14} />
      </button>

    </div>
  );
};

export default ProfileStrength;
