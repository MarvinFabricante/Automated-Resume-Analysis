import React, { useMemo } from 'react';
import { ShieldCheck, CheckCircle2, ChevronRight, Sparkles, User, FileText, Briefcase, Award } from 'lucide-react';
import { useNavigate } from '@/utils/navigation';
import { useSelector } from 'react-redux';
import { RootState } from '../../../redux/store';

const ProfileStrength: React.FC = () => {
  const navigate = useNavigate();
  const { user: email } = useSelector((state: RootState) => state.auth);

  // Calculate dynamic completeness based on available candidate profile data
  const { completionPercentage, checklist } = useMemo(() => {
    const fullname = typeof localStorage !== 'undefined' ? localStorage.getItem('fullname') : null;
    const phone = typeof localStorage !== 'undefined' ? localStorage.getItem('phone') : null;
    const hasResume = typeof localStorage !== 'undefined' ? Boolean(localStorage.getItem('candidate_resume_uploaded') || localStorage.getItem('draft_application_job_id')) : false;

    const items = [
      {
        id: 'personal',
        label: 'Personal Name & Account',
        completed: Boolean(fullname && email),
        points: 25,
        icon: User
      },
      {
        id: 'contact',
        label: 'Contact & Phone Details',
        completed: Boolean(phone && phone.length > 5),
        points: 25,
        icon: ShieldCheck
      },
      {
        id: 'resume',
        label: 'Primary Resume Uploaded',
        completed: hasResume,
        points: 25,
        icon: FileText
      },
      {
        id: 'experience',
        label: 'Work History & Credentials',
        completed: Boolean(fullname && hasResume),
        points: 25,
        icon: Briefcase
      }
    ];

    const completedPoints = items.reduce((acc, item) => (item.completed ? acc + item.points : acc), 0);
    // Ensure base score of at least 50% for logged-in candidates
    const finalScore = Math.max(50, completedPoints);

    return {
      completionPercentage: finalScore,
      checklist: items
    };
  }, [email]);

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-5 sm:p-7 shadow-xs space-y-4">
      
      {/* Top Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 border border-emerald-100">
            <ShieldCheck size={16} />
          </div>
          <div>
            <h4 className="text-xs sm:text-sm font-black text-slate-900 tracking-tight">
              Profile Readiness
            </h4>
            <p className="text-[10px] text-slate-400 font-medium">ATS candidate score</p>
          </div>
        </div>

        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200/60 font-mono">
          {completionPercentage}% Complete
        </span>
      </div>

      {/* Progress Bar & Value */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-slate-700">Completeness</span>
          <span className="font-mono font-black text-[#D10043]">{completionPercentage}%</span>
        </div>
        
        <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
          <div
            style={{ width: `${completionPercentage}%` }}
            className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-500"
          />
        </div>
        
        <p className="text-[11px] text-slate-400 font-medium leading-relaxed pt-0.5">
          A high readiness score improves automated ARAS job matching and HR evaluation priority.
        </p>
      </div>

      {/* Checklist items */}
      <div className="space-y-2 pt-2 border-t border-slate-100">
        {checklist.map((item) => (
          <div
            key={item.id}
            onClick={() => navigate('/candidate/settings')}
            className="flex items-center justify-between text-xs py-1 px-1.5 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer group"
          >
            <span className={`font-semibold transition-colors ${item.completed ? 'text-slate-700' : 'text-slate-500 group-hover:text-[#D10043]'}`}>
              {item.label}
            </span>
            {item.completed ? (
              <CheckCircle2 size={15} className="text-emerald-500 shrink-0" />
            ) : (
              <span className="text-[9px] font-black text-amber-700 bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200/80">
                +{item.points}%
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Action Button */}
      <button
        type="button"
        onClick={() => navigate('/candidate/settings')}
        className="w-full py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-[#D10043] text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all active:scale-[0.98] cursor-pointer"
      >
        <span>Manage Profile Details</span>
        <ChevronRight size={13} />
      </button>

    </div>
  );
};

export default ProfileStrength;
