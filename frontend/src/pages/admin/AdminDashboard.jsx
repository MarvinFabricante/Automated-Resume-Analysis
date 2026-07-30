import React, { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  ChevronDown, 
  LayoutDashboard, 
  Users, 
  ShieldCheck, 
  Settings, 
  LogOut, 
  Database,
  Download,
  Activity,
  AlertTriangle,
  Clock,
  ArrowUpRight,
  Search,
  Filter
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';

import { useGetHRActivitiesQuery, useGetAdminSystemStatsQuery } from '../../redux/api/apiSlice';
import { Briefcase } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { data: hrActivities = [], isLoading: isActivitiesLoading } = useGetHRActivitiesQuery();
  const { data: stats, isLoading: isStatsLoading } = useGetAdminSystemStatsQuery();

  const SYSTEM_STATS = [
    { 
      label: 'Total Users', 
      value: isStatsLoading ? '...' : stats?.total_users?.toLocaleString(), 
      change: '+12%', 
      icon: Users, 
      color: 'text-[#D10043]', 
      bg: 'bg-red-50' 
    },
    { 
      label: 'HR Officers', 
      value: isStatsLoading ? '...' : stats?.hr_count?.toLocaleString(), 
      change: 'Active', 
      icon: ShieldCheck, 
      color: 'text-emerald-600', 
      bg: 'bg-emerald-50' 
    },
    { 
      label: 'Candidates', 
      value: isStatsLoading ? '...' : stats?.candidate_count?.toLocaleString(), 
      change: 'Registered', 
      icon: Users, 
      color: 'text-blue-600', 
      bg: 'bg-blue-50' 
    },
    { 
      label: 'Total Jobs', 
      value: isStatsLoading ? '...' : stats?.job_count?.toLocaleString(), 
      change: 'Posted', 
      icon: Briefcase, 
      color: 'text-amber-600', 
      bg: 'bg-amber-50' 
    },
  ];

  return (
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
      <Helmet>
        <title>Admin Page - Dashboard</title>
      </Helmet>
      
      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 max-w-[1400px] mx-auto px-10 py-10">
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-gray-900">System Overview</h2>
            <p className="text-sm text-gray-400 font-medium tracking-wide mt-1">
              Monitoring global performance and administrative logs
            </p>
          </div>

          <div className="flex space-x-3 w-full md:w-auto">
            <button className="flex-1 md:flex-none bg-white border border-gray-200 px-5 py-2.5 rounded-xl hover:shadow-sm transition-all text-xs font-bold tracking-tight text-gray-600 flex items-center justify-center">
              Network Live
              <div className="w-2.5 h-2.5 bg-[#D10043] rounded-full ml-3 animate-pulse"></div>
            </button>
            <button className="flex-1 md:flex-none bg-[#D10043] text-white px-5 py-2.5 rounded-xl hover:bg-[#b00038] transition-all text-xs font-bold tracking-tight flex items-center justify-center shadow-lg shadow-red-100">
              <Download className="h-4 w-4 mr-2" />
              Export Reports
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          {SYSTEM_STATS.map((stat, idx) => (
            <div key={idx} className="bg-white border border-gray-100 p-6 rounded-[24px] shadow-sm hover:shadow-md transition-all">
              <div className="flex justify-between items-start mb-4">
                <div className={`p-3 rounded-2xl ${stat.bg}`}>
                  <stat.icon className={`${stat.color} h-6 w-6`} />
                </div>
                <span className={`text-[10px] font-bold px-2 py-1 rounded-lg ${stat.change.includes('+') ? 'bg-emerald-50 text-emerald-600' : 'bg-gray-50 text-gray-400'}`}>
                  {stat.change}
                </span>
              </div>
              <p className="text-sm font-semibold text-gray-400 tracking-wide uppercase text-[10px]">{stat.label}</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</h3>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
          
          <div className="lg:col-span-2 bg-white border border-gray-100 rounded-[32px] p-8 shadow-sm">
            <div className="flex justify-between items-center mb-8">
              <h4 className="text-lg font-bold text-gray-900">Recent HR Activity</h4>
              <div className="flex gap-2">
                <button className="p-2 hover:bg-gray-50 rounded-lg text-gray-400 transition-colors"><Search size={18} /></button>
                <button className="p-2 hover:bg-gray-50 rounded-lg text-gray-400 transition-colors"><Filter size={18} /></button>
              </div>
            </div>
            
            <div className="overflow-x-auto">
              {isActivitiesLoading ? (
                <div className="py-10 flex flex-col items-center">
                   <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#D10043] mb-3"></div>
                   <p className="text-xs text-gray-400 font-bold">Syncing activities...</p>
                </div>
              ) : hrActivities.length === 0 ? (
                <div className="py-10 text-center text-gray-400 text-sm font-medium">No recent HR activity recorded.</div>
              ) : (
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-gray-50 uppercase text-[10px] tracking-[0.1em] text-gray-400 font-bold">
                      <th className="pb-4 font-bold">HR Officer</th>
                      <th className="pb-4 font-bold">Action Performed</th>
                      <th className="pb-4 font-bold text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {hrActivities.map((log) => (
                      <tr key={log.id} className="group hover:bg-gray-50/50 transition-colors">
                        <td className="py-5">
                          <div className="flex items-center gap-3">
                            <div className={`w-9 h-9 rounded-full flex items-center justify-center overflow-hidden border border-gray-100 ${!log.profileImage ? 'bg-red-50 font-bold text-[#D10043] text-xs' : ''}`}>
                              {log.profileImage ? (
                                <img src={log.profileImage} alt={log.user} className="w-full h-full object-cover" />
                              ) : (
                                log.user.charAt(0)
                              )}
                            </div>
                            <div>
                              <p className="text-sm font-bold text-gray-900">{log.user}</p>
                              <p className="text-[11px] text-gray-400 font-medium">{log.role}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-5">
                          <p className="text-sm font-semibold text-gray-700">{log.action}</p>
                          {log.details && (
                            <p className="text-xs text-gray-500 mt-1">{log.details}</p>
                          )}
                          <p className="text-[11px] text-gray-400 flex items-center gap-1 mt-0.5 italic">
                            <Clock size={12} /> {log.time} • {log.target}
                          </p>
                        </td>
                        <td className="py-5 text-right">
                          <span className={`text-[11px] font-bold px-3 py-1 rounded-full ${
                            log.status === 'Success' ? 'bg-emerald-50 text-emerald-600' : 
                            log.status === 'Warning' ? 'bg-amber-50 text-amber-600' : 'bg-red-50 text-[#D10043]'
                          }`}>
                            {log.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <button 
              onClick={() => navigate('/admin/audit')}
              className="w-full mt-6 py-3 text-xs font-bold text-[#D10043] hover:bg-red-50 rounded-xl transition-colors"
            >
              View Full Audit Trail
            </button>
          </div>

          <div className="space-y-6">
            <div className="bg-[#D10043] rounded-[32px] p-8 text-white relative overflow-hidden group shadow-xl shadow-red-100">
              <div className="relative z-10">
                <ShieldCheck className="mb-4 opacity-80" size={32} />
                <h4 className="text-xl font-bold mb-2">Security Status</h4>
                <p className="text-red-50 text-sm leading-relaxed mb-6">
                  All systems operational. Last security scan performed 14 minutes ago.
                </p>
                <button className="bg-white/20 hover:bg-white/30 backdrop-blur-md px-6 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2">
                  Launch Scan <ArrowUpRight size={14} />
                </button>
              </div>
              <div className="absolute -right-8 -bottom-8 w-32 h-32 bg-white/10 rounded-full blur-3xl group-hover:scale-150 transition-transform duration-700"></div>
            </div>

            <div className="bg-white border border-gray-100 rounded-[32px] p-8 shadow-sm">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center">
                  <AlertTriangle className="text-[#D10043]" size={20} />
                </div>
                <h4 className="font-bold text-gray-900">System Warnings</h4>
              </div>
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100">
                  <p className="text-xs font-bold text-gray-800">Storage reaching 85%</p>
                  <p className="text-[11px] text-gray-400 mt-1 uppercase tracking-wider font-bold">Cluster: US-East-1</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100">
                  <p className="text-xs font-bold text-gray-800">Deprecated API calls</p>
                  <p className="text-[11px] text-gray-400 mt-1 uppercase tracking-wider font-bold">3 endpoints flagged</p>
                </div>
              </div>
            </div>
          </div>

        </div>
      </main>
      </div>
    </div>
  );
};

export default AdminDashboard;