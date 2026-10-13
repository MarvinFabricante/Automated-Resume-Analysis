import React from 'react';
import { Search, Sparkles, TrendingUp, MessageSquare, ChevronRight } from 'lucide-react';
import { useNavigate } from '@/utils/navigation';

const QuickActions: React.FC = () => {
  const navigate = useNavigate();

  const ACTIONS = [
    {
      icon: Search,
      label: 'Browse Jobs',
      desc: 'Active Mariwasa openings',
      path: '/candidate/findjobs',
      iconColor: 'text-blue-600',
      iconBg: 'bg-blue-50 border-blue-100',
      hoverBorder: 'hover:border-blue-200'
    },
    {
      icon: Sparkles,
      label: 'AI Smart Match',
      desc: 'Instant resume fit scoring',
      path: '/candidate/smart-matches',
      iconColor: 'text-[#D10043]',
      iconBg: 'bg-rose-50 border-rose-100',
      hoverBorder: 'hover:border-rose-200'
    },
    {
      icon: TrendingUp,
      label: 'Track Pipeline',
      desc: 'Application status stages',
      path: '/candidate/applicationtracking',
      iconColor: 'text-emerald-600',
      iconBg: 'bg-emerald-50 border-emerald-100',
      hoverBorder: 'hover:border-emerald-200'
    },
    {
      icon: MessageSquare,
      label: 'HR Messages',
      desc: 'Inquiries & coordinator chat',
      path: '/candidate/messages',
      iconColor: 'text-purple-600',
      iconBg: 'bg-purple-50 border-purple-100',
      hoverBorder: 'hover:border-purple-200'
    }
  ];

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-5 sm:p-7 shadow-xs space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <h3 className="text-base sm:text-lg font-black text-slate-900 tracking-tight">Quick Actions</h3>
          <p className="text-xs text-slate-400 font-medium">Direct access to candidate tools</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2.5 sm:gap-3">
        {ACTIONS.map((action, i) => {
          const Icon = action.icon;
          return (
            <button
              key={i}
              type="button"
              onClick={() => navigate(action.path)}
              className={`flex flex-col justify-between p-3.5 sm:p-4 rounded-xl sm:rounded-2xl border border-slate-200/80 bg-slate-50/40 hover:bg-white ${action.hoverBorder} hover:shadow-xs transition-all duration-200 group text-left cursor-pointer`}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <div className={`w-9 h-9 rounded-xl ${action.iconBg} ${action.iconColor} border flex items-center justify-center shrink-0 shadow-2xs`}>
                  <Icon size={17} />
                </div>
                <ChevronRight size={14} className="text-slate-300 group-hover:text-slate-700 group-hover:translate-x-0.5 transition-all" />
              </div>

              <div>
                <p className="text-xs sm:text-sm font-black text-slate-900 group-hover:text-[#D10043] transition-colors leading-tight truncate">
                  {action.label}
                </p>
                <p className="text-[10px] sm:text-[11px] text-slate-400 font-medium truncate mt-0.5">
                  {action.desc}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default QuickActions;
