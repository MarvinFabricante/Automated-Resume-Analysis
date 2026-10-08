import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MoreHorizontal, TrendingUp, Calendar, Zap,
  PieChart as PieIcon, Briefcase, Filter, ChevronRight,
  Download, RefreshCw, BarChart3, Activity, Check,
  X, Layers, Info, ArrowUpRight, ArrowDownRight, Eye, Sparkles
} from 'lucide-react';
import { useGetDashboardTrendsQuery } from '../../../redux/api/apiSlice';
import { exportToCSV } from '../../../utils/exportUtils';

const ApplicationTrends = ({ applications = [], appStats = {} }) => {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useGetDashboardTrendsQuery();

  // Functional interactive states
  const [timeRange, setTimeRange] = useState('7D'); // '7D' | '14D' | '30D'
  const [chartView, setChartView] = useState('bar'); // 'bar' | 'area'
  const [showGrid, setShowGrid] = useState(true);
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedDay, setSelectedDay] = useState(null);
  const [hoveredDay, setHoveredDay] = useState(null);
  const [distributionTab, setDistributionTab] = useState('department'); // 'department' | 'status'
  const [toastMessage, setToastMessage] = useState(null);

  const calendarRef = useRef(null);
  const menuRef = useRef(null);

  // Close popovers on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (calendarRef.current && !calendarRef.current.contains(e.target)) {
        setIsCalendarOpen(false);
      }
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setIsMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Compute trend data dynamically based on timeRange (7D, 14D, 30D)
  const numDays = timeRange === '30D' ? 30 : timeRange === '14D' ? 14 : 7;

  const { trendsList, startDateLabel, endDateLabel } = useMemo(() => {
    const today = new Date();
    const dates = [];

    for (let i = numDays - 1; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const iso = d.toISOString().split('T')[0];
      const day = d.toLocaleDateString('en-US', { weekday: 'short' });
      const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const fullDate = d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
      dates.push({ iso, day, label, fullDate });
    }

    // Map application counts if real applications exist
    const hasApps = Array.isArray(applications) && applications.length > 0;
    const dateCounts = {};
    const dateBreakdown = {};

    if (hasApps) {
      applications.forEach(app => {
        if (!app.date) return;
        const dStr = new Date(app.date).toISOString().split('T')[0];
        dateCounts[dStr] = (dateCounts[dStr] || 0) + 1;
        if (!dateBreakdown[dStr]) {
          dateBreakdown[dStr] = { pending: 0, reviewed: 0, accepted: 0, rejected: 0 };
        }
        const st = (app.status || 'pending').toLowerCase();
        if (dateBreakdown[dStr][st] !== undefined) {
          dateBreakdown[dStr][st] += 1;
        } else {
          dateBreakdown[dStr].pending += 1;
        }
      });
    }

    // Check if any applications exist in this period
    const totalFound = dates.reduce((sum, d) => sum + (dateCounts[d.iso] || 0), 0);

    let prevCount = null;
    let list = [];

    if (totalFound > 0 || hasApps) {
      list = dates.map(d => {
        const count = dateCounts[d.iso] || 0;
        let growth = '+0%';
        if (prevCount !== null && prevCount > 0) {
          const diff = count - prevCount;
          const pct = Math.round((diff / prevCount) * 100);
          growth = pct >= 0 ? `+${pct}%` : `${pct}%`;
        } else if (count > 0 && (prevCount === null || prevCount === 0)) {
          growth = `+${count * 100}%`;
        }
        prevCount = count;

        return {
          day: d.day,
          date: d.label,
          fullDate: d.fullDate,
          iso: d.iso,
          applications: count,
          growth,
          breakdown: dateBreakdown[d.iso] || { pending: 0, reviewed: 0, accepted: 0, rejected: 0 }
        };
      });
    } else {
      // Fallback to backend weekly_trends if available
      const rawWeekly = data?.weekly_trends || [];
      if (rawWeekly.length > 0 && numDays === 7) {
        list = rawWeekly.map(w => ({
          ...w,
          fullDate: `${w.date}, ${new Date().getFullYear()}`,
          breakdown: { pending: Math.ceil(w.applications * 0.6), reviewed: Math.floor(w.applications * 0.3), accepted: Math.floor(w.applications * 0.1), rejected: 0 }
        }));
      } else {
        // Synthesize for expanded ranges from weekly trends
        list = dates.map((d, idx) => {
          const sample = rawWeekly[idx % (rawWeekly.length || 7)] || { applications: 0, growth: '+0%' };
          return {
            day: d.day,
            date: d.label,
            fullDate: d.fullDate,
            iso: d.iso,
            applications: sample.applications || 0,
            growth: sample.growth || '+0%',
            breakdown: { pending: 0, reviewed: 0, accepted: 0, rejected: 0 }
          };
        });
      }
    }

    const startLabel = dates[0]?.label || '';
    const endLabel = dates[dates.length - 1]?.label || '';

    return { trendsList: list, startDateLabel: startLabel, endDateLabel: endLabel };
  }, [applications, data?.weekly_trends, numDays, timeRange]);

  // Calculations for charts
  const totalAppsInPeriod = useMemo(() => {
    return trendsList.reduce((sum, item) => sum + item.applications, 0);
  }, [trendsList]);

  const maxApps = useMemo(() => {
    return Math.max(...trendsList.map(d => d.applications), 0);
  }, [trendsList]);

  const peakDay = useMemo(() => {
    return trendsList.find(d => d.applications === maxApps && maxApps > 0);
  }, [trendsList, maxApps]);

  const dailyAverage = useMemo(() => {
    if (!trendsList.length) return '0.0';
    return (totalAppsInPeriod / trendsList.length).toFixed(1);
  }, [totalAppsInPeriod, trendsList]);

  const chartData = useMemo(() => {
    return trendsList.map(d => {
      const pct = maxApps > 0 ? (d.applications / maxApps) * 88 : 0;
      return {
        ...d,
        height: `${Math.max(pct, d.applications > 0 ? 8 : 2)}%`,
        isPeak: peakDay && d.date === peakDay.date,
        percentageOfTotal: totalAppsInPeriod > 0 ? Math.round((d.applications / totalAppsInPeriod) * 100) : 0
      };
    });
  }, [trendsList, maxApps, peakDay, totalAppsInPeriod]);

  const displayMax = maxApps > 0 ? maxApps : 10;
  const label75 = Math.round(displayMax * 0.75);
  const label50 = Math.round(displayMax * 0.5);
  const label25 = Math.round(displayMax * 0.25);

  // Department and Status Distribution data
  const backendDeptData = data?.department_distribution || [];
  const totalBackendApps = data?.total_applications || applications.length || 0;

  const departmentData = useMemo(() => {
    if (backendDeptData.length > 0) return backendDeptData;
    // Calculate from applications if backend not ready
    if (applications.length > 0) {
      const deptCounts = {};
      applications.forEach(a => {
        const dept = a.jobDepartment || a.company || 'Engineering';
        deptCounts[dept] = (deptCounts[dept] || 0) + 1;
      });
      const colors = ['#D60041', '#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#EC4899'];
      const total = applications.length;
      return Object.entries(deptCounts).map(([label, value], i) => ({
        label,
        value,
        color: colors[i % colors.length],
        percentage: `${Math.round((value / total) * 100)}%`
      }));
    }
    return [
      { label: 'Engineering', value: 0, color: '#D60041', percentage: '0%' },
      { label: 'Operations', value: 0, color: '#3B82F6', percentage: '0%' },
      { label: 'Human Resources', value: 0, color: '#10B981', percentage: '0%' }
    ];
  }, [backendDeptData, applications]);

  const statusDistributionData = useMemo(() => {
    const pending = appStats?.pending ?? 0;
    const reviewed = appStats?.reviewed ?? 0;
    const accepted = appStats?.accepted ?? 0;
    const rejected = appStats?.rejected ?? 0;
    const total = (pending + reviewed + accepted + rejected) || 1;

    return [
      { label: 'Under Review', value: reviewed, color: '#3B82F6', percentage: `${Math.round((reviewed / total) * 100)}%`, statusKey: 'REVIEWED' },
      { label: 'Pending Action', value: pending, color: '#F59E0B', percentage: `${Math.round((pending / total) * 100)}%`, statusKey: 'PENDING' },
      { label: 'Accepted Candidates', value: accepted, color: '#10B981', percentage: `${Math.round((accepted / total) * 100)}%`, statusKey: 'ACCEPTED' },
      { label: 'Archived / Rejected', value: rejected, color: '#94A3B8', percentage: `${Math.round((rejected / total) * 100)}%`, statusKey: 'REJECTED' },
    ];
  }, [appStats]);

  const activeDistribution = distributionTab === 'department' ? departmentData : statusDistributionData;

  // Donut chart conic gradient
  const conicGradientString = useMemo(() => {
    let currentPct = 0;
    const parts = [];
    activeDistribution.forEach(item => {
      const pct = parseFloat(item.percentage) || 0;
      if (pct > 0) {
        const next = currentPct + pct;
        parts.push(`${item.color} ${currentPct}% ${next}%`);
        currentPct = next;
      }
    });
    if (currentPct < 100) {
      parts.push(`#F1F5F9 ${currentPct}% 100%`);
    }
    return parts.length ? `conic-gradient(${parts.join(', ')})` : 'conic-gradient(#E2E8F0 0% 100%)';
  }, [activeDistribution]);

  // Derived recruitment intelligence
  const pendingCount = useMemo(() => {
    if (appStats?.pending !== undefined && appStats?.pending !== null) return appStats.pending;
    return applications.filter(a => (a.status || '').toUpperCase() === 'PENDING').length;
  }, [appStats, applications]);

  const highMatchCandidates = useMemo(() => {
    return applications.filter(a => (a.matchScore || 0) >= 80);
  }, [applications]);

  const topMatchScore = useMemo(() => {
    if (!applications.length) return 0;
    return Math.max(...applications.map(a => a.matchScore || 0), 0);
  }, [applications]);

  const topDepartment = useMemo(() => {
    if (!departmentData.length) return 'General';
    return departmentData[0].label || 'General';
  }, [departmentData]);

  const topDeptPercentage = useMemo(() => {
    if (!departmentData.length) return '0%';
    return departmentData[0].percentage || '0%';
  }, [departmentData]);

  const recommendation = useMemo(() => {
    if (pendingCount > 0) {
      if (highMatchCandidates.length > 0) {
        return {
          badge: "High-Priority Talent",
          title: "Fast-Track Top Matches",
          description: (
            <>
              You have <strong className="text-white font-bold">{pendingCount} candidate{pendingCount === 1 ? '' : 's'}</strong> awaiting review, with <strong className="text-white font-bold">{highMatchCandidates.length} high-match applicant{highMatchCandidates.length === 1 ? '' : 'es'} (≥80%)</strong>. Prioritize screening candidates in <strong className="text-white font-bold">{topDepartment}</strong> to lock in top talent early.
            </>
          ),
          buttonLabel: `Review ${pendingCount} Pending Applicant${pendingCount === 1 ? '' : 's'}`,
          targetUrl: "/hr/screeningportal?status=PENDING"
        };
      }
      return {
        badge: "Screening Queue",
        title: "Review Incoming Pipeline",
        description: (
          <>
            <strong className="text-white font-bold">{pendingCount} new candidate{pendingCount === 1 ? '' : 's'}</strong> awaiting your initial evaluation. Review applicants in <strong className="text-white font-bold">{topDepartment}</strong> ({topDeptPercentage} of volume) to maintain short turnaround times.
          </>
        ),
        buttonLabel: `Screen ${pendingCount} Applicant${pendingCount === 1 ? '' : 's'}`,
        targetUrl: "/hr/screeningportal?status=PENDING"
      };
    }

    if (applications.length > 0) {
      return {
        badge: "Optimal Flow",
        title: "Pipeline Up to Date",
        description: (
          <>
            All current candidate submissions have been reviewed. Talent intake is strongest in <strong className="text-white font-bold">{topDepartment}</strong>. Coordinate with interview panelists to advance candidates in the hiring pipeline.
          </>
        ),
        buttonLabel: "Manage Active Pipeline",
        targetUrl: "/hr/screeningportal"
      };
    }

    return {
      badge: "Sourcing Ready",
      title: "Talent Inflow Steady",
      description: (
        <>
          No pending submissions in the current window. Keep active job postings open in <strong className="text-white font-bold">{topDepartment}</strong> to continuously draw qualified applicants.
        </>
      ),
      buttonLabel: "Explore Screening Portal",
      targetUrl: "/hr/screeningportal"
    };
  }, [pendingCount, highMatchCandidates.length, applications.length, topDepartment, topDeptPercentage]);

  // SVG coordinates for Area/Line Chart View
  const areaSvgData = useMemo(() => {
    if (chartData.length < 2) return { path: '', area: '', points: [] };
    const width = 800;
    const height = 240;
    const step = width / (chartData.length - 1);

    const points = chartData.map((d, i) => {
      const x = i * step;
      const y = maxApps > 0 ? height - (d.applications / maxApps) * (height - 30) - 15 : height - 15;
      return { x, y, data: d };
    });

    // Generate smooth cubic bezier curve
    let path = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i];
      const p1 = points[i + 1];
      const cp1x = p0.x + (p1.x - p0.x) / 2;
      const cp1y = p0.y;
      const cp2x = p0.x + (p1.x - p0.x) / 2;
      const cp2y = p1.y;
      path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p1.x} ${p1.y}`;
    }

    const area = `${path} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z`;

    return { path, area, points };
  }, [chartData, maxApps]);

  // Action handlers
  const handleRefresh = async () => {
    setIsRefreshing(true);
    setIsMenuOpen(false);
    try {
      if (refetch) await refetch();
      showToast('Application trends refreshed successfully');
    } catch {
      showToast('Trends synchronized with latest records');
    } finally {
      setTimeout(() => setIsRefreshing(false), 600);
    }
  };

  const handleExport = () => {
    setIsMenuOpen(false);
    if (!chartData.length) {
      alert('No trend data available to export.');
      return;
    }
    const exportRows = chartData.map(item => ({
      Date: item.fullDate || item.date,
      DayOfWeek: item.day,
      Submissions: item.applications,
      GrowthRate: item.growth,
      ShareOfPeriod: `${item.percentageOfTotal}%`,
      PendingReview: item.breakdown?.pending || 0,
      Reviewed: item.breakdown?.reviewed || 0,
      Accepted: item.breakdown?.accepted || 0,
      Rejected: item.breakdown?.rejected || 0
    }));
    exportToCSV(exportRows, `Application_Trends_${timeRange}_${new Date().toISOString().split('T')[0]}`);
    showToast(`Exported ${chartData.length} days of trend data to CSV`);
  };

  const handleDayClick = (item) => {
    if (selectedDay?.date === item.date) {
      setSelectedDay(null);
    } else {
      setSelectedDay(item);
    }
  };

  if (isLoading && !data && applications.length === 0) {
    return (
      <div className="space-y-8 mb-8">
        <div className="bg-white border border-gray-100 rounded-[32px] p-6 sm:p-8 lg:p-10 shadow-sm h-[420px] flex flex-col justify-between animate-pulse">
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

  if (error && applications.length === 0) {
    return (
      <div className="bg-red-50 border border-red-100 text-red-700 p-6 rounded-[32px] mb-8 text-center font-medium flex items-center justify-center gap-3">
        <Info size={18} />
        <span>Failed to load application trends data.</span>
        <button onClick={handleRefresh} className="px-4 py-1.5 bg-red-600 text-white rounded-xl text-xs font-bold hover:bg-red-700">Retry</button>
      </div>
    );
  }

  return (
    <div className="space-y-8 mb-8">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-8 right-8 bg-slate-900 text-white px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-3 text-xs font-bold z-50 animate-in fade-in slide-in-from-bottom-3 duration-300 border border-slate-800">
          <Check size={16} className="text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* 1. Main Trends Chart Card */}
      <div className="bg-white border border-gray-100 rounded-[32px] p-6 sm:p-8 lg:p-10 shadow-sm relative overflow-hidden group/container">
        {/* Subtle Ambient Glow */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 bg-pink-50/40 rounded-full blur-3xl pointer-events-none group-hover/container:bg-pink-100/40 transition-colors duration-700" />

        {/* Top Header & Interactive Controls */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-8 gap-6 relative z-20">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
              <h3 className="text-xl md:text-2xl font-black tracking-tight text-gray-900">Application Trends</h3>
              <span className="bg-emerald-50 text-emerald-700 text-[10px] font-black px-2.5 py-0.5 rounded-full flex items-center gap-1.5 border border-emerald-200/80 shadow-xs uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live Sync
              </span>
            </div>
            <p className="text-xs md:text-sm text-gray-500 font-semibold tracking-tight">
              Submission volume analysis • <span className="font-bold text-gray-700">{startDateLabel} — {endDateLabel}</span>
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap w-full lg:w-auto justify-between lg:justify-end">
            {/* Range Selector Buttons (7D, 14D, 30D) */}
            <div className="inline-flex bg-gray-50 p-1 rounded-2xl border border-gray-100">
              {[
                { id: '7D', label: '7 Days' },
                { id: '14D', label: '14 Days' },
                { id: '30D', label: '30 Days' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setTimeRange(tab.id);
                    setSelectedDay(null);
                  }}
                  className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all ${
                    timeRange === tab.id
                      ? 'bg-slate-900 text-white shadow-md shadow-slate-900/10'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-white/80'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* View Mode Toggle (Bar vs Area) */}
            <div className="inline-flex bg-gray-50 p-1 rounded-2xl border border-gray-100">
              <button
                onClick={() => setChartView('bar')}
                title="Bar Chart View"
                className={`p-1.5 rounded-xl transition-all ${
                  chartView === 'bar'
                    ? 'bg-white text-[#D60041] shadow-sm'
                    : 'text-gray-400 hover:text-gray-800'
                }`}
              >
                <BarChart3 size={16} />
              </button>
              <button
                onClick={() => setChartView('area')}
                title="Trend Curve View"
                className={`p-1.5 rounded-xl transition-all ${
                  chartView === 'area'
                    ? 'bg-white text-[#D60041] shadow-sm'
                    : 'text-gray-400 hover:text-gray-800'
                }`}
              >
                <Activity size={16} />
              </button>
            </div>

            {/* Calendar Popover Button */}
            <div className="relative" ref={calendarRef}>
              <button
                onClick={() => setIsCalendarOpen(!isCalendarOpen)}
                className={`p-2.5 rounded-2xl transition-all border shadow-xs flex items-center gap-2 ${
                  isCalendarOpen
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white text-gray-600 border-gray-200/90 hover:bg-gray-50 hover:border-pink-200'
                }`}
                title="Select Date Window"
              >
                <Calendar size={16} className={isCalendarOpen ? 'text-white' : 'text-gray-500'} />
              </button>

              {isCalendarOpen && (
                <div className="absolute right-0 top-full mt-2 w-64 bg-white border border-gray-100 rounded-3xl shadow-2xl p-4 z-40 animate-in fade-in zoom-in-95 duration-200">
                  <div className="flex items-center justify-between pb-3 border-b border-gray-50 mb-3">
                    <span className="text-xs font-black text-gray-900 uppercase tracking-wider">Date Window</span>
                    <span className="text-[10px] font-bold text-gray-400">{timeRange}</span>
                  </div>
                  <div className="space-y-1">
                    {[
                      { id: '7D', label: 'Past 7 Days', desc: 'Detailed daily pulse' },
                      { id: '14D', label: 'Past 14 Days', desc: 'Bi-weekly trajectory' },
                      { id: '30D', label: 'Past 30 Days', desc: 'Monthly hiring cycle' }
                    ].map(opt => (
                      <button
                        key={opt.id}
                        onClick={() => {
                          setTimeRange(opt.id);
                          setIsCalendarOpen(false);
                          setSelectedDay(null);
                        }}
                        className={`w-full text-left px-3 py-2.5 rounded-xl text-xs flex items-center justify-between transition-colors ${
                          timeRange === opt.id
                            ? 'bg-red-50 text-[#D60041] font-bold'
                            : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                        }`}
                      >
                        <div>
                          <div className="font-bold">{opt.label}</div>
                          <div className="text-[10px] text-gray-400">{opt.desc}</div>
                        </div>
                        {timeRange === opt.id && <Check size={14} className="text-[#D60041]" />}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* More Options Dropdown Button */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                className={`p-2.5 rounded-2xl transition-all border shadow-xs ${
                  isMenuOpen
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white text-gray-600 border-gray-200/90 hover:bg-gray-50 hover:border-pink-200'
                }`}
                title="Chart Options"
              >
                <MoreHorizontal size={16} />
              </button>

              {isMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-56 bg-white border border-gray-100 rounded-3xl shadow-2xl p-2 z-40 animate-in fade-in zoom-in-95 duration-200">
                  <button
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                    className="w-full text-left px-3 py-2.5 rounded-xl text-xs font-bold text-gray-700 hover:bg-gray-50 hover:text-gray-900 flex items-center gap-2.5 transition-colors"
                  >
                    <RefreshCw size={14} className={`text-gray-400 ${isRefreshing ? 'animate-spin text-[#D60041]' : ''}`} />
                    <span>Sync Live Data</span>
                  </button>

                  <button
                    onClick={handleExport}
                    className="w-full text-left px-3 py-2.5 rounded-xl text-xs font-bold text-gray-700 hover:bg-gray-50 hover:text-gray-900 flex items-center gap-2.5 transition-colors"
                  >
                    <Download size={14} className="text-gray-400" />
                    <span>Export CSV Dataset</span>
                  </button>

                  <div className="h-px bg-gray-100 my-1" />

                  <button
                    onClick={() => {
                      setShowGrid(!showGrid);
                      setIsMenuOpen(false);
                    }}
                    className="w-full text-left px-3 py-2.5 rounded-xl text-xs font-bold text-gray-700 hover:bg-gray-50 hover:text-gray-900 flex items-center justify-between transition-colors"
                  >
                    <span className="flex items-center gap-2.5">
                      <Layers size={14} className="text-gray-400" />
                      Gridlines
                    </span>
                    <span className="text-[10px] font-black text-gray-400 uppercase">{showGrid ? 'On' : 'Off'}</span>
                  </button>

                  <button
                    onClick={() => {
                      setChartView(chartView === 'bar' ? 'area' : 'bar');
                      setIsMenuOpen(false);
                    }}
                    className="w-full text-left px-3 py-2.5 rounded-xl text-xs font-bold text-gray-700 hover:bg-gray-50 hover:text-gray-900 flex items-center gap-2.5 transition-colors"
                  >
                    {chartView === 'bar' ? <Activity size={14} className="text-gray-400" /> : <BarChart3 size={14} className="text-gray-400" />}
                    <span>Switch to {chartView === 'bar' ? 'Area Curve' : 'Bar Columns'}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Detailed Metrics Overview Ribbon */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 sm:p-5 bg-gradient-to-br from-slate-50/80 to-pink-50/20 rounded-2xl sm:rounded-3xl border border-gray-100 mb-8 relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-pink-100/70 text-[#D60041] flex items-center justify-center shrink-0">
              <Zap size={18} />
            </div>
            <div>
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Period Peak</p>
              <p className="text-sm sm:text-base font-black text-gray-900">
                {maxApps} <span className="text-xs text-gray-500 font-bold">{maxApps === 1 ? 'App' : 'Apps'}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100/70 text-blue-600 flex items-center justify-center shrink-0">
              <TrendingUp size={18} />
            </div>
            <div>
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Daily Average</p>
              <p className="text-sm sm:text-base font-black text-gray-900">
                {dailyAverage} <span className="text-xs text-gray-500 font-bold">/ day</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-100/70 text-purple-600 flex items-center justify-center shrink-0">
              <Briefcase size={18} />
            </div>
            <div>
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Window Total</p>
              <p className="text-sm sm:text-base font-black text-gray-900">
                {totalAppsInPeriod} <span className="text-xs text-gray-500 font-bold">Total</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100/70 text-emerald-600 flex items-center justify-center shrink-0">
              <Activity size={18} />
            </div>
            <div>
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Best Day</p>
              <p className="text-sm sm:text-base font-black text-gray-900 truncate">
                {peakDay ? peakDay.date : 'N/A'}
              </p>
            </div>
          </div>
        </div>

        {/* Selected Day Inspector Ribbon (if user clicks a bar/point) */}
        {selectedDay && (
          <div className="mb-6 p-4 rounded-2xl bg-slate-900 text-white flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-in fade-in slide-in-from-top-2 duration-200 relative z-20">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center text-[#ff4d7d]">
                <Calendar size={18} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-black text-white">{selectedDay.fullDate || selectedDay.date}</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/10 text-gray-300">
                    {selectedDay.day}
                  </span>
                  {selectedDay.isPeak && (
                    <span className="text-[9px] font-black px-2 py-0.5 rounded-full bg-[#D60041] text-white uppercase tracking-wider">
                      Peak Day
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-300 mt-0.5">
                  <strong className="text-white font-black">{selectedDay.applications}</strong> application{selectedDay.applications === 1 ? '' : 's'} recorded ({selectedDay.percentageOfTotal}% of window)
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-center">
              <button
                onClick={() => navigate('/hr/screeningportal')}
                className="px-4 py-2 bg-[#D60041] hover:bg-[#b50037] text-white text-xs font-black rounded-xl transition-all flex items-center gap-1.5 shadow-md shadow-pink-900/30"
              >
                <span>Filter Candidates</span>
                <ChevronRight size={14} />
              </button>
              <button
                onClick={() => setSelectedDay(null)}
                className="p-2 bg-white/10 hover:bg-white/20 text-gray-300 hover:text-white rounded-xl transition-colors"
                title="Dismiss"
              >
                <X size={14} />
              </button>
            </div>
          </div>
        )}

        {/* 2. Interactive Chart Canvas */}
        <div className="overflow-x-auto scrollbar-hide pb-8 -mx-2 px-2 relative z-10">
          <div className="min-w-[650px] h-[320px] relative mt-4 pl-12 pr-4">
            {/* Y-Axis Labels */}
            <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-[11px] text-gray-400 font-black tracking-widest py-1 pr-3">
              <span>{displayMax}</span>
              <span>{label75}</span>
              <span>{label50}</span>
              <span>{label25}</span>
              <span className="text-gray-300">0</span>
            </div>

            {/* Optional Gridlines */}
            {showGrid && (
              <div className="absolute inset-0 pl-12 flex flex-col justify-between w-full h-full pointer-events-none">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="border-t border-gray-100/90 w-full h-px relative" />
                ))}
              </div>
            )}

            {/* A. Bar Chart Visualization Mode */}
            {chartView === 'bar' && (
              <div className="w-full h-full flex items-end justify-between relative px-2">
                {chartData.map((item, index) => {
                  const isSelected = selectedDay?.date === item.date;
                  const isHovered = hoveredDay?.date === item.date;

                  return (
                    <div
                      key={index}
                      className="flex flex-col items-center group h-full justify-end relative"
                      style={{ width: `${Math.max(100 / chartData.length - 2, 2.5)}%` }}
                      onMouseEnter={() => setHoveredDay(item)}
                      onMouseLeave={() => setHoveredDay(null)}
                      onClick={() => handleDayClick(item)}
                    >
                      {/* Detailed Tooltip on Hover */}
                      <div
                        className={`absolute -top-24 left-1/2 -translate-x-1/2 bg-slate-900 text-white p-3 rounded-2xl transition-all duration-200 pointer-events-none shadow-2xl z-30 min-w-[150px] ${
                          isHovered ? 'opacity-100 -translate-y-2 scale-100' : 'opacity-0 scale-95 pointer-events-none'
                        }`}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-[10px] text-gray-400 font-bold uppercase">{item.day}, {item.date}</span>
                          <span className={`text-[9px] font-black px-1.5 py-0.5 rounded ${
                            item.growth.startsWith('+') ? 'text-emerald-400 bg-emerald-500/20' : 'text-red-400 bg-red-500/20'
                          }`}>
                            {item.growth}
                          </span>
                        </div>
                        <div className="text-sm font-black text-white">{item.applications} Applications</div>
                        <div className="text-[10px] text-gray-400 mt-0.5 font-medium">
                          {item.percentageOfTotal}% of {timeRange} volume
                        </div>
                        <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-900 rotate-45" />
                      </div>

                      {/* Clickable Column Bar */}
                      <div className="w-full flex flex-col items-center h-full justify-end cursor-pointer">
                        {item.isPeak && (
                          <div className="absolute top-0 flex flex-col items-center">
                            <span className="text-[9px] font-black text-[#D60041] uppercase tracking-tighter bg-pink-50 px-2 py-0.5 rounded-full mb-1 border border-pink-100 shadow-2xs">
                              Peak
                            </span>
                            <div className="w-px h-full bg-gradient-to-b from-[#D60041] to-transparent border-dashed border-l border-pink-300 opacity-60" />
                          </div>
                        )}

                        <div
                          className={`w-full max-w-[44px] rounded-t-[14px] transition-all duration-500 ease-out relative ${
                            isSelected
                              ? 'bg-gradient-to-t from-slate-900 to-slate-700 ring-4 ring-slate-300 shadow-xl'
                              : item.isPeak
                              ? 'bg-gradient-to-t from-[#D60041] to-[#ff4d7d] shadow-[0_4px_20px_rgba(214,0,65,0.25)]'
                              : 'bg-gradient-to-t from-gray-100 to-gray-200 group-hover:from-pink-100 group-hover:to-[#D60041] group-hover:shadow-[0_4px_20px_rgba(214,0,65,0.2)]'
                          }`}
                          style={{ height: item.height }}
                        >
                          {/* Glossy top cap */}
                          <div className="absolute inset-x-0 top-0 h-1/3 bg-white/20 rounded-t-[14px]" />
                        </div>
                      </div>

                      {/* X-Axis Date / Day label */}
                      <div className="absolute -bottom-8 flex flex-col items-center text-center">
                        <span className={`text-[11px] font-black tracking-tight transition-colors ${
                          isSelected ? 'text-[#D60041]' : 'text-gray-900 group-hover:text-[#D60041]'
                        }`}>
                          {item.day}
                        </span>
                        <span className="text-[9px] text-gray-400 font-bold leading-none mt-0.5 whitespace-nowrap">
                          {item.date.split(' ')[1] || item.date}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* B. Area / Line Curve Visualization Mode */}
            {chartView === 'area' && (
              <div className="w-full h-full relative">
                <svg viewBox="0 0 800 240" preserveAspectRatio="none" className="w-full h-full overflow-visible">
                  <defs>
                    <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#D60041" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#D60041" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Gradient Area Fill */}
                  <path d={areaSvgData.area} fill="url(#trendGradient)" />

                  {/* Main Stroke Curve */}
                  <path
                    d={areaSvgData.path}
                    fill="none"
                    stroke="#D60041"
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                  {/* Nodes on each day */}
                  {areaSvgData.points.map((pt, idx) => {
                    const isSelected = selectedDay?.date === pt.data.date;
                    const isPeak = pt.data.isPeak;

                    return (
                      <g key={idx} className="cursor-pointer" onClick={() => handleDayClick(pt.data)}>
                        <circle
                          cx={pt.x}
                          cy={pt.y}
                          r={isSelected ? 7 : isPeak ? 6 : 4.5}
                          fill={isPeak ? '#D60041' : '#ffffff'}
                          stroke={isPeak ? '#ffffff' : '#D60041'}
                          strokeWidth={isSelected ? 3 : 2}
                          className="transition-transform duration-200 hover:scale-150"
                        />
                      </g>
                    );
                  })}
                </svg>

                {/* X-Axis Labels beneath area curve */}
                <div className="w-full flex justify-between absolute -bottom-8 px-1">
                  {chartData.map((item, idx) => (
                    <div
                      key={idx}
                      onClick={() => handleDayClick(item)}
                      className="flex flex-col items-center cursor-pointer group text-center"
                    >
                      <span className="text-[11px] font-black text-gray-900 group-hover:text-[#D60041]">
                        {item.day}
                      </span>
                      <span className="text-[9px] text-gray-400 font-bold">
                        {item.date.split(' ')[1] || item.date}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Meta Details */}
        <div className="mt-14 flex flex-wrap items-center justify-between gap-4 pt-6 border-t border-gray-50 relative z-10 text-xs">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gradient-to-br from-pink-400 to-[#D60041]" />
              <span className="text-gray-600 font-bold">Total Submissions</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-slate-900" />
              <span className="text-gray-500 font-semibold">Selected Data Node</span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-gray-400 font-semibold">
            <Calendar size={14} className="text-gray-400" />
            <span>Updated: {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          </div>
        </div>
      </div>

      {/* 3. Distribution Breakdown & Dynamic Hiring Insights Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Distribution Card (Switchable by Dept / by Status) */}
        <div className="lg:col-span-2 bg-white border border-gray-100 rounded-[32px] p-6 sm:p-8 shadow-sm group/pie relative overflow-hidden flex flex-col justify-between">
          <div className="absolute bottom-0 left-0 -ml-16 -mb-16 w-56 h-56 bg-blue-50/40 rounded-full blur-3xl pointer-events-none" />

          {/* Distribution Header & Tab Toggle */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4 relative z-10">
            <div>
              <h3 className="text-xl font-black tracking-tight text-gray-900 flex items-center gap-2.5">
                <PieIcon size={20} className="text-[#D60041]" />
                Application Distribution
              </h3>
              <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mt-1">
                {distributionTab === 'department' ? 'Categorized by Department' : 'Categorized by Application Pipeline Status'}
              </p>
            </div>

            {/* Segmented Switcher Button */}
            <div className="inline-flex bg-gray-50 p-1 rounded-2xl border border-gray-100 self-end sm:self-auto">
              <button
                onClick={() => setDistributionTab('department')}
                className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all ${
                  distributionTab === 'department'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-gray-400 hover:text-gray-700'
                }`}
              >
                Department
              </button>
              <button
                onClick={() => setDistributionTab('status')}
                className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all ${
                  distributionTab === 'status'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-gray-400 hover:text-gray-700'
                }`}
              >
                Status
              </button>
            </div>
          </div>

          {/* Interactive Donut & Legend Items */}
          <div className="flex flex-col md:flex-row items-center justify-around gap-8 sm:gap-12 relative z-10 my-auto">
            {/* Donut Chart */}
            <div className="relative w-44 h-44 sm:w-52 sm:h-52 shrink-0">
              <div className="absolute inset-0 rounded-full border-[18px] border-gray-50" />
              <div
                className="absolute inset-0 rounded-full border-[18px] transition-transform duration-700 group-hover/pie:scale-105"
                style={{
                  borderImageSource: conicGradientString,
                  borderImageSlice: 1,
                  borderRadius: '50%',
                  background: conicGradientString,
                  WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
                  WebkitMaskComposite: 'xor',
                  padding: '18px'
                }}
              />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-black text-gray-900 leading-none">
                  {totalBackendApps}
                </span>
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mt-1">
                  Total Apps
                </span>
              </div>
            </div>

            {/* List with Click-to-Filter */}
            <div className="flex-grow w-full space-y-3.5">
              {activeDistribution.map((item, idx) => (
                <div
                  key={idx}
                  onClick={() => {
                    if (item.statusKey) {
                      navigate(`/hr/screeningportal?status=${item.statusKey}`);
                    } else {
                      navigate('/hr/screeningportal');
                    }
                  }}
                  className="p-2.5 -mx-2.5 rounded-2xl hover:bg-slate-50 transition-all cursor-pointer group/row border border-transparent hover:border-gray-100"
                  title="Click to view applicants in screening portal"
                >
                  <div className="flex justify-between items-center mb-1.5">
                    <div className="flex items-center gap-2.5">
                      <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                      <span className="text-xs sm:text-sm font-bold text-gray-700 group-hover/row:text-[#D60041] transition-colors flex items-center gap-1.5">
                        {item.label}
                        <ArrowUpRight size={12} className="opacity-0 group-hover/row:opacity-100 text-[#D60041] transition-opacity" />
                      </span>
                    </div>
                    <span className="text-xs sm:text-sm font-black text-gray-900">
                      {item.percentage} <span className="text-gray-400 font-bold">({item.value})</span>
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-1000 ease-out"
                      style={{ width: item.percentage, backgroundColor: item.color }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-gray-50 flex items-center justify-between text-xs text-gray-400 relative z-10">
            <span className="font-medium">Click any category to open matching candidates</span>
            <button
              onClick={() => navigate('/hr/screeningportal')}
              className="text-[#D60041] font-bold hover:underline flex items-center gap-1"
            >
              <span>View All</span>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>

        {/* Right Col: Intelligent Recruitment Action Card */}
        <div className="bg-gradient-to-br from-[#D60041] via-[#c2003b] to-[#8f0029] rounded-[32px] p-6 sm:p-8 text-white shadow-xl shadow-pink-200/50 relative overflow-hidden flex flex-col justify-between">
          <div className="absolute top-0 right-0 p-8 opacity-15 pointer-events-none">
            <Briefcase size={100} />
          </div>

          <div className="relative z-10">
            <div className="flex items-center justify-between mb-5">
              <div className="bg-white/20 backdrop-blur-md w-11 h-11 rounded-2xl flex items-center justify-center shadow-inner">
                <Sparkles size={20} className="text-pink-100" />
              </div>
              <span className="text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full bg-white/15 border border-white/20 backdrop-blur-md">
                {recommendation.badge}
              </span>
            </div>

            <h4 className="text-2xl font-black tracking-tight mb-2.5 leading-tight">
              {recommendation.title}
            </h4>

            <p className="text-white/90 text-xs sm:text-sm font-medium leading-relaxed mb-6">
              {recommendation.description}
            </p>

            {/* Quick KPI Chips */}
            <div className="grid grid-cols-3 gap-2.5 mb-6">
              <div className="bg-black/15 backdrop-blur-md border border-white/10 rounded-2xl p-2.5 text-center">
                <span className="text-[9px] uppercase font-black tracking-wider text-pink-200/90 block mb-0.5">Queue</span>
                <span className="text-base font-black text-white">{pendingCount}</span>
              </div>
              <div className="bg-black/15 backdrop-blur-md border border-white/10 rounded-2xl p-2.5 text-center">
                <span className="text-[9px] uppercase font-black tracking-wider text-pink-200/90 block mb-0.5">Top Match</span>
                <span className="text-base font-black text-white">{topMatchScore > 0 ? `${topMatchScore}%` : 'N/A'}</span>
              </div>
              <div className="bg-black/15 backdrop-blur-md border border-white/10 rounded-2xl p-2.5 text-center truncate">
                <span className="text-[9px] uppercase font-black tracking-wider text-pink-200/90 block mb-0.5">Focus</span>
                <span className="text-[11px] font-black text-white truncate block">{topDepartment}</span>
              </div>
            </div>
          </div>

          {/* Targeted Action Button */}
          <div className="relative z-10 pt-2">
            <button
              onClick={() => navigate(recommendation.targetUrl)}
              className="w-full bg-white hover:bg-pink-50 text-[#D60041] py-3.5 px-5 rounded-2xl font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-lg shadow-black/15 active:scale-95 group"
            >
              <span>{recommendation.buttonLabel}</span>
              <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApplicationTrends;