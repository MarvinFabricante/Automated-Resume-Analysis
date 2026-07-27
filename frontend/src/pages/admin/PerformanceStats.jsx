import React from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  Activity,
  Users,
  Briefcase,
  FileText,
  Clock,
  TrendingUp,
  CheckCircle,
  XCircle,
  Database,
  BarChart3
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { useGetSystemPerformanceQuery } from '../../redux/api/apiSlice';


const PerformanceStats = () => {
  const { data: stats, isLoading } = useGetSystemPerformanceQuery();

  return (
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
      <Helmet>
        <title>Admin Page - Performance & Usage</title>
      </Helmet>
      
      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 max-w-[1400px] mx-auto px-10 py-10">
        
        <div className="mb-10 flex justify-between items-end">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 flex items-center gap-3">
              <Activity className="text-[#D10043]" size={28} /> Performance & Usage
            </h2>
            <p className="text-sm text-gray-400 font-medium tracking-wide mt-1">
              Detailed system statistics, application metrics, and usage analytics.
            </p>
          </div>
          <button className="bg-white border border-gray-200 px-5 py-2.5 rounded-xl hover:shadow-sm transition-all text-xs font-bold tracking-tight text-gray-600 flex items-center justify-center">
            <TrendingUp size={14} className="mr-2" /> Download Report
          </button>
        </div>

        {isLoading ? (
           <div className="py-20 flex flex-col items-center">
             <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#D10043] mb-4"></div>
             <p className="text-sm text-gray-400 font-bold">Aggregating system statistics...</p>
           </div>
        ) : !stats ? (
           <div className="py-10 text-center text-gray-400">Failed to load statistics.</div>
        ) : (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4">
            
            {/* Top KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
              {[
                { title: 'Total Users', val: stats.total_users, sub: `${stats.active_users} active, ${stats.archived_users} archived`, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
                { title: 'Total Jobs', val: stats.total_jobs, sub: `${stats.active_jobs} active, ${stats.inactive_jobs} inactive`, icon: Briefcase, color: 'text-amber-600', bg: 'bg-amber-50' },
                { title: 'Applications', val: stats.total_applications, sub: `${stats.pending_applications} pending review`, icon: FileText, color: 'text-emerald-600', bg: 'bg-emerald-50' },
                { title: 'Avg Match Score', val: `${stats.avg_match_score || 0}%`, sub: 'Across all AI analyses', icon: BarChart3, color: 'text-[#D10043]', bg: 'bg-red-50' },
              ].map((kpi, i) => (
                <div key={i} className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex justify-between items-start mb-4">
                    <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${kpi.bg}`}>
                      <kpi.icon className={kpi.color} size={24} />
                    </div>
                  </div>
                  <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">{kpi.title}</p>
                  <h3 className="text-3xl font-bold text-gray-900 mt-1 mb-2">{kpi.val}</h3>
                  <p className="text-xs text-gray-500 font-medium">{kpi.sub}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left Column */}
              <div className="lg:col-span-2 space-y-8">
                
                {/* Application Funnel */}
                <div className="bg-white border border-gray-100 rounded-[32px] p-8 shadow-sm">
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-bold text-gray-900">Application Pipeline</h3>
                    <div className="bg-gray-50 border border-gray-100 px-3 py-1 rounded-full text-xs font-bold text-gray-500">
                      Conversion Rate: <span className="text-[#D10043]">{stats.conversion_rate}%</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { l: 'Pending', v: stats.pending_applications, c: 'bg-amber-500' },
                      { l: 'Reviewed', v: stats.reviewed_applications, c: 'bg-blue-500' },
                      { l: 'Accepted', v: stats.accepted_applications, c: 'bg-emerald-500' },
                      { l: 'Rejected', v: stats.rejected_applications, c: 'bg-red-500' }
                    ].map(st => (
                      <div key={st.l} className="bg-gray-50 p-4 rounded-2xl border border-gray-100 text-center relative overflow-hidden">
                        <div className={`absolute top-0 left-0 w-full h-1 ${st.c}`}></div>
                        <h4 className="text-2xl font-bold text-gray-900 mt-2">{st.v}</h4>
                        <p className="text-[10px] uppercase font-bold text-gray-400 mt-1">{st.l}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Applications Trend Placeholder (Would normally be a Chart) */}
                <div className="bg-white border border-gray-100 rounded-[32px] p-8 shadow-sm">
                  <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center justify-between">
                    <span>Weekly Applications Trend</span>
                    <span className="text-xs font-semibold bg-gray-100 text-gray-500 px-3 py-1 rounded-full">Last 7 Days</span>
                  </h3>
                  <div className="h-48 flex items-end justify-between gap-2 px-2 pt-8">
                    {stats.applications_trend.map((day, idx) => {
                      const maxCount = Math.max(...stats.applications_trend.map(d => d.count), 1);
                      const height = `${(day.count / maxCount) * 100}%`;
                      return (
                        <div key={idx} className="flex flex-col items-center w-full group">
                          <div className="text-[10px] font-bold text-gray-400 mb-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            {day.count}
                          </div>
                          <div className="w-full bg-[#D10043]/10 hover:bg-[#D10043] rounded-t-lg transition-colors duration-300 relative" style={{ height: height || '5%' }}>
                          </div>
                          <div className="text-[10px] text-gray-400 font-bold mt-3 border-t border-gray-100 pt-2 w-full text-center">
                            {day.date.split(' ')[1]}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

              </div>

              {/* Right Column */}
              <div className="space-y-8">
                
                {/* User Demographics */}
                <div className="bg-white border border-gray-100 rounded-[32px] p-8 shadow-sm">
                  <h3 className="text-lg font-bold text-gray-900 mb-6">User Roles</h3>
                  <div className="space-y-4">
                    {Object.entries(stats.users_by_role).map(([role, count]) => {
                      const pct = Math.round((count / stats.total_users) * 100) || 0;
                      return (
                        <div key={role}>
                          <div className="flex justify-between text-xs font-bold mb-1.5">
                            <span className="text-gray-700">{role}</span>
                            <span className="text-gray-400">{count} ({pct}%)</span>
                          </div>
                          <div className="w-full bg-gray-100 rounded-full h-1.5">
                            <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${pct}%` }}></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Top Jobs */}
                <div className="bg-white border border-gray-100 rounded-[32px] p-8 shadow-sm">
                  <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                    <Briefcase size={18} className="text-[#D10043]" /> Top Performing Jobs
                  </h3>
                  <div className="space-y-4">
                    {stats.top_jobs && stats.top_jobs.length > 0 ? (
                      stats.top_jobs.map((job, idx) => (
                        <div key={idx} className="flex justify-between items-center">
                          <div className="flex items-center gap-3">
                            <span className="w-5 h-5 rounded-full bg-red-50 text-[#D10043] flex items-center justify-center text-[10px] font-bold">{idx + 1}</span>
                            <span className="text-sm font-bold text-gray-700 line-clamp-1">{job.title}</span>
                          </div>
                          <span className="text-xs font-bold text-gray-400 bg-gray-50 px-2 py-1 rounded-lg">{job.count} apps</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-gray-400 text-center py-2">No applications yet</p>
                    )}
                  </div>
                </div>

                {/* System Health */}
                <div className="bg-[#111] rounded-[32px] p-8 text-white relative overflow-hidden group shadow-xl">
                  <div className="relative z-10">
                    <Database className="mb-4 text-emerald-400" size={24} />
                    <h4 className="text-lg font-bold mb-4">System Health</h4>
                    
                    <div className="space-y-4 text-xs font-medium text-gray-300">
                      <div className="flex justify-between border-b border-white/10 pb-2">
                        <span>Data Points Processed</span>
                        <span className="text-emerald-400">~{stats.data_points.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between border-b border-white/10 pb-2">
                        <span>AI Document Analyses</span>
                        <span className="text-emerald-400">{stats.ai_analysis_count.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between border-b border-white/10 pb-2">
                        <span>Total Audit Logs</span>
                        <span className="text-white">{stats.total_audit_logs.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between pb-2">
                        <span>Recent Logins (7d)</span>
                        <span className="text-white">{stats.recent_logins.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                  <div className="absolute -right-10 -bottom-10 w-32 h-32 bg-emerald-500 rounded-full blur-[80px] opacity-20 group-hover:opacity-40 transition-opacity"></div>
                </div>

              </div>
            </div>

          </div>
        )}

        </main>
      </div>
    </div>
  );
};

export default PerformanceStats;
