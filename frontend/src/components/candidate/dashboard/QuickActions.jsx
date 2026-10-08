import React from 'react';
import { Search, Sparkles, TrendingUp, Settings, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const QuickActions = () => {
  const navigate = useNavigate();

  const ACTIONS = [
    {
      icon: Search,
      label: "Find Jobs",
      desc: "Browse active openings across divisions",
      path: "/candidate/findjobs",
      badge: "Open Roles",
      badgeColor: "bg-blue-50 text-blue-700 border-blue-200"
    },
    {
      icon: Sparkles,
      label: "AI Smart Match",
      desc: "Instant resume-to-job fit scoring",
      path: "/candidate/smart-matches",
      badge: "AI Powered",
      badgeColor: "bg-pink-50 text-[#D10043] border-pink-200"
    },
    {
      icon: TrendingUp,
      label: "Application Tracking",
      desc: "Detailed stage progression timeline",
      path: "/candidate/applicationtracking",
      badge: "Pipeline",
      badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-200"
    },
    {
      icon: Settings,
      label: "Profile & Settings",
      desc: "Credentials, alerts & notification preferences",
      path: "/candidate/settings",
      badge: "Account",
      badgeColor: "bg-slate-100 text-slate-700 border-slate-200"
    }
  ];

  return (
    <div className="bg-white border border-slate-200/80 rounded-[32px] p-6 sm:p-8 shadow-sm space-y-5">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">Quick Actions</h3>
          <p className="text-xs text-slate-400 font-medium">Direct access to candidate tools</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {ACTIONS.map((action, i) => {
          const Icon = action.icon;
          return (
            <button
              key={i}
              type="button"
              onClick={() => navigate(action.path)}
              className="w-full flex items-center justify-between p-4 rounded-2xl border border-slate-200/70 bg-slate-50/50 hover:bg-white hover:border-[#D10043]/30 hover:shadow-md transition-all duration-200 group text-left"
            >
              <div className="flex items-center gap-3.5 min-w-0">
                <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-slate-500 group-hover:text-[#D10043] border border-slate-200/80 group-hover:border-[#D10043]/30 shadow-2xs transition-colors shrink-0">
                  <Icon size={18} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-xs sm:text-sm font-black text-slate-900 group-hover:text-[#D10043] transition-colors truncate">
                      {action.label}
                    </p>
                    <span className={`hidden sm:inline-block text-[9px] font-black uppercase px-2 py-0.2 rounded-full border ${action.badgeColor}`}>
                      {action.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 font-medium truncate mt-0.5">
                    {action.desc}
                  </p>
                </div>
              </div>
              <ChevronRight size={16} className="text-slate-300 group-hover:text-[#D10043] group-hover:translate-x-0.5 transition-all shrink-0 ml-2" />
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default QuickActions;
