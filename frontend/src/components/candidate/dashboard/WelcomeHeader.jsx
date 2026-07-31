import React from 'react';
import { Zap, Sparkles, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const WelcomeHeader = () => {
  const navigate = useNavigate();
  const fullname = localStorage.getItem('fullname') || 'Candidate';

  return (
    <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-12 gap-6 animate-in fade-in slide-in-from-top-4 duration-700">
      <div>
        <div className="flex items-center gap-2 bg-[#D10043]/5 text-[#D10043] px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-[0.2em] mb-3 border border-[#D10043]/10 w-fit">
          <Zap size={12} className="animate-pulse" />
          Portal Overview
        </div>
        <h2 className="text-4xl font-black tracking-tight text-slate-900 leading-none">
          Welcome back, <span className="text-[#D10043]">{fullname}</span>
        </h2>
        <p className="text-slate-400 font-bold text-sm mt-3 uppercase tracking-widest max-w-md">
          Your application journey is moving fast. Check your latest status and updates below.
        </p>
      </div>

      {/* <button
        onClick={() => navigate('/careerspage')}
        className="bg-[#D10043] text-white px-8 py-4 rounded-2xl hover:bg-slate-900 transition-all text-xs font-black uppercase tracking-widest shadow-xl shadow-pink-100 flex items-center group active:scale-[0.95]"
      >
        Explore New Opportunities
        <ChevronRight size={16} className="ml-3 group-hover:translate-x-1 transition-transform" />
      </button> */}
    </div>
  );
};

export default WelcomeHeader;
