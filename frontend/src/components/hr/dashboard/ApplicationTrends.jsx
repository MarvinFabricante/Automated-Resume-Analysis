import React from 'react';
import {
  MoreHorizontal, TrendingUp, Calendar, Zap,
  PieChart as PieIcon, Briefcase, Filter, ChevronRight
} from 'lucide-react';
import { useGetDashboardTrendsQuery } from '../../../redux/api/apiSlice';

const ApplicationTrends = () => {
  const { data, isLoading, error } = useGetDashboardTrendsQuery();

  const weeklyTrends = data?.weekly_trends || [];
  const distributionData = data?.department_distribution || [];
  const totalApps = data?.total_applications || 0;

  // Find max applications to calculate relative heights
  const maxApps = Math.max(...weeklyTrends.map(d => d.applications), 0);
  const peakDay = weeklyTrends.find(d => d.applications === maxApps && maxApps > 0);

  const chartData = weeklyTrends.map(d => {
    const pct = maxApps > 0 ? (d.applications / maxApps) * 90 : 0;
    return {
      ...d,
      height: `${Math.max(pct, d.applications > 0 ? 5 : 0)}%`,
      isPeak: peakDay && d.date === peakDay.date
    };
  });

  const displayMax = maxApps > 0 ? maxApps : 100;
  const label75 = Math.round(displayMax * 0.75);
  const label50 = Math.round(displayMax * 0.5);
  const label25 = Math.round(displayMax * 0.25);

  let currentPercentage = 0;
  const conicParts = [];
  distributionData.forEach(item => {
    const pct = parseFloat(item.percentage) || 0;
    if (pct > 0) {
      const nextPercentage = currentPercentage + pct;
      conicParts.push(`${item.color} ${currentPercentage}% ${nextPercentage}%`);
      currentPercentage = nextPercentage;
    }
  });
  if (currentPercentage < 100) {
    conicParts.push(`#E2E8F0 ${currentPercentage}% 100%`);
  }
  const conicGradientString = `conic-gradient(${conicParts.join(', ')})`;

  if (isLoading) {
    return (
      <div className="space-y-8 mb-8">
        <div className="bg-white border border-gray-100 rounded-[32px] p-6 sm:p-8 lg:p-10 shadow-sm h-[400px] flex flex-col justify-between animate-pulse">
          <div className="space-y-2">
            <div className="h-6 bg-gray-100 rounded w-1/4"></div>
            <div className="h-4 bg-gray-50 rounded w-1/3"></div>
          </div>
          <div className="h-48 bg-gray-50 rounded-2xl w-full"></div>
          <div className="h-8 bg-gray-100 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-100 text-red-700 p-6 rounded-[32px] mb-8 text-center font-medium">
        Failed to load application trends data. Please try again later.
      </div>
    );
  }

  return (
    <div className="space-y-8 mb-8">
      {/* 1. Bar Chart Section */}
      <div className="bg-white border border-gray-100 rounded-[32px] p-6 sm:p-8 lg:p-10 shadow-sm relative overflow-hidden group/container">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-pink-50/30 rounded-full blur-3xl pointer-events-none group-hover/container:bg-pink-100/40 transition-colors duration-700"></div>

        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-xl md:text-2xl font-black tracking-tight text-gray-900">Application Trends</h3>
              <span className="bg-green-50 text-green-600 text-[10px] font-bold px-2 py-0.5 rounded-md flex items-center gap-1 border border-green-100">
                <TrendingUp size={10} /> Live Data
              </span>
            </div>
            <p className="text-xs md:text-sm text-gray-500 font-bold tracking-tight">Submission volume analysis for the past 7 days</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-4 mr-4 pr-4 border-r border-gray-100">
              <div className="text-right">
                <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Weekly Peak</p>
                <p className="text-sm font-black text-gray-900">{maxApps} Applications</p>
              </div>
              <div className="w-10 h-10 bg-pink-50 rounded-xl flex items-center justify-center">
                <Zap className="text-[#D60041] h-5 w-5" />
              </div>
            </div>
            <button className="bg-gray-50 hover:bg-gray-100 p-2.5 rounded-xl transition-all group shadow-sm border border-gray-100">
              <Calendar className="w-5 h-5 text-gray-500 group-hover:text-gray-900" />
            </button>
            <button className="bg-gray-50 hover:bg-gray-100 p-2.5 rounded-xl transition-all group shadow-sm border border-gray-100">
              <MoreHorizontal className="w-5 h-5 text-gray-400 group-hover:text-[#D60041]" />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto scrollbar-hide pb-12 -mx-2 px-2 relative z-10">
          <div className="min-w-[700px] h-[320px] relative mt-6 pl-10">
            {/* Y-Axis Labels */}
            <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-[11px] text-gray-400 font-black tracking-widest py-0 pr-4">
              <span>{displayMax}</span><span>{label75}</span><span>{label50}</span><span>{label25}</span><span className="text-gray-300">0</span>
            </div>

            {/* Grid Lines */}
            <div className="absolute inset-0 pl-10 flex flex-col justify-between w-full h-full pointer-events-none">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="border-t border-gray-100/80 w-full h-px relative" />
              ))}
            </div>

            {/* Chart Bars */}
            <div className="w-full h-full flex items-end justify-between px-10 relative">
              {chartData.map((data, index) => (
                <div key={index} className="flex flex-col items-center group h-full justify-end w-1/12 relative">
                  <div className="absolute -top-16 left-1/2 -translate-x-1/2 bg-gray-900 text-white p-3 rounded-2xl opacity-0 group-hover:opacity-100 group-hover:-translate-y-2 transition-all duration-300 pointer-events-none shadow-2xl z-20 min-w-[120px]">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[10px] text-gray-400 font-bold uppercase">{data.date}</span>
                      <span className={`text-[9px] font-black ${data.growth.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>{data.growth}</span>
                    </div>
                    <div className="text-sm font-black">{data.applications} Applications</div>
                    <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-gray-900 rotate-45"></div>
                  </div>

                  <div className="w-full flex flex-col items-center h-full justify-end cursor-pointer">
                    {data.isPeak && (
                      <div className="absolute top-0 mb-2 flex flex-col items-center opacity-40 group-hover:opacity-100 transition-opacity">
                        <div className="text-[9px] font-black text-[#D60041] uppercase tracking-tighter bg-pink-50 px-2 py-0.5 rounded-full mb-1">Peak Day</div>
                        <div className="w-px h-full bg-[#D60041] border-dashed border-l border-pink-200"></div>
                      </div>
                    )}
                    <div
                      className={`w-full max-w-[48px] relative rounded-t-[14px] transition-all duration-700 ease-[cubic-bezier(0.34,1.56,0.64,1)] 
                        ${data.isPeak
                          ? 'bg-gradient-to-t from-[#D60041] to-[#ff4d7d] shadow-[0_4px_20px_rgba(214,0,65,0.2)]'
                          : 'bg-gradient-to-t from-gray-50 to-gray-200 group-hover:from-pink-100 group-hover:to-[#D60041] group-hover:shadow-[0_4px_20px_rgba(214,0,65,0.15)]'
                        }`}
                      style={{ height: data.height }}
                    >
                      <div className="absolute inset-x-0 top-0 h-1/2 bg-white/10 rounded-t-[14px]"></div>
                    </div>
                  </div>
                  <div className="absolute -bottom-10 flex flex-col items-center">
                    <span className="text-[11px] text-gray-900 font-black tracking-tight group-hover:text-[#D60041] transition-colors">{data.day}</span>
                    <span className="text-[9px] text-gray-400 font-bold mt-0.5">{data.date.split(' ')[1]}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-16 flex flex-wrap items-center gap-8 pt-8 border-t border-gray-50 relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-gradient-to-br from-pink-400 to-[#D60041]"></div>
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">Total Submissions</span>
          </div>
          <div className="ml-auto flex items-center gap-2 text-xs font-bold text-gray-400">
            <Calendar size={14} /> Last Updated: {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>

      {/* 2. Pie Chart Section (Application Distribution) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 bg-white border border-gray-100 rounded-[32px] p-8 shadow-sm group/pie relative overflow-hidden">
          <div className="absolute bottom-0 left-0 -ml-12 -mb-12 w-48 h-48 bg-blue-50/30 rounded-full blur-3xl pointer-events-none"></div>

          <div className="flex justify-between items-center mb-8 relative z-10">
            <div>
              <h3 className="text-xl font-black tracking-tight text-gray-900 flex items-center gap-2">
                <PieIcon size={20} className="text-[#D60041]" />
                Job Distribution
              </h3>
              <p className="text-xs text-gray-400 font-bold uppercase tracking-widest mt-1">By Department</p>
            </div>
          </div>

          <div className="flex flex-col md:flex-row items-center justify-around gap-12 relative z-10">
            {/* Visual Pie Representation (CSS Based) */}
            <div className="relative w-48 h-48 md:w-56 md:h-56 shrink-0">
              <div className="absolute inset-0 rounded-full border-[18px] border-gray-50"></div>
              <div
                className="absolute inset-0 rounded-full border-[18px] transition-transform duration-1000 group-hover/pie:scale-105"
                style={{
                  borderImageSource: conicGradientString,
                  borderImageSlice: 1,
                  borderRadius: '50%',
                  background: conicGradientString,
                  WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
                  WebkitMaskComposite: 'xor',
                  padding: '18px'
                }}
              ></div>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-black text-gray-900">{totalApps}</span>
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">Total Apps</span>
              </div>
            </div>

            {/* Legend & Stats */}
            <div className="flex-grow w-full space-y-4">
              {distributionData.map((item, idx) => (
                <div key={idx} className="group/item cursor-pointer">
                  <div className="flex justify-between items-center mb-1.5">
                    <div className="flex items-center gap-3">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }}></div>
                      <span className="text-sm font-bold text-gray-700 group-hover/item:text-[#D60041] transition-colors">{item.label}</span>
                    </div>
                    <span className="text-sm font-black text-gray-900">{item.percentage} ({item.value})</span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-50 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-1000 delay-300"
                      style={{ width: item.percentage, backgroundColor: item.color }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Quick Insight Card */}
        <div className="bg-gradient-to-br from-[#D60041] to-[#b50037] rounded-[32px] p-8 text-white shadow-lg shadow-pink-200 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-20">
            <Briefcase size={80} />
          </div>
          <div className="relative z-10 h-full flex flex-col">
            <div className="bg-white/20 w-12 h-12 rounded-2xl flex items-center justify-center mb-6">
              <TrendingUp size={24} />
            </div>
            <h4 className="text-xl font-black mb-2">Hiring Insights</h4>
            <p className="text-white/80 text-sm font-medium leading-relaxed mb-8">
              Keep tracking live application submissions across all departments to optimize your HR pipelines dynamically.
            </p>
            <button className="mt-auto w-full bg-white text-[#D60041] py-4 rounded-2xl font-black text-sm flex items-center justify-center gap-2 hover:bg-pink-50 transition-colors">
              Live Feed Active
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApplicationTrends;