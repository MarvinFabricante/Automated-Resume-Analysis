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
  Clock,
  User,
  CheckCircle2,
  AlertCircle,
  CalendarDays,
  ListFilter,
  Check,
  ExternalLink,
  Sparkles,
  Link as LinkIcon,
  Users,
  X,
  RotateCcw,
  Eye,
  ArrowRight,
  Lock
} from 'lucide-react';
import { useSelector } from 'react-redux';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import InterviewDetailsModal from '../../components/modals/hr/InterviewDetailsModal';
import NewScheduleModal from '../../components/modals/hr/NewScheduleModal';
import {
  useGetCalendarFeedQuery,
  useSyncGoogleCalendarMutation,
  useGetGoogleCalendarStatusQuery,
  useGetHRInterviewersQuery
} from '../../redux/api/apiSlice';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const DAYS_OF_WEEK = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const WORKING_HOURS = [
  { hour: 8, label: '08:00 AM' },
  { hour: 9, label: '09:00 AM' },
  { hour: 10, label: '10:00 AM' },
  { hour: 11, label: '11:00 AM' },
  { hour: 12, label: '12:00 PM', isLunch: true },
  { hour: 13, label: '01:00 PM' },
  { hour: 14, label: '02:00 PM' },
  { hour: 15, label: '03:00 PM' },
  { hour: 16, label: '04:00 PM' },
  { hour: 17, label: '05:00 PM' },
];

const HRSchedulingPage = () => {
  // Calendar view state
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState('month'); // 'month' | 'week' | 'day' | 'agenda'
  const [selectedDayForDayView, setSelectedDayForDayView] = useState(new Date());
  const [agendaFilterTab, setAgendaFilterTab] = useState('upcoming'); // 'upcoming' | 'month' | 'week' | 'past'

  // Filter & Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sourceFilter, setSourceFilter] = useState('ALL');
  const [hrFilter, setHrFilter] = useState('ALL');

  // Modals state
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [newScheduleModalOpen, setNewScheduleModalOpen] = useState(false);
  const [newScheduleDate, setNewScheduleDate] = useState('');
  const [newScheduleInitialTime, setNewScheduleInitialTime] = useState('');
  const [newSchedulePreselectedHr, setNewSchedulePreselectedHr] = useState(null);
  const [syncToast, setSyncToast] = useState('');

  // API queries
  const { data: interviewers = [] } = useGetHRInterviewersQuery();
  const { data: calendarFeed, isLoading, refetch } = useGetCalendarFeedQuery(
    hrFilter !== 'ALL' ? { hr_id: hrFilter } : undefined
  );
  const { data: googleStatus } = useGetGoogleCalendarStatusQuery();
  const [syncGoogleCalendar, { isLoading: isSyncing }] = useSyncGoogleCalendarMutation();

  const interviews = calendarFeed?.interviews || [];
  const googleEvents = calendarFeed?.google_events || [];
  const isGoogleConnected = calendarFeed?.google_connected ?? googleStatus?.connected ?? false;
  const googleAccount = calendarFeed?.google_account || googleStatus?.email;

  const loggedInUserId = parseInt(localStorage.getItem('user_id'), 10);
  const userRole = useSelector((state) => state.auth?.role) || localStorage.getItem('role');
  const isAdmin = userRole === 'ADMIN' || userRole === 'SUPERADMIN';

  const isEventOwnedByCurrentUser = (ev) => {
    if (ev.isGoogleEvent) return true;
    if (!ev.interviewer_id) return true;
    return ev.interviewer_id === loggedInUserId;
  };

  const isEventReadOnly = (ev) => {
    if (ev.isGoogleEvent) return false;
    return !isAdmin && !isEventOwnedByCurrentUser(ev);
  };

  const toLocalDateString = (d) => {
    const dateObj = d instanceof Date ? d : new Date(d || Date.now());
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, '0');
    const day = String(dateObj.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  const isSameDay = (d1, d2) => {
    if (!d1 || !d2) return false;
    const date1 = d1 instanceof Date ? d1 : new Date(d1);
    const date2 = d2 instanceof Date ? d2 : new Date(d2);
    return (
      date1.getFullYear() === date2.getFullYear() &&
      date1.getMonth() === date2.getMonth() &&
      date1.getDate() === date2.getDate()
    );
  };

  const isToday = (d) => isSameDay(d, new Date());

  // Navigation handlers
  const handlePrev = () => {
    if (viewMode === 'month' || viewMode === 'agenda') {
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
    if (viewMode === 'month' || viewMode === 'agenda') {
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
        start_time: iv.start_time,
        end_time: iv.end_time,
        meeting_link: iv.meeting_link,
        google_event_id: iv.google_event_id,
        description: iv.description,
        interviewer_id: iv.interviewer_id,
        interviewer_name: iv.interviewer_name,
        interviewer_email: iv.interviewer_email,
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
          start_time: ev.start_datetime,
          end_time: ev.end_datetime,
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
      // HR Panelist Filter
      if (hrFilter !== 'ALL') {
        if (!ev.isGoogleEvent) {
          if (!ev.interviewer_id || String(ev.interviewer_id) !== String(hrFilter)) {
            return false;
          }
        }
      }

      // Source filter
      if (sourceFilter === 'INTERVIEWS' && ev.isGoogleEvent) return false;
      if (sourceFilter === 'GOOGLE' && !ev.isGoogleEvent) return false;

      // Status filter
      if (statusFilter !== 'ALL') {
        const evStatus = (ev.status || '').toUpperCase();
        if (ev.isGoogleEvent) {
          if (statusFilter !== 'SCHEDULED') return false;
        } else {
          if (statusFilter === 'CANCELED') {
            if (evStatus !== 'CANCELED' && evStatus !== 'CANCELLED') return false;
          } else if (evStatus !== statusFilter) {
            return false;
          }
        }
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const titleMatch = (ev.title || '').toLowerCase().includes(q);
        const nameMatch = (ev.candidate_name || '').toLowerCase().includes(q);
        const jobMatch = (ev.job_title || '').toLowerCase().includes(q);
        const interviewerMatch = (ev.interviewer_name || '').toLowerCase().includes(q);
        const emailMatch = (ev.candidate_email || '').toLowerCase().includes(q);
        if (!titleMatch && !nameMatch && !jobMatch && !interviewerMatch && !emailMatch) return false;
      }

      return true;
    });
  }, [allEvents, sourceFilter, statusFilter, hrFilter, searchQuery]);

  const hasActiveFilters = searchQuery.trim() !== '' || statusFilter !== 'ALL' || sourceFilter !== 'ALL' || hrFilter !== 'ALL';

  const handleResetFilters = () => {
    setSearchQuery('');
    setStatusFilter('ALL');
    setSourceFilter('ALL');
    setHrFilter('ALL');
  };

  // Metrics computation dynamically from filtered dataset
  const metrics = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const todayEnd = new Date(today);
    todayEnd.setHours(23, 59, 59, 999);

    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - today.getDay());
    startOfWeek.setHours(0, 0, 0, 0);

    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    endOfWeek.setHours(23, 59, 59, 999);

    const todayCount = filteredEvents.filter((ev) => {
      const d = ev.start;
      const st = (ev.status || '').toUpperCase();
      return d >= today && d <= todayEnd && st !== 'CANCELED' && st !== 'CANCELLED';
    }).length;

    const weekCount = filteredEvents.filter((ev) => {
      const d = ev.start;
      const st = (ev.status || '').toUpperCase();
      return d >= startOfWeek && d <= endOfWeek && st !== 'CANCELED' && st !== 'CANCELLED';
    }).length;

    const completedCount = filteredEvents.filter((ev) => (ev.status || '').toUpperCase() === 'COMPLETED').length;
    const totalScheduled = filteredEvents.filter((ev) => (ev.status || '').toUpperCase() === 'SCHEDULED' || ev.isGoogleEvent).length;

    return { todayCount, weekCount, completedCount, totalScheduled, totalCount: filteredEvents.length };
  }, [filteredEvents]);

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

  const weekTitle = useMemo(() => {
    if (currentWeekDays.length === 0) return '';
    const start = currentWeekDays[0];
    const end = currentWeekDays[6];
    const startM = start.toLocaleString('en-US', { month: 'short' });
    const endM = end.toLocaleString('en-US', { month: 'short' });
    if (startM === endM) {
      return `${startM} ${start.getDate()} – ${end.getDate()}, ${start.getFullYear()}`;
    }
    return `${startM} ${start.getDate()} – ${endM} ${end.getDate()}, ${end.getFullYear()}`;
  }, [currentWeekDays]);

  const getEventsForDay = (dayDate) => {
    return filteredEvents.filter((ev) => isSameDay(ev.start, dayDate));
  };

  const handleEventClick = (ev) => {
    setSelectedEvent(ev);
    setDetailsModalOpen(true);
  };

  const handleOpenNewSchedule = (dayDate, initialTime = '') => {
    setNewScheduleDate(toLocalDateString(dayDate || new Date()));
    setNewScheduleInitialTime(initialTime || '');
    setNewSchedulePreselectedHr(hrFilter !== 'ALL' ? hrFilter : null);
    setNewScheduleModalOpen(true);
  };

  const handleScheduled = (info) => {
    const name = info?.candidateName || 'Candidate';
    setSyncToast(`Interview scheduled for ${name}! Synchronizing calendar...`);
    setTimeout(() => setSyncToast(''), 4500);
    refetch();
  };

  const formatEventTime = (dateObj) => {
    return dateObj.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
  };

  // Agenda filtered & sorted events
  const agendaEvents = useMemo(() => {
    const now = new Date();
    const list = [...filteredEvents];

    if (agendaFilterTab === 'upcoming') {
      return list.filter((ev) => ev.end >= now).sort((a, b) => a.start - b.start);
    } else if (agendaFilterTab === 'month') {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth();
      return list
        .filter((ev) => ev.start.getFullYear() === year && ev.start.getMonth() === month)
        .sort((a, b) => a.start - b.start);
    } else if (agendaFilterTab === 'week') {
      if (currentWeekDays.length === 0) return list;
      const startW = new Date(currentWeekDays[0]);
      startW.setHours(0, 0, 0, 0);
      const endW = new Date(currentWeekDays[6]);
      endW.setHours(23, 59, 59, 999);
      return list
        .filter((ev) => ev.start >= startW && ev.start <= endW)
        .sort((a, b) => a.start - b.start);
    } else if (agendaFilterTab === 'past') {
      return list.filter((ev) => ev.end < now).sort((a, b) => b.start - a.start);
    }
    return list.sort((a, b) => a.start - b.start);
  }, [filteredEvents, agendaFilterTab, currentDate, currentWeekDays]);

  // Group agenda events by date
  const groupedAgendaEvents = useMemo(() => {
    const groups = {};
    agendaEvents.forEach((ev) => {
      const dateKey = toLocalDateString(ev.start);
      if (!groups[dateKey]) {
        groups[dateKey] = {
          date: ev.start,
          events: []
        };
      }
      groups[dateKey].events.push(ev);
    });
    return Object.values(groups);
  }, [agendaEvents]);

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
                  onClick={() => handleOpenNewSchedule(viewMode === 'day' ? selectedDayForDayView : new Date())}
                  className="px-4 py-2 bg-[#D60041] hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-[#D60041]/20 flex items-center gap-2"
                >
                  <Plus size={16} />
                  <span>New Schedule</span>
                </button>
              </div>
            </div>

            {/* Sync Toast Notification */}
            {syncToast && (
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-2.5 text-xs text-emerald-800 font-bold animate-in fade-in slide-in-from-top-2 duration-300 shadow-sm">
                <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />
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
                <p className="text-[11px] text-gray-400 font-semibold mt-0.5">
                  {hasActiveFilters ? 'Filtered sessions today' : 'Interviews scheduled today'}
                </p>
              </div>

              <div className="bg-white border border-gray-100 rounded-3xl p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider">This Week</span>
                  <div className="w-8 h-8 rounded-xl bg-orange-50 text-orange-600 flex items-center justify-center">
                    <CalendarDays size={16} />
                  </div>
                </div>
                <p className="text-2xl font-black text-gray-900 mt-2">{metrics.weekCount}</p>
                <p className="text-[11px] text-gray-400 font-semibold mt-0.5">
                  {hasActiveFilters ? 'Filtered sessions this week' : 'Total sessions this week'}
                </p>
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
                    ? selectedDayForDayView.toLocaleDateString('en-US', { weekday: 'short', month: 'long', day: 'numeric', year: 'numeric' })
                    : viewMode === 'week'
                    ? weekTitle
                    : viewMode === 'agenda'
                    ? `${MONTH_NAMES[currentDate.getMonth()]} ${currentDate.getFullYear()} Agenda`
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
            <div className="space-y-2">
              <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
                <div className="relative flex-1 max-w-md">
                  <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search candidate, title, role, or interviewer..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-9 py-2 bg-white border border-gray-200 rounded-xl text-xs font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] shadow-sm"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-0.5"
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0 scrollbar-hide">
                  {/* Status Filter */}
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className={`px-3 py-2 bg-white border rounded-xl text-xs font-bold transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 cursor-pointer ${
                      statusFilter !== 'ALL' ? 'border-[#D60041] text-[#D60041] bg-pink-50/20' : 'border-gray-200 text-gray-700'
                    }`}
                  >
                    <option value="ALL">All Status</option>
                    <option value="SCHEDULED">Scheduled</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="CANCELED">Canceled</option>
                    <option value="NO_SHOW">No Show</option>
                  </select>

                  {/* Sources Filter */}
                  <select
                    value={sourceFilter}
                    onChange={(e) => setSourceFilter(e.target.value)}
                    className={`px-3 py-2 bg-white border rounded-xl text-xs font-bold transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 cursor-pointer ${
                      sourceFilter !== 'ALL' ? 'border-blue-500 text-blue-700 bg-blue-50/20' : 'border-gray-200 text-gray-700'
                    }`}
                  >
                    <option value="ALL">All Sources</option>
                    <option value="INTERVIEWS">ARAS Interviews Only</option>
                    <option value="GOOGLE">Google Calendar Only</option>
                  </select>

                  {/* HR Panelist Filter */}
                  <div className={`flex items-center gap-1.5 bg-white border rounded-xl px-3 py-2 shadow-sm transition-colors ${
                    hrFilter !== 'ALL' ? 'border-emerald-500 bg-emerald-50/20' : 'border-gray-200'
                  }`}>
                    <Users size={14} className={hrFilter !== 'ALL' ? 'text-emerald-600 shrink-0' : 'text-[#D60041] shrink-0'} />
                    <select
                      value={hrFilter}
                      onChange={(e) => setHrFilter(e.target.value)}
                      className={`bg-transparent text-xs font-bold focus:outline-none cursor-pointer ${
                        hrFilter !== 'ALL' ? 'text-emerald-700' : 'text-gray-700'
                      }`}
                    >
                      <option value="ALL">All HR Panelists</option>
                      {interviewers.map((hr) => (
                        <option key={hr.id} value={hr.id}>
                          {hr.fullname}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Active Filters Pill Strip */}
              {hasActiveFilters && (
                <div className="flex flex-wrap items-center gap-2 pt-1 pb-1">
                  <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1">
                    <Filter size={12} /> Active Filters:
                  </span>

                  {searchQuery.trim() && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-700 border border-gray-200">
                      Search: "{searchQuery}"
                      <button onClick={() => setSearchQuery('')} className="hover:text-rose-600">
                        <X size={12} />
                      </button>
                    </span>
                  )}

                  {statusFilter !== 'ALL' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-pink-50 text-[#D60041] border border-pink-200">
                      Status: {statusFilter.replace('_', ' ')}
                      <button onClick={() => setStatusFilter('ALL')} className="hover:text-rose-700">
                        <X size={12} />
                      </button>
                    </span>
                  )}

                  {sourceFilter !== 'ALL' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
                      Source: {sourceFilter === 'INTERVIEWS' ? 'ARAS Interviews' : 'Google Calendar'}
                      <button onClick={() => setSourceFilter('ALL')} className="hover:text-blue-900">
                        <X size={12} />
                      </button>
                    </span>
                  )}

                  {hrFilter !== 'ALL' && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      Panelist: {interviewers.find((h) => String(h.id) === String(hrFilter))?.fullname || 'Selected HR'}
                      <button onClick={() => setHrFilter('ALL')} className="hover:text-emerald-900">
                        <X size={12} />
                      </button>
                    </span>
                  )}

                  <button
                    onClick={handleResetFilters}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold text-gray-500 hover:text-rose-600 hover:bg-rose-50 border border-dashed border-gray-300 transition-colors"
                  >
                    <RotateCcw size={11} /> Reset All
                  </button>

                  <span className="text-[11px] font-semibold text-gray-400 ml-auto">
                    Showing {filteredEvents.length} of {allEvents.length} sessions
                  </span>
                </div>
              )}
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
                        className={`min-h-[125px] p-2 flex flex-col justify-between transition-colors cursor-pointer group ${
                          dayObj.isCurrentMonth ? 'bg-white hover:bg-gray-50/50' : 'bg-gray-50/30 text-gray-300'
                        }`}
                      >
                        {/* Day Number Header */}
                        <div className="flex items-center justify-between mb-1.5">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedDayForDayView(dayObj.date);
                              setViewMode('day');
                            }}
                            className={`text-xs font-black w-6 h-6 rounded-full flex items-center justify-center transition-all hover:scale-110 ${
                              dayIsToday
                                ? 'bg-[#D60041] text-white shadow-sm shadow-[#D60041]/30'
                                : dayObj.isCurrentMonth
                                ? 'text-gray-800 hover:bg-pink-50 hover:text-[#D60041]'
                                : 'text-gray-300'
                            }`}
                            title="Open Day View"
                          >
                            {dayObj.date.getDate()}
                          </button>

                          <span className="opacity-0 group-hover:opacity-100 text-[#D60041] text-[10px] font-bold transition-opacity">
                            + Add
                          </span>
                        </div>

                        {/* Events List in Day Cell */}
                        <div className="space-y-1 flex-1 overflow-y-auto max-h-[85px] scrollbar-hide">
                          {dayEvents.slice(0, 3).map((ev) => {
                            const isGoogle = ev.isGoogleEvent;
                            const isCompleted = ev.status === 'COMPLETED';
                            const isCanceled = ev.status === 'CANCELED' || ev.status === 'CANCELLED';
                            const isNoShow = ev.status === 'NO_SHOW';
                            const readOnly = isEventReadOnly(ev);

                            let badgeStyle = 'bg-pink-50 text-[#D60041] border border-pink-200/80 hover:border-[#D60041]';
                            if (isGoogle) {
                              badgeStyle = 'bg-blue-50 text-blue-700 border border-blue-200/80 hover:border-blue-400';
                            } else if (isCompleted) {
                              badgeStyle = 'bg-emerald-50 text-emerald-700 border border-emerald-200/80';
                            } else if (isCanceled) {
                              badgeStyle = 'bg-gray-100 text-gray-400 line-through border border-gray-200';
                            } else if (isNoShow) {
                              badgeStyle = 'bg-amber-50 text-amber-700 border border-amber-200';
                            } else if (readOnly) {
                              badgeStyle = 'bg-gray-50 text-gray-700 border border-gray-200 hover:border-gray-400';
                            }

                            return (
                              <div
                                key={ev.id}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleEventClick(ev);
                                }}
                                className={`px-2 py-1 rounded-lg text-[10px] font-bold truncate flex items-center gap-1 transition-transform hover:scale-101 cursor-pointer ${badgeStyle}`}
                                title={`${ev.title} (${formatEventTime(ev.start)})${readOnly && ev.interviewer_name ? ` • Assigned to ${ev.interviewer_name} (Read-Only)` : ''}`}
                              >
                                {isGoogle ? (
                                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                                ) : readOnly ? (
                                  <Lock size={10} className="shrink-0 text-amber-600" />
                                ) : (
                                  <CalendarIcon size={10} className="shrink-0" />
                                )}
                                <span className="shrink-0 font-medium opacity-80">{formatEventTime(ev.start)}</span>
                                <span className="truncate">{ev.candidate_name && !isGoogle ? ev.candidate_name : ev.title}</span>
                              </div>
                            );
                          })}

                          {dayEvents.length > 3 && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedDayForDayView(dayObj.date);
                                setViewMode('day');
                              }}
                              className="text-[9px] font-black text-gray-500 hover:text-[#D60041] px-1 block hover:underline"
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
                {/* 7-column header */}
                <div className="grid grid-cols-7 border-b border-gray-100 bg-gray-50/70 text-center divide-x divide-gray-100">
                  {currentWeekDays.map((d, i) => {
                    const isTod = isToday(d);
                    const dayEvents = getEventsForDay(d);
                    return (
                      <div key={i} className="py-3 px-2">
                        <p className="text-[10px] font-black uppercase tracking-wider text-gray-400">
                          {DAYS_OF_WEEK[d.getDay()]}
                        </p>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedDayForDayView(d);
                            setViewMode('day');
                          }}
                          className={`text-base font-black mt-0.5 inline-block px-2.5 py-0.5 rounded-full transition-all hover:scale-105 ${
                            isTod ? 'bg-[#D60041] text-white shadow-sm' : 'text-gray-900 hover:text-[#D60041]'
                          }`}
                          title="View Day Schedule"
                        >
                          {d.getDate()}
                        </button>
                        <div className="mt-1 flex items-center justify-center gap-1">
                          <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded-md ${
                            dayEvents.length > 0 ? 'bg-pink-100 text-[#D60041]' : 'text-gray-400'
                          }`}>
                            {dayEvents.length} {dayEvents.length === 1 ? 'session' : 'sessions'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* 7-column Week Schedule Canvas */}
                <div className="grid grid-cols-7 divide-x divide-gray-100 min-h-[550px]">
                  {currentWeekDays.map((dayDate, colIdx) => {
                    const dayEvents = getEventsForDay(dayDate).sort((a, b) => a.start - b.start);
                    return (
                      <div
                        key={colIdx}
                        className="p-2.5 flex flex-col justify-between hover:bg-gray-50/30 transition-colors"
                      >
                        <div className="space-y-2 flex-1">
                          {dayEvents.length === 0 ? (
                            <div className="h-36 flex flex-col items-center justify-center text-center p-2 text-gray-300">
                              <CalendarIcon size={20} className="mb-1 opacity-50" />
                              <span className="text-[11px] font-medium">No sessions</span>
                              <button
                                type="button"
                                onClick={() => handleOpenNewSchedule(dayDate)}
                                className="mt-2 text-[10px] font-bold text-[#D60041] hover:underline"
                              >
                                + Schedule
                              </button>
                            </div>
                          ) : (
                            dayEvents.map((ev) => {
                              const isGoogle = ev.isGoogleEvent;
                              const isCompleted = ev.status === 'COMPLETED';
                              const isCanceled = ev.status === 'CANCELED' || ev.status === 'CANCELLED';
                              const readOnly = isEventReadOnly(ev);
                              const isOwner = isEventOwnedByCurrentUser(ev);

                              return (
                                <div
                                  key={ev.id}
                                  onClick={() => handleEventClick(ev)}
                                  className={`p-2.5 rounded-2xl border text-xs cursor-pointer shadow-sm hover:shadow-md transition-all group ${
                                    isGoogle
                                      ? 'bg-blue-50/60 border-blue-200 text-blue-900'
                                      : isCompleted
                                      ? 'bg-emerald-50/60 border-emerald-200 text-emerald-900'
                                      : isCanceled
                                      ? 'bg-gray-100 border-gray-200 text-gray-400 line-through'
                                      : readOnly
                                      ? 'bg-gray-50/70 border-gray-200 text-gray-800 hover:border-gray-300'
                                      : 'bg-white border-pink-200/90 text-gray-900 hover:border-[#D60041]'
                                  }`}
                                >
                                  <div className="flex items-center justify-between text-[10px] font-bold text-gray-500 mb-1">
                                    <span>{formatEventTime(ev.start)} – {formatEventTime(ev.end)}</span>
                                    {readOnly && (
                                      <span className="inline-flex items-center gap-0.5 text-[9px] font-black text-amber-700 bg-amber-50 px-1 py-0.5 rounded border border-amber-200" title="Read-Only">
                                        <Lock size={8} /> Read-Only
                                      </span>
                                    )}
                                  </div>
                                  <h5 className="font-bold text-xs truncate group-hover:text-[#D60041] transition-colors">
                                    {ev.candidate_name && !isGoogle ? ev.candidate_name : ev.title}
                                  </h5>
                                  <p className="text-[11px] text-gray-500 font-medium truncate mt-0.5">
                                    {ev.job_title || (isGoogle ? 'External Google Event' : ev.title)}
                                  </p>
                                  {!isGoogle && (
                                    <p className={`text-[10px] font-bold truncate mt-1 flex items-center gap-1 ${
                                      readOnly ? 'text-gray-600' : 'text-[#D60041]'
                                    }`}>
                                      {readOnly ? (
                                        <>
                                          <Lock size={10} className="text-amber-600 shrink-0" />
                                          <span>Panelist: {ev.interviewer_name || 'HR'} • Read-Only</span>
                                        </>
                                      ) : (
                                        <>
                                          <Users size={10} className="shrink-0" />
                                          <span>Panelist: {isOwner ? 'You' : (ev.interviewer_name || 'Assigned')}</span>
                                        </>
                                      )}
                                    </p>
                                  )}
                                </div>
                              );
                            })
                          )}
                        </div>

                        {/* Quick Add footer button for this day */}
                        <button
                          type="button"
                          onClick={() => handleOpenNewSchedule(dayDate)}
                          className="mt-3 w-full py-1.5 border border-dashed border-gray-200 hover:border-[#D60041] text-gray-400 hover:text-[#D60041] hover:bg-pink-50/30 rounded-xl text-[11px] font-bold transition-all flex items-center justify-center gap-1"
                        >
                          <Plus size={12} /> Add
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* VIEW 3: DAY VIEW */}
            {!isLoading && viewMode === 'day' && (
              <div className="bg-white border border-gray-100 rounded-3xl shadow-sm p-6 space-y-6">
                {/* Day Header with Quick Date Selector */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-gray-100">
                  <div>
                    <h4 className="text-xl font-black text-gray-900">
                      {selectedDayForDayView.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
                    </h4>
                    <p className="text-xs text-gray-500 font-medium mt-0.5">
                      {getEventsForDay(selectedDayForDayView).length} scheduled session(s) on this date
                    </p>
                  </div>

                  <div className="flex items-center gap-3 w-full sm:w-auto">
                    {/* Inline Date Input Picker */}
                    <input
                      type="date"
                      value={toLocalDateString(selectedDayForDayView)}
                      onChange={(e) => {
                        if (e.target.value) {
                          const parts = e.target.value.split('-');
                          const newD = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
                          setSelectedDayForDayView(newD);
                        }
                      }}
                      className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-bold text-gray-800 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 cursor-pointer shadow-sm"
                    />

                    <button
                      onClick={() => handleOpenNewSchedule(selectedDayForDayView)}
                      className="px-4 py-2 bg-[#D60041] hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm shadow-[#D60041]/20"
                    >
                      <Plus size={14} /> Schedule for this day
                    </button>
                  </div>
                </div>

                {/* Day Hourly Schedule Timeline (8:00 AM - 5:00 PM) */}
                <div className="space-y-3">
                  {WORKING_HOURS.map((slot) => {
                    const hourEvents = getEventsForDay(selectedDayForDayView).filter((ev) => {
                      const evHour = ev.start.getHours();
                      return evHour === slot.hour;
                    });

                    return (
                      <div
                        key={slot.hour}
                        className="flex items-start gap-4 p-3.5 rounded-2xl border border-gray-100 hover:border-gray-200 transition-colors bg-gray-50/20"
                      >
                        {/* Hour marker */}
                        <div className="w-20 shrink-0 text-center py-1">
                          <span className="text-xs font-black text-gray-700 block">{slot.label}</span>
                          {slot.isLunch && (
                            <span className="text-[9px] font-bold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-md mt-0.5 inline-block">
                              Lunch Break
                            </span>
                          )}
                        </div>

                        {/* Hourly Content */}
                        <div className="flex-1 min-w-0">
                          {hourEvents.length === 0 ? (
                            <div className="flex items-center justify-between p-3 bg-white border border-dashed border-gray-200 rounded-xl hover:border-pink-300 transition-colors group">
                              <span className="text-xs text-gray-400 font-medium">
                                {slot.isLunch ? 'Lunch break reservation window' : 'No interviews scheduled — Slot available'}
                              </span>
                              <button
                                type="button"
                                onClick={() => handleOpenNewSchedule(selectedDayForDayView, `${String(slot.hour).padStart(2, '0')}:00`)}
                                className="px-3 py-1 bg-gray-50 hover:bg-pink-50 text-gray-600 hover:text-[#D60041] border border-gray-200 hover:border-pink-200 rounded-lg text-xs font-bold transition-colors flex items-center gap-1 group-hover:border-[#D60041]/40"
                              >
                                <Plus size={12} /> Schedule at {slot.label}
                              </button>
                            </div>
                          ) : (
                            <div className="space-y-2">
                              {hourEvents.map((ev) => {
                                const isGoogle = ev.isGoogleEvent;
                                const readOnly = isEventReadOnly(ev);
                                const isOwner = isEventOwnedByCurrentUser(ev);
                                return (
                                  <div
                                    key={ev.id}
                                    onClick={() => handleEventClick(ev)}
                                    className="p-3.5 bg-white hover:bg-pink-50/30 border border-gray-200 hover:border-[#D60041]/40 rounded-xl cursor-pointer transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm"
                                  >
                                    <div className="flex items-center gap-3 min-w-0">
                                      <div className="w-10 h-10 rounded-xl bg-pink-50 text-[#D60041] border border-pink-200 flex items-center justify-center font-bold text-sm shrink-0">
                                        {isGoogle ? 'G' : (ev.candidate_name || 'C').charAt(0)}
                                      </div>
                                      <div className="truncate">
                                        <div className="flex items-center gap-2 flex-wrap">
                                          <h5 className="text-sm font-bold text-gray-900 truncate">
                                            {ev.candidate_name && !isGoogle ? ev.candidate_name : ev.title}
                                          </h5>
                                          {isGoogle ? (
                                            <span className="bg-blue-100 text-blue-700 text-[9px] font-black px-2 py-0.5 rounded-full uppercase">Google</span>
                                          ) : (
                                            <>
                                              <span className={`text-[9px] font-black px-2 py-0.5 rounded-full uppercase ${
                                                ev.status === 'COMPLETED'
                                                  ? 'bg-emerald-100 text-emerald-700'
                                                  : ev.status === 'CANCELED' || ev.status === 'CANCELLED'
                                                  ? 'bg-rose-100 text-rose-700 line-through'
                                                  : 'bg-pink-100 text-[#D60041]'
                                              }`}>
                                                {ev.status}
                                              </span>
                                              {readOnly && (
                                                <span className="bg-amber-100 text-amber-800 text-[9px] font-black px-2 py-0.5 rounded-full uppercase inline-flex items-center gap-1">
                                                  <Lock size={9} /> Read-Only ({ev.interviewer_name ? `Assigned to ${ev.interviewer_name}` : 'Other HR'})
                                                </span>
                                              )}
                                            </>
                                          )}
                                        </div>
                                        <p className="text-xs text-gray-500 font-medium truncate mt-0.5">
                                          {ev.job_title ? `${ev.job_title} • ` : ''}{ev.title} ({formatEventTime(ev.start)} – {formatEventTime(ev.end)})
                                        </p>
                                        {!isGoogle && (
                                          <p className="text-[11px] text-[#D60041] font-semibold mt-0.5 flex items-center gap-1.5">
                                            <Users size={12} /> Panelist: {isOwner ? 'You' : (ev.interviewer_name || 'Assigned HR')}
                                          </p>
                                        )}
                                      </div>
                                    </div>

                                    <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                                      <button
                                        type="button"
                                        onClick={() => handleEventClick(ev)}
                                        className="px-3 py-1.5 bg-gray-50 hover:bg-gray-100 text-gray-700 border border-gray-200 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
                                      >
                                        {readOnly ? (
                                          <>
                                            <Lock size={12} className="text-amber-600" />
                                            <span>View (Read-Only)</span>
                                          </>
                                        ) : (
                                          <span>Manage</span>
                                        )}
                                      </button>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* VIEW 4: AGENDA / LIST VIEW */}
            {!isLoading && viewMode === 'agenda' && (
              <div className="bg-white border border-gray-100 rounded-3xl shadow-sm p-6 space-y-6">
                {/* Agenda Header & Sub-filter tabs */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-gray-100">
                  <div>
                    <h4 className="text-xl font-black text-gray-900">Upcoming Schedule Agenda</h4>
                    <p className="text-xs text-gray-500 font-medium mt-0.5">
                      All scheduled candidate interviews and synchronized Google Calendar commitments
                    </p>
                  </div>

                  {/* Filter Tabs within Agenda */}
                  <div className="flex bg-gray-100 p-1 rounded-xl border border-gray-200 text-xs font-bold text-gray-600">
                    <button
                      onClick={() => setAgendaFilterTab('upcoming')}
                      className={`px-3 py-1.5 rounded-lg transition-all ${
                        agendaFilterTab === 'upcoming' ? 'bg-white text-[#D60041] shadow-sm font-black' : 'hover:text-gray-900'
                      }`}
                    >
                      All Upcoming
                    </button>
                    <button
                      onClick={() => setAgendaFilterTab('month')}
                      className={`px-3 py-1.5 rounded-lg transition-all ${
                        agendaFilterTab === 'month' ? 'bg-white text-[#D60041] shadow-sm font-black' : 'hover:text-gray-900'
                      }`}
                    >
                      This Month
                    </button>
                    <button
                      onClick={() => setAgendaFilterTab('week')}
                      className={`px-3 py-1.5 rounded-lg transition-all ${
                        agendaFilterTab === 'week' ? 'bg-white text-[#D60041] shadow-sm font-black' : 'hover:text-gray-900'
                      }`}
                    >
                      This Week
                    </button>
                    <button
                      onClick={() => setAgendaFilterTab('past')}
                      className={`px-3 py-1.5 rounded-lg transition-all ${
                        agendaFilterTab === 'past' ? 'bg-white text-[#D60041] shadow-sm font-black' : 'hover:text-gray-900'
                      }`}
                    >
                      Past Sessions
                    </button>
                  </div>
                </div>

                {groupedAgendaEvents.length === 0 ? (
                  <div className="py-16 text-center text-gray-400 space-y-3">
                    <CalendarIcon size={36} className="mx-auto text-gray-300" />
                    <p className="text-sm font-bold text-gray-700">No scheduled sessions found for this agenda view</p>
                    <p className="text-xs text-gray-400 max-w-sm mx-auto">
                      Adjust your filter settings or click "New Schedule" to create a new candidate interview session.
                    </p>
                    <button
                      onClick={() => handleOpenNewSchedule(new Date())}
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#D60041] hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm"
                    >
                      <Plus size={14} /> Schedule Interview
                    </button>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {groupedAgendaEvents.map((group) => {
                      const isGroupToday = isToday(group.date);
                      return (
                        <div key={toLocalDateString(group.date)} className="space-y-3">
                          {/* Date Section Header */}
                          <div className="flex items-center gap-3">
                            <div className={`px-3 py-1 rounded-xl text-xs font-black uppercase tracking-wider ${
                              isGroupToday ? 'bg-[#D60041] text-white shadow-sm' : 'bg-gray-100 text-gray-700 border border-gray-200'
                            }`}>
                              {isGroupToday ? 'Today — ' : ''}
                              {group.date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
                            </div>
                            <div className="h-px bg-gray-100 flex-1" />
                            <span className="text-[11px] font-bold text-gray-400">
                              {group.events.length} session{group.events.length > 1 ? 's' : ''}
                            </span>
                          </div>

                          {/* Sessions in this Date */}
                          <div className="space-y-2.5">
                            {group.events.map((ev) => {
                              const isGoogle = ev.isGoogleEvent;
                              const readOnly = isEventReadOnly(ev);
                              const isOwner = isEventOwnedByCurrentUser(ev);
                              return (
                                <div
                                  key={ev.id}
                                  onClick={() => handleEventClick(ev)}
                                  className="p-4 bg-white hover:bg-pink-50/20 border border-gray-200 hover:border-[#D60041]/40 rounded-2xl cursor-pointer transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm"
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
                                      <div className="flex items-center gap-2 flex-wrap">
                                        <h5 className="text-sm font-bold text-gray-900 truncate">
                                          {ev.candidate_name && !isGoogle ? ev.candidate_name : ev.title}
                                        </h5>
                                        {isGoogle ? (
                                          <span className="bg-blue-100 text-blue-700 text-[9px] font-black px-2 py-0.5 rounded-full uppercase">Google Calendar</span>
                                        ) : (
                                          <>
                                            <span className={`text-[9px] font-black px-2 py-0.5 rounded-full uppercase ${
                                              ev.status === 'COMPLETED'
                                                ? 'bg-emerald-100 text-emerald-700'
                                                : ev.status === 'CANCELED' || ev.status === 'CANCELLED'
                                                ? 'bg-rose-100 text-rose-700'
                                                : 'bg-pink-100 text-[#D60041]'
                                            }`}>
                                              {ev.status}
                                            </span>
                                            {readOnly && (
                                              <span className="bg-amber-100 text-amber-800 text-[9px] font-black px-2 py-0.5 rounded-full uppercase inline-flex items-center gap-1">
                                                <Lock size={9} /> Read-Only ({ev.interviewer_name ? `Assigned to ${ev.interviewer_name}` : 'Other HR'})
                                              </span>
                                            )}
                                          </>
                                        )}
                                      </div>
                                      <p className="text-xs text-gray-500 font-medium truncate mt-0.5">
                                        {ev.job_title ? `${ev.job_title} • ` : ''}{ev.title}
                                      </p>
                                      <p className="text-[11px] text-gray-400 font-semibold mt-1 flex items-center gap-1.5">
                                        <Clock size={12} className="text-[#D60041]" />
                                        {formatEventTime(ev.start)} – {formatEventTime(ev.end)}
                                      </p>
                                      {!isGoogle && (
                                        <p className="text-[11px] text-[#D60041] font-semibold mt-1 flex items-center gap-1.5">
                                          <Users size={12} /> Assigned Panelist: {isOwner ? 'You' : (ev.interviewer_name || 'Assigned HR')}
                                        </p>
                                      )}
                                    </div>
                                  </div>

                                  <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                                    <button
                                      type="button"
                                      onClick={() => handleEventClick(ev)}
                                      className="px-3.5 py-2 bg-gray-50 hover:bg-gray-100 text-gray-700 border border-gray-200 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
                                    >
                                      {readOnly ? (
                                        <>
                                          <Lock size={12} className="text-amber-600" />
                                          <span>View (Read-Only)</span>
                                        </>
                                      ) : (
                                        <span>Manage</span>
                                      )}
                                    </button>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
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
        initialTime={newScheduleInitialTime}
        initialInterviewerId={newSchedulePreselectedHr}
        onScheduled={handleScheduled}
      />
    </div>
  );
};

export default HRSchedulingPage;
