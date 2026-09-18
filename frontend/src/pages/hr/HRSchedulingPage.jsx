import React, { useState, useMemo } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Plus,
  RefreshCw,
  Search,
  Filter,
  Video,
  Clock,
  User,
  CheckCircle2,
  AlertCircle,
  CalendarDays,
  ListFilter,
  Check,
  ExternalLink,
  Sparkles,
  Link as LinkIcon
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import InterviewDetailsModal from '../../components/modals/hr/InterviewDetailsModal';
import NewScheduleModal from '../../components/modals/hr/NewScheduleModal';
import {
  useGetCalendarFeedQuery,
  useSyncGoogleCalendarMutation,
  useGetGoogleCalendarStatusQuery
} from '../../redux/api/apiSlice';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const DAYS_OF_WEEK = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const HRSchedulingPage = () => {
  // Calendar state
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState('month'); // 'month' | 'week' | 'day' | 'agenda'
  const [selectedDayForDayView, setSelectedDayForDayView] = useState(new Date());

  // Filter & Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sourceFilter, setSourceFilter] = useState('ALL');

  // Modals state
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [newScheduleModalOpen, setNewScheduleModalOpen] = useState(false);
  const [newScheduleDate, setNewScheduleDate] = useState('');
  const [syncToast, setSyncToast] = useState('');

  // API queries
  const { data: calendarFeed, isLoading, refetch } = useGetCalendarFeedQuery();
  const { data: googleStatus } = useGetGoogleCalendarStatusQuery();
  const [syncGoogleCalendar, { isLoading: isSyncing }] = useSyncGoogleCalendarMutation();

  const interviews = calendarFeed?.interviews || [];
  const googleEvents = calendarFeed?.google_events || [];
  const isGoogleConnected = calendarFeed?.google_connected ?? googleStatus?.connected ?? false;
  const googleAccount = calendarFeed?.google_account || googleStatus?.email;

  // Navigation handlers
  const handlePrev = () => {
    if (viewMode === 'month') {
      setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
    } else if (viewMode === 'week') {
      const prevWeek = new Date(currentDate);
      prevWeek.setDate(currentDate.getDate() - 7);
      setCurrentDate(prevWeek);
    } else if (viewMode === 'day') {
      const prevDay = new Date(selectedDayForDayView);
      prevDay.setDate(selectedDayForDayView.getDate() - 1);
      setSelectedDayForDayView(prevDay);
    }
  };

  const handleNext = () => {
    if (viewMode === 'month') {
      setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
    } else if (viewMode === 'week') {
      const nextWeek = new Date(currentDate);
      nextWeek.setDate(currentDate.getDate() + 7);
      setCurrentDate(nextWeek);
    } else if (viewMode === 'day') {
      const nextDay = new Date(selectedDayForDayView);
      nextDay.setDate(selectedDayForDayView.getDate() + 1);
      setSelectedDayForDayView(nextDay);
    }
  };

  const handleToday = () => {
    const today = new Date();
    setCurrentDate(today);
    setSelectedDayForDayView(today);
  };

  // Trigger manual sync
  const handleManualSync = async () => {
    try {
      await syncGoogleCalendar().unwrap();
      setSyncToast('Calendar synchronized with Google Calendar!');
      setTimeout(() => setSyncToast(''), 4000);
      refetch();
    } catch {
      setSyncToast('Sync completed with local system.');
      setTimeout(() => setSyncToast(''), 4000);
    }
  };

  // Combine and format all events
  const allEvents = useMemo(() => {
    const list = [];

    // System interviews
    interviews.forEach((iv) => {
      const start = new Date(iv.start_time);
      const end = new Date(iv.end_time);
      list.push({
        id: `iv-${iv.id}`,
        rawId: iv.id,
        isGoogleEvent: false,
        title: iv.title || 'Interview Session',
        candidate_name: iv.candidate_name,
        candidate_email: iv.candidate_email,
        candidate_phone: iv.candidate_phone,
        job_title: iv.job_title,
        status: iv.status || 'SCHEDULED',
        start,
        end,
        meeting_link: iv.meeting_link,
        google_event_id: iv.google_event_id,
        description: iv.description,
        type: 'interview'
      });
    });

    // Google Calendar external events
    googleEvents.forEach((ev) => {
      const start = ev.start_datetime ? new Date(ev.start_datetime) : null;
      const end = ev.end_datetime ? new Date(ev.end_datetime) : null;
      if (start && end) {
        list.push({
          id: `g-${ev.id}`,
          rawId: ev.id,
          isGoogleEvent: true,
          title: ev.summary || 'Google Calendar Event',
          candidate_name: 'External Google Event',
          candidate_email: '',
          candidate_phone: '',
          job_title: '',
          status: 'CONFIRMED',
          start,
          end,
          meeting_link: ev.meet_link,
          html_link: ev.html_link,
          google_event_id: ev.id,
          description: ev.description,
          type: 'google'
        });
      }
    });

    return list;
  }, [interviews, googleEvents]);

  // Filter events based on search and filters
  const filteredEvents = useMemo(() => {
    return allEvents.filter((ev) => {
      // Source filter
      if (sourceFilter === 'INTERVIEWS' && ev.isGoogleEvent) return false;
      if (sourceFilter === 'GOOGLE' && !ev.isGoogleEvent) return false;

      // Status filter
      if (statusFilter !== 'ALL') {
        if (ev.isGoogleEvent && statusFilter !== 'SCHEDULED') return false;
        if (!ev.isGoogleEvent && ev.status !== statusFilter) return false;
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const titleMatch = ev.title.toLowerCase().includes(q);
        const nameMatch = (ev.candidate_name || '').toLowerCase().includes(q);
        const jobMatch = (ev.job_title || '').toLowerCase().includes(q);
        if (!titleMatch && !nameMatch && !jobMatch) return false;
      }

      return true;
    });
  }, [allEvents, sourceFilter, statusFilter, searchQuery]);

  // Metrics computation
  const metrics = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const todayEnd = new Date(today);
    todayEnd.setHours(23, 59, 59, 999);

    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - today.getDay());

    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    endOfWeek.setHours(23, 59, 59, 999);

    const todayCount = interviews.filter((i) => {
      const d = new Date(i.start_time);
      return d >= today && d <= todayEnd && i.status !== 'CANCELED';
    }).length;

    const weekCount = interviews.filter((i) => {
      const d = new Date(i.start_time);
      return d >= startOfWeek && d <= endOfWeek && i.status !== 'CANCELED';
    }).length;

    const completedCount = interviews.filter((i) => i.status === 'COMPLETED').length;
    const totalScheduled = interviews.filter((i) => i.status === 'SCHEDULED').length;

    return { todayCount, weekCount, completedCount, totalScheduled };
  }, [interviews]);

  // Month View calendar grid calculation
  const monthGridDays = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const firstDayIndex = new Date(year, month, 1).getDay();
    const daysInCurrentMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrevMonth = new Date(year, month, 0).getDate();

    const days = [];

    // Prev month overflow days
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const d = new Date(year, month - 1, daysInPrevMonth - i);
      days.push({ date: d, isCurrentMonth: false });
    }

    // Current month days
    for (let i = 1; i <= daysInCurrentMonth; i++) {
      const d = new Date(year, month, i);
      days.push({ date: d, isCurrentMonth: true });
    }

    // Next month overflow days
    const remainingSlots = 42 - days.length;
    for (let i = 1; i <= remainingSlots; i++) {
      const d = new Date(year, month + 1, i);
      days.push({ date: d, isCurrentMonth: false });
    }

    return days;
  }, [currentDate]);

  // Week View calculation
  const currentWeekDays = useMemo(() => {
    const curr = new Date(currentDate);
    const day = curr.getDay(); // 0 is Sunday
    const sunday = new Date(curr);
    sunday.setDate(curr.getDate() - day);

    const week = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(sunday);
      d.setDate(sunday.getDate() + i);
      week.push(d);
    }
    return week;
  }, [currentDate]);

  const isSameDay = (d1, d2) => {
    return (
      d1.getFullYear() === d2.getFullYear() &&
      d1.getMonth() === d2.getMonth() &&
      d1.getDate() === d2.getDate()
    );
  };

  const isToday = (d) => isSameDay(d, new Date());

  const getEventsForDay = (dayDate) => {
    return filteredEvents.filter((ev) => isSameDay(ev.start, dayDate));
  };

  const handleEventClick = (ev) => {
    setSelectedEvent(ev);
    setDetailsModalOpen(true);
  };

  const handleOpenNewSchedule = (dayDate) => {
    if (dayDate) {
      const iso = dayDate.toISOString().split('T')[0];
      setNewScheduleDate(iso);
    } else {
      setNewScheduleDate(new Date().toISOString().split('T')[0]);
    }
    setNewScheduleModalOpen(true);
  };

  const formatEventTime = (dateObj) => {
    return dateObj.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
  };

  return (
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
      <Helmet>
        <title>Scheduling Module | Mariwasa ARAS</title>
      </Helmet>
      <Header />

      <div className="flex flex-1">
        <Sidebar />

        <div className="flex-1 min-w-0">
          <main className="w-full max-w-[1600px] mx-auto px-4 sm:px-6 md:px-10 py-6 md:py-8 space-y-6">
            {/* Top Bar Header */}
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 pb-2">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2.5 h-2.5 rounded-full bg-[#D60041] animate-pulse" />
                  <span className="text-[11px] font-black uppercase text-gray-400 tracking-widest">
                    HR Scheduling Module
                  </span>
                </div>
                <h2 className="text-2xl md:text-3xl font-black tracking-tight text-gray-900 leading-tight">
                  Interview Scheduling Calendar
                </h2>
                <p className="text-sm text-gray-500 font-medium mt-0.5">
                  Schedule interviews, prevent double-bookings, and synchronize directly with Google Calendar
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
                {/* Google Calendar Connection Status Badge */}
                <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-white border border-gray-200 text-xs font-semibold shadow-sm">
                  <div className={`w-2.5 h-2.5 rounded-full ${isGoogleConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'}`} />
                  <span className="text-gray-700">
                    {isGoogleConnected ? (
                      <span className="flex items-center gap-1">
                        Google Calendar: <strong className="text-emerald-600 font-bold truncate max-w-[120px]">{googleAccount || 'Connected'}</strong>
                      </span>
                    ) : (
                      <span className="text-gray-500">Google Calendar: Offline</span>
                    )}
                  </span>
                </div>

                {/* Manual Sync Button */}
                <button
                  onClick={handleManualSync}
                  disabled={isSyncing}
                  className="px-3.5 py-2 bg-white hover:bg-pink-50 border border-gray-200 hover:border-pink-200 text-gray-700 hover:text-[#D60041] rounded-xl text-xs font-bold transition-all shadow-sm flex items-center gap-2"
                  title="Synchronize events with Google Calendar"
                >
                  <RefreshCw size={14} className={isSyncing ? 'animate-spin text-[#D60041]' : 'text-gray-400'} />
                  <span>{isSyncing ? 'Syncing...' : 'Sync Calendar'}</span>
                </button>

                {/* New Schedule Button */}
                <button
                  onClick={() => handleOpenNewSchedule()}
                  className="px-4 py-2 bg-[#D60041] hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-[#D60041]/20 flex items-center gap-2"
                >
                  <Plus size={16} />
                  <span>New Schedule</span>
                </button>
              </div>
            </div>

            {/* Sync Toast Notification */}
            {syncToast && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-2.5 text-xs text-emerald-800 font-bold animate-in fade-in slide-in-from-top-2 duration-300">
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                <span>{syncToast}</span>
              </div>
            )}

            {/* KPI Summary Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white border border-gray-100 rounded-3xl p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider">Today's Sessions</span>
                  <div className="w-8 h-8 rounded-xl bg-pink-50 text-[#D60041] flex items-center justify-center">
                    <Clock size={16} />
                  </div>
                </div>
                <p className="text-2xl font-black text-gray-900 mt-2">{metrics.todayCount}</p>
                <p className="text-[11px] text-gray-400 font-semibold mt-0.5">Interviews scheduled today</p>
              </div>

              <div className="bg-white border border-gray-100 rounded-3xl p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider">This Week</span>
                  <div className="w-8 h-8 rounded-xl bg-orange-50 text-orange-600 flex items-center justify-center">
                    <CalendarDays size={16} />
                  </div>
                </div>
                <p className="text-2xl font-black text-gray-900 mt-2">{metrics.weekCount}</p>
                <p className="text-[11px] text-gray-400 font-semibold mt-0.5">Total sessions this week</p>
              </div>

              <div className="bg-white border border-gray-100 rounded-3xl p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider">Active Scheduled</span>
                  <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                    <User size={16} />
                  </div>
                </div>
                <p className="text-2xl font-black text-gray-900 mt-2">{metrics.totalScheduled}</p>
                <p className="text-[11px] text-gray-400 font-semibold mt-0.5">Upcoming candidate interviews</p>
              </div>

              <div className="bg-white border border-gray-100 rounded-3xl p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider">Completed</span>
                  <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                    <CheckCircle2 size={16} />
                  </div>
                </div>
                <p className="text-2xl font-black text-emerald-600 mt-2">{metrics.completedCount}</p>
                <p className="text-[11px] text-gray-400 font-semibold mt-0.5">Completed candidate sessions</p>
              </div>
            </div>

            {/* Calendar Control Toolbar */}
            <div className="bg-white border border-gray-100 rounded-3xl p-5 shadow-sm flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4">
              {/* Date Navigation */}
              <div className="flex items-center gap-3">
                <div className="flex items-center border border-gray-200 rounded-xl overflow-hidden bg-gray-50/50">
                  <button
                    onClick={handlePrev}
                    className="p-2 hover:bg-white text-gray-600 hover:text-gray-900 transition-colors"
                    title="Previous"
                  >
                    <ChevronLeft size={18} />
                  </button>
                  <button
                    onClick={handleToday}
                    className="px-3 py-1 text-xs font-bold text-gray-700 hover:bg-white border-x border-gray-200 transition-colors"
                  >
                    Today
                  </button>
                  <button
                    onClick={handleNext}
                    className="p-2 hover:bg-white text-gray-600 hover:text-gray-900 transition-colors"
                    title="Next"
                  >
                    <ChevronRight size={18} />
                  </button>
                </div>

                <h3 className="text-lg md:text-xl font-black text-gray-900 tracking-tight">
                  {viewMode === 'day'
                    ? selectedDayForDayView.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
                    : `${MONTH_NAMES[currentDate.getMonth()]} ${currentDate.getFullYear()}`}
                </h3>
              </div>

              {/* View Mode Switcher */}
              <div className="flex items-center gap-2">
                <div className="flex bg-gray-100 p-1 rounded-xl border border-gray-200/60 text-xs font-bold text-gray-600">
                  <button
                    onClick={() => setViewMode('month')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${
                      viewMode === 'month' ? 'bg-white text-[#D60041] shadow-sm font-black' : 'hover:text-gray-900'
                    }`}
                  >
                    Month
                  </button>
                  <button
                    onClick={() => setViewMode('week')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${
                      viewMode === 'week' ? 'bg-white text-[#D60041] shadow-sm font-black' : 'hover:text-gray-900'
                    }`}
                  >
                    Week
                  </button>
                  <button
                    onClick={() => setViewMode('day')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${
                      viewMode === 'day' ? 'bg-white text-[#D60041] shadow-sm font-black' : 'hover:text-gray-900'
                    }`}
                  >
                    Day
                  </button>
                  <button
                    onClick={() => setViewMode('agenda')}
                    className={`px-3 py-1.5 rounded-lg transition-all ${
                      viewMode === 'agenda' ? 'bg-white text-[#D60041] shadow-sm font-black' : 'hover:text-gray-900'
                    }`}
                  >
                    Agenda
                  </button>
                </div>
              </div>
            </div>

            {/* Filter & Search Strip */}
            <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
              <div className="relative flex-1 max-w-md">
                <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Filter by candidate, title, or position..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-xl text-xs font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] shadow-sm"
                />
              </div>

              <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0 scrollbar-hide">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-2 bg-white border border-gray-200 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 shadow-sm"
                >
                  <option value="ALL">All Status</option>
                  <option value="SCHEDULED">Scheduled</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="CANCELED">Canceled</option>
                  <option value="NO_SHOW">No Show</option>
                </select>

                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                  className="px-3 py-2 bg-white border border-gray-200 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 shadow-sm"
                >
                  <option value="ALL">All Sources</option>
                  <option value="INTERVIEWS">ARAS Interviews Only</option>
                  <option value="GOOGLE">Google Calendar Only</option>
                </select>
              </div>
            </div>

            {/* Loading Overlay */}
            {isLoading && (
              <div className="p-8 text-center bg-white rounded-3xl border border-gray-100 shadow-sm">
                <div className="w-8 h-8 border-3 border-[#D60041] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-xs font-bold text-gray-500">Loading schedules and syncing Google Calendar...</p>
              </div>
            )}

            {/* VIEW 1: MONTH VIEW */}
            {!isLoading && viewMode === 'month' && (
              <div className="bg-white border border-gray-100 rounded-3xl shadow-sm overflow-hidden">
                {/* Days of Week Header */}
                <div className="grid grid-cols-7 border-b border-gray-100 bg-gray-50/70 text-center">
                  {DAYS_OF_WEEK.map((d, i) => (
                    <div key={i} className="py-3 text-xs font-black uppercase tracking-wider text-gray-500">
                      {d}
                    </div>
                  ))}
                </div>

                {/* 7-column Calendar Grid */}
                <div className="grid grid-cols-7 auto-rows-fr divide-x divide-y divide-gray-100">
                  {monthGridDays.map((dayObj, index) => {
                    const dayEvents = getEventsForDay(dayObj.date);
                    const dayIsToday = isToday(dayObj.date);

                    return (
                      <div
                        key={index}
                        onClick={() => handleOpenNewSchedule(dayObj.date)}
                        className={`min-h-[120px] p-2 flex flex-col justify-between transition-colors cursor-pointer group ${
                          dayObj.isCurrentMonth ? 'bg-white hover:bg-gray-50/50' : 'bg-gray-50/30 text-gray-300'
                        }`}
                      >
                        {/* Day Number Header */}
                        <div className="flex items-center justify-between mb-1.5">
                          <span
                            className={`text-xs font-black w-6 h-6 rounded-full flex items-center justify-center transition-all ${
                              dayIsToday
                                ? 'bg-[#D60041] text-white shadow-sm shadow-[#D60041]/30'
                                : dayObj.isCurrentMonth
                                ? 'text-gray-800'
                                : 'text-gray-300'
                            }`}
                          >
                            {dayObj.date.getDate()}
                          </span>

                          <span className="opacity-0 group-hover:opacity-100 text-[#D60041] text-[10px] font-bold transition-opacity">
                            + Add
                          </span>
                        </div>

                        {/* Events List in Day Cell */}
                        <div className="space-y-1 flex-1 overflow-y-auto max-h-[85px] scrollbar-hide">
                          {dayEvents.slice(0, 3).map((ev) => {
                            const isGoogle = ev.isGoogleEvent;
                            const isCompleted = ev.status === 'COMPLETED';
                            const isCanceled = ev.status === 'CANCELED';

                            let badgeStyle = 'bg-pink-50 text-[#D60041] border border-pink-200/80 hover:border-[#D60041]';
                            if (isGoogle) {
                              badgeStyle = 'bg-blue-50 text-blue-700 border border-blue-200/80 hover:border-blue-400';
                            } else if (isCompleted) {
                              badgeStyle = 'bg-emerald-50 text-emerald-700 border border-emerald-200/80';
                            } else if (isCanceled) {
                              badgeStyle = 'bg-gray-100 text-gray-500 line-through border border-gray-200';
                            }

                            return (
                              <div
                                key={ev.id}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleEventClick(ev);
                                }}
                                className={`px-2 py-1 rounded-lg text-[10px] font-bold truncate flex items-center gap-1 transition-transform hover:scale-101 cursor-pointer ${badgeStyle}`}
                                title={`${ev.title} (${formatEventTime(ev.start)})`}
                              >
                                {isGoogle ? (
                                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                                ) : (
                                  <Video size={10} className="shrink-0" />
                                )}
                                <span className="shrink-0 font-medium opacity-80">{formatEventTime(ev.start)}</span>
                                <span className="truncate">{ev.candidate_name && !isGoogle ? ev.candidate_name : ev.title}</span>
                              </div>
                            );
                          })}

                          {dayEvents.length > 3 && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedDayForDayView(dayObj.date);
                                setViewMode('day');
                              }}
                              className="text-[9px] font-black text-gray-500 hover:text-[#D60041] px-1 block"
                            >
                              +{dayEvents.length - 3} more
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* VIEW 2: WEEK VIEW */}
            {!isLoading && viewMode === 'week' && (
              <div className="bg-white border border-gray-100 rounded-3xl shadow-sm overflow-hidden">
                <div className="grid grid-cols-7 border-b border-gray-100 bg-gray-50/70 text-center divide-x divide-gray-100">
                  {currentWeekDays.map((d, i) => {
                    const isTod = isToday(d);
                    return (
                      <div key={i} className="py-3 px-2">
                        <p className="text-[10px] font-black uppercase tracking-wider text-gray-400">
                          {DAYS_OF_WEEK[d.getDay()]}
                        </p>
                        <p className={`text-base font-black mt-0.5 inline-block px-2.5 py-0.5 rounded-full ${
                          isTod ? 'bg-[#D60041] text-white shadow-sm' : 'text-gray-900'
                        }`}>
                          {d.getDate()}
                        </p>
                      </div>
                    );
                  })}
                </div>

                <div className="grid grid-cols-7 divide-x divide-gray-100 min-h-[480px]">
                  {currentWeekDays.map((dayDate, colIdx) => {
                    const dayEvents = getEventsForDay(dayDate);
                    return (
                      <div
                        key={colIdx}
                        onClick={() => handleOpenNewSchedule(dayDate)}
                        className="p-2 space-y-2 hover:bg-gray-50/40 transition-colors cursor-pointer"
                      >
                        {dayEvents.length === 0 ? (
                          <div className="h-full flex items-center justify-center text-[11px] text-gray-300 font-medium">
                            No sessions
                          </div>
                        ) : (
                          dayEvents.map((ev) => (
                            <div
                              key={ev.id}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEventClick(ev);
                              }}
                              className={`p-2.5 rounded-2xl border text-xs cursor-pointer shadow-sm hover:shadow-md transition-all ${
                                ev.isGoogleEvent
                                  ? 'bg-blue-50/60 border-blue-200 text-blue-900'
                                  : ev.status === 'COMPLETED'
                                  ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900'
                                  : 'bg-white border-pink-200/90 text-gray-900 hover:border-[#D60041]'
                              }`}
                            >
                              <div className="flex items-center justify-between text-[10px] font-bold text-gray-500 mb-1">
                                <span>{formatEventTime(ev.start)}</span>
                                {ev.meeting_link && <Video size={12} className="text-[#D60041]" />}
                              </div>
                              <h5 className="font-bold text-xs truncate">{ev.candidate_name || ev.title}</h5>
                              <p className="text-[11px] text-gray-500 font-medium truncate mt-0.5">
                                {ev.job_title || ev.title}
                              </p>
                            </div>
                          ))
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* VIEW 3: DAY VIEW */}
            {!isLoading && viewMode === 'day' && (
              <div className="bg-white border border-gray-100 rounded-3xl shadow-sm p-6 space-y-4">
                <div className="flex items-center justify-between pb-4 border-b border-gray-100">
                  <div>
                    <h4 className="text-xl font-black text-gray-900">
                      {selectedDayForDayView.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
                    </h4>
                    <p className="text-xs text-gray-500 font-medium mt-0.5">
                      {getEventsForDay(selectedDayForDayView).length} scheduled session(s) today
                    </p>
                  </div>
                  <button
                    onClick={() => handleOpenNewSchedule(selectedDayForDayView)}
                    className="px-4 py-2 bg-[#D60041] hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
                  >
                    <Plus size={14} /> Schedule for this day
                  </button>
                </div>

                {getEventsForDay(selectedDayForDayView).length === 0 ? (
                  <div className="py-16 text-center text-gray-400 space-y-2">
                    <CalendarIcon size={32} className="mx-auto text-gray-300" />
                    <p className="text-sm font-bold text-gray-600">No interviews scheduled for this date</p>
                    <p className="text-xs text-gray-400">Click the button above to set up a new candidate interview session.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {getEventsForDay(selectedDayForDayView).map((ev) => (
                      <div
                        key={ev.id}
                        onClick={() => handleEventClick(ev)}
                        className="p-4 bg-gray-50/60 hover:bg-pink-50/40 border border-gray-200/80 hover:border-[#D60041]/40 rounded-2xl cursor-pointer transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
                      >
                        <div className="flex items-center gap-4 min-w-0">
                          <div className="w-12 h-12 rounded-2xl bg-white border border-gray-200 text-[#D60041] flex flex-col items-center justify-center font-bold shadow-sm shrink-0">
                            <span className="text-xs font-black">{formatEventTime(ev.start)}</span>
                          </div>
                          <div className="truncate">
                            <div className="flex items-center gap-2">
                              <h5 className="text-sm font-bold text-gray-900 truncate">
                                {ev.candidate_name || ev.title}
                              </h5>
                              {ev.isGoogleEvent ? (
                                <span className="bg-blue-100 text-blue-700 text-[9px] font-black px-2 py-0.5 rounded-full uppercase">Google</span>
                              ) : (
                                <span className="bg-pink-100 text-[#D60041] text-[9px] font-black px-2 py-0.5 rounded-full uppercase">{ev.status}</span>
                              )}
                            </div>
                            <p className="text-xs text-gray-500 font-medium truncate mt-0.5">
                              {ev.job_title ? `${ev.job_title} • ` : ''}{ev.title}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                          {ev.meeting_link && (
                            <a
                              href={ev.meeting_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1 shadow-sm"
                            >
                              <Video size={12} /> Join Meet
                            </a>
                          )}
                          <button
                            onClick={() => handleEventClick(ev)}
                            className="px-3 py-1.5 bg-white hover:bg-gray-100 text-gray-700 border border-gray-200 rounded-xl text-xs font-bold transition-colors"
                          >
                            Details
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* VIEW 4: AGENDA / LIST VIEW */}
            {!isLoading && viewMode === 'agenda' && (
              <div className="bg-white border border-gray-100 rounded-3xl shadow-sm p-6 space-y-4">
                <div className="flex items-center justify-between pb-4 border-b border-gray-100">
                  <div>
                    <h4 className="text-xl font-black text-gray-900">Upcoming Schedule Agenda</h4>
                    <p className="text-xs text-gray-500 font-medium mt-0.5">
                      All scheduled candidate interviews and synchronized Google Calendar commitments
                    </p>
                  </div>
                  <span className="text-xs font-bold text-gray-400">
                    {filteredEvents.length} Total Sessions
                  </span>
                </div>

                {filteredEvents.length === 0 ? (
                  <div className="py-16 text-center text-gray-400 space-y-2">
                    <CalendarIcon size={32} className="mx-auto text-gray-300" />
                    <p className="text-sm font-bold text-gray-600">No scheduled sessions match your filters</p>
                    <p className="text-xs text-gray-400">Adjust search keywords or click "New Schedule" to create an interview.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {filteredEvents
                      .sort((a, b) => a.start - b.start)
                      .map((ev) => (
                        <div
                          key={ev.id}
                          onClick={() => handleEventClick(ev)}
                          className="p-4 bg-white hover:bg-pink-50/30 border border-gray-200/80 hover:border-[#D60041]/40 rounded-2xl cursor-pointer transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm"
                        >
                          <div className="flex items-center gap-4 min-w-0">
                            <div className="w-14 h-14 rounded-2xl bg-gray-50 border border-gray-200 text-center flex flex-col items-center justify-center shrink-0">
                              <span className="text-[10px] font-black uppercase text-gray-400">
                                {ev.start.toLocaleString('en-US', { month: 'short' })}
                              </span>
                              <span className="text-lg font-black text-gray-900 leading-none">
                                {ev.start.getDate()}
                              </span>
                            </div>

                            <div className="truncate">
                              <div className="flex items-center gap-2">
                                <h5 className="text-sm font-bold text-gray-900 truncate">
                                  {ev.candidate_name || ev.title}
                                </h5>
                                {ev.isGoogleEvent ? (
                                  <span className="bg-blue-100 text-blue-700 text-[9px] font-black px-2 py-0.5 rounded-full uppercase">Google Calendar</span>
                                ) : (
                                  <span className={`text-[9px] font-black px-2 py-0.5 rounded-full uppercase ${
                                    ev.status === 'COMPLETED'
                                      ? 'bg-emerald-100 text-emerald-700'
                                      : ev.status === 'CANCELED'
                                      ? 'bg-rose-100 text-rose-700'
                                      : 'bg-pink-100 text-[#D60041]'
                                  }`}>
                                    {ev.status}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-gray-500 font-medium truncate mt-0.5">
                                {ev.job_title ? `${ev.job_title} • ` : ''}{ev.title}
                              </p>
                              <p className="text-[11px] text-gray-400 font-semibold mt-1 flex items-center gap-1.5">
                                <Clock size={12} className="text-[#D60041]" />
                                {formatEventTime(ev.start)} – {formatEventTime(ev.end)}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                            {ev.meeting_link && (
                              <a
                                href={ev.meeting_link}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
                              >
                                <Video size={14} /> Join Call
                              </a>
                            )}
                            <button
                              onClick={() => handleEventClick(ev)}
                              className="px-3.5 py-2 bg-gray-50 hover:bg-gray-100 text-gray-700 border border-gray-200 rounded-xl text-xs font-bold transition-colors"
                            >
                              Manage
                            </button>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}
          </main>
        </div>
      </div>

      {/* Details & Reschedule Modal */}
      <InterviewDetailsModal
        isOpen={detailsModalOpen}
        onClose={() => setDetailsModalOpen(false)}
        interview={selectedEvent}
        onStatusChanged={refetch}
      />

      {/* New Schedule Modal */}
      <NewScheduleModal
        isOpen={newScheduleModalOpen}
        onClose={() => setNewScheduleModalOpen(false)}
        initialDate={newScheduleDate}
        onScheduled={refetch}
      />
    </div>
  );
};

export default HRSchedulingPage;
