import React from 'react';
import { MoreHorizontal, FileText, Clock, Briefcase, Zap, Users, CheckCircle2, X } from 'lucide-react';

const StatCard = ({ icon: Icon, label, value, trend, trendColor, bgColor, iconColor }) => (
  <div className="flex flex-col p-6 border border-gray-100 bg-gray-50/50 rounded-[24px] hover:bg-white hover:border-pink-100 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group">
    <div className="flex justify-between items-start mb-6">
      <div className={`w-14 h-14 ${bgColor} rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner`}>
        <Icon className={`h-6 w-6 ${iconColor}`} />
      </div>
    </div>
    
    <div className="mt-auto">
      <h4 className="text-3xl font-black tracking-tight text-gray-900 mb-1">{value}</h4>
      <p className="text-xs text-gray-500 font-bold tracking-wide uppercase">{label}</p>
      
      {trend && (
        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-100/80">
          <div className={`w-1.5 h-1.5 rounded-full ${iconColor.replace('text', 'bg')}`}></div>
          <p className={`text-[10px] font-bold tracking-wide uppercase ${trendColor}`}>
            {trend}
          </p>
        </div>
      )}
    </div>
  </div>
);

const ApplicationStatusCard = ({ appStats }) => (
  <div className="flex flex-col p-6 border border-gray-100 bg-gray-50/50 rounded-[24px] hover:bg-white hover:border-pink-100 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group md:col-span-2 xl:col-span-2">
    <div className="flex justify-between items-center mb-6">
      <div className="w-12 h-12 bg-pink-50 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner">
        <Zap className="h-5 w-5 text-[#D60041]" />
      </div>
      <span className="text-[10px] font-black tracking-widest text-[#D60041] uppercase bg-pink-50 px-3 py-1 rounded-full">
        Application Flow
      </span>
    </div>

    <div className="grid grid-cols-3 gap-4 mt-auto">
      <div className="flex flex-col">
        <h4 className="text-xl font-black text-gray-900 mb-1">{appStats?.pending || 0}</h4>
        <p className="text-[9px] text-gray-500 font-bold uppercase tracking-wider">Pending</p>
        <div className="w-full h-1 bg-orange-100 rounded-full mt-2 overflow-hidden">
          <div className="h-full bg-orange-400" style={{ width: '60%' }}></div>
        </div>
      </div>
      
      <div className="flex flex-col">
        <h4 className="text-xl font-black text-gray-900 mb-1">{appStats?.accepted || 0}</h4>
        <p className="text-[9px] text-gray-500 font-bold uppercase tracking-wider">Accepted</p>
        <div className="w-full h-1 bg-green-100 rounded-full mt-2 overflow-hidden">
          <div className="h-full bg-green-500" style={{ width: '80%' }}></div>
        </div>
      </div>

      <div className="flex flex-col">
        <h4 className="text-xl font-black text-gray-900 mb-1">{appStats?.rejected || 0}</h4>
        <p className="text-[9px] text-gray-500 font-bold uppercase tracking-wider">Rejected</p>
        <div className="w-full h-1 bg-red-100 rounded-full mt-2 overflow-hidden">
          <div className="h-full bg-red-500" style={{ width: '40%' }}></div>
        </div>
      </div>
    </div>
  </div>
);

const KeyMetrics = ({ activeJobsCount, totalCandidates, totalResumes, appStats }) => {
  return (
    <div className="bg-white border border-gray-100 rounded-[32px] p-6 sm:p-8 lg:p-10 mb-8 shadow-sm">
      <div className="flex justify-between items-start mb-8">
        <div>
          <h3 className="text-lg md:text-xl font-extrabold tracking-tight text-gray-900">Key Metrics</h3>
          <p className="text-xs md:text-sm text-gray-500 mt-1 font-medium">
            Real-time overview of your recruitment performance
          </p>
        </div>
        <button className="p-2 hover:bg-gray-50 rounded-xl transition-colors group">
          <MoreHorizontal className="w-5 h-5 text-gray-400 group-hover:text-[#D60041]" />
        </button>
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-5">
        <StatCard 
          icon={FileText} 
          label="Total Resumes" 
          value={totalResumes} 
          trend="Live Database" 
          trendColor="text-gray-500" 
          bgColor="bg-pink-50" 
          iconColor="text-[#D60041]" 
        />

        <ApplicationStatusCard appStats={appStats} />
        
        <StatCard 
          icon={Briefcase} 
          label="Active Jobs" 
          value={activeJobsCount} 
          trend="Openings" 
          trendColor="text-blue-600" 
          bgColor="bg-blue-50" 
          iconColor="text-blue-500" 
        />

        <StatCard 
          icon={Users} 
          label="Total Candidates" 
          value={totalCandidates} 
          trend="Users" 
          trendColor="text-purple-600" 
          bgColor="bg-purple-50" 
          iconColor="text-purple-500" 
        />
      </div>
    </div>
  );
};

export default KeyMetrics;