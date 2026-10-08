import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Users, Building2, User, Settings, Search, Briefcase,
  HelpCircle, BookOpen, ChevronRight, MessageSquare, Menu, ChevronLeft, Scale,
  Sliders, Activity, Calendar, Sparkles, CheckCircle2
} from 'lucide-react';
import { useSelector, useDispatch } from 'react-redux';
import { toggleSidebar, closeSidebar } from '../../redux/slices/uiSlice';

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const { role: userRole } = useSelector(state => state.auth);
  const { isSidebarOpen } = useSelector(state => state.ui);

  const normRole = (userRole || '').toUpperCase();
  const isAdminRole = normRole === 'ADMIN';
  const isHRRole = normRole === 'HR';
  const isCandidateRole = normRole === 'CANDIDATE';
  const isHRPage = location.pathname.startsWith('/hr');
  const isHR = isHRRole || isHRPage;

  // Grouped navigation structure for modern SaaS UX
  const getNavSections = () => {
    if (isAdminRole) {
      return [
        {
          title: 'ANALYTICS & METRICS',
          items: [
            { label: 'Dashboard', path: '/admin/dashboard', icon: <LayoutDashboard size={19} /> },
            { label: 'Performance', path: '/admin/performance', icon: <Activity size={19} /> },
          ]
        },
        {
          title: 'MANAGEMENT',
          items: [
            { label: 'User Directory', path: '/admin/users', icon: <Users size={19} /> },
            { label: 'Job Postings', path: '/admin/jobmanagement', icon: <Briefcase size={19} /> },
            { label: 'System Config', path: '/admin/system-config', icon: <Sliders size={19} /> },
          ]
        },
        {
          title: 'COMMUNICATION',
          items: [
            { label: 'Messages', path: '/admin/messages', icon: <MessageSquare size={19} /> }
          ]
        }
      ];
    }

    if (isHR) {
      return [
        {
          title: 'TALENT PIPELINE',
          items: [
            { label: 'Dashboard', path: '/hr/dashboard', icon: <LayoutDashboard size={19} /> },
            { 
              label: 'AI Screening', 
              path: '/hr/screeningportal', 
              icon: <User size={19} />, 
              badge: 'AI', 
              badgeColor: 'bg-gradient-to-r from-rose-500 to-pink-500 text-white' 
            },
            { label: 'Interview Scheduling', path: '/hr/scheduling', icon: <Calendar size={19} /> },
            { label: 'Candidate Comparison', path: '/hr/comparecandidates', icon: <Scale size={19} /> },
          ]
        },
        {
          title: 'COMMUNICATION',
          items: [
            { label: 'Messages', path: '/hr/messages', icon: <MessageSquare size={19} /> }
          ]
        }
      ];
    }

    if (isCandidateRole) {
      return [
        {
          title: 'CAREER',
          items: [
            { label: 'Dashboard', path: '/candidate/dashboard', icon: <LayoutDashboard size={19} /> },
            { label: 'Find Jobs', path: '/candidate/findjobs', icon: <Search size={19} /> },
          ]
        },
        {
          title: 'COMMUNICATION',
          items: [
            { label: 'Messages', path: '/candidate/messages', icon: <MessageSquare size={19} /> }
          ]
        }
      ];
    }

    return [
      {
        title: 'EXPLORE',
        items: [
          { label: 'About', path: '/aboutpage', icon: <BookOpen size={19} /> },
          { label: 'Careers', path: '/careerspage', icon: <Briefcase size={19} /> }
        ]
      }
    ];
  };

  const navSections = getNavSections();

  const getWorkspaceTitle = () => {
    if (isHR) return 'Mariwasa HR';
    if (isAdminRole) return 'Admin Suite';
    if (isCandidateRole) return 'Career Portal';
    return 'Mariwasa ARAS';
  };

  const getWorkspaceSubtitle = () => {
    if (isHR) return 'Talent Operations';
    if (isAdminRole) return 'System Control';
    if (isCandidateRole) return 'Candidate Hub';
    return 'Resume Analysis';
  };

  const settingsPath = isHR ? '/hr/settings' : isAdminRole ? '/admin/settings' : '/accountsettings';

  return (
    <>
      {/* Mobile Backdrop for non-HR routes where sidebar can be toggled on mobile */}
      {!isHR && (
        <div 
          className={`lg:hidden fixed inset-0 bg-gray-900/40 backdrop-blur-xs z-[35] transition-opacity duration-300 ${
            isSidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
          }`}
          onClick={() => dispatch(closeSidebar())}
        />
      )}

      <aside
        className={`
          ${isHR ? 'hidden lg:flex' : 'flex'} fixed top-[81px] left-0 
          bg-white/95 backdrop-blur-md border-r border-gray-100/90 
          h-[calc(100vh-81px)] 
          z-[40] flex-col transition-all duration-300 ease-in-out shadow-[1px_0_12px_rgba(0,0,0,0.02)]
          ${isSidebarOpen ? 'translate-x-0 w-64' : '-translate-x-full lg:translate-x-0 lg:w-20'}
        `}
      >
        {/* WORKSPACE HEADER */}
        <div className={`p-3.5 border-b border-gray-100/80 flex items-center shrink-0 ${isSidebarOpen ? 'justify-between' : 'justify-center flex-col gap-2'}`}>
          {isSidebarOpen ? (
            <>
              <div className="flex items-center space-x-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#D60041] via-[#E11D48] to-[#FF4D6D] text-white flex items-center justify-center shadow-sm shadow-[#D60041]/25 shrink-0">
                  {isHR ? <Building2 size={18} /> : isAdminRole ? <Sliders size={18} /> : <Sparkles size={18} />}
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-bold text-gray-900 tracking-tight leading-tight truncate">
                    {getWorkspaceTitle()}
                  </h3>
                  <div className="flex items-center space-x-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider truncate">
                      {getWorkspaceSubtitle()}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => dispatch(toggleSidebar())}
                className="p-1.5 hover:bg-gray-100/80 active:scale-95 rounded-xl text-gray-400 hover:text-gray-700 transition-all shadow-xs"
                title="Collapse sidebar"
                aria-label="Collapse sidebar"
              >
                <ChevronLeft size={18} />
              </button>
            </>
          ) : (
            <>
              <div 
                onClick={() => dispatch(toggleSidebar())}
                className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#D60041] via-[#E11D48] to-[#FF4D6D] text-white flex items-center justify-center shadow-sm shadow-[#D60041]/25 cursor-pointer hover:scale-105 transition-transform"
                title="Expand sidebar"
              >
                {isHR ? <Building2 size={19} /> : isAdminRole ? <Sliders size={19} /> : <Sparkles size={19} />}
              </div>
              <button
                onClick={() => dispatch(toggleSidebar())}
                className="p-1.5 text-gray-400 hover:text-[#D60041] hover:bg-red-50 rounded-lg transition-all active:scale-95"
                title="Expand sidebar"
                aria-label="Expand sidebar"
              >
                <ChevronRight size={16} />
              </button>
            </>
          )}
        </div>

        {/* NAVIGATION ITEMS */}
        <div className="flex-grow overflow-y-auto overflow-x-hidden scrollbar-none px-3 py-3 space-y-4">
          {navSections.map((section, sIdx) => (
            <div key={sIdx} className="space-y-1">
              {isSidebarOpen ? (
                <div className="px-3 pt-1 pb-1">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                    {section.title}
                  </p>
                </div>
              ) : (
                <div className="w-full flex justify-center py-1">
                  <div className="w-5 border-t border-gray-100" />
                </div>
              )}

              <nav className="space-y-1">
                {section.items.map((item, index) => {
                  const isActive = location.pathname === item.path;

                  if (isSidebarOpen) {
                    return (
                      <button
                        key={index}
                        onClick={() => {
                          navigate(item.path);
                          if (window.innerWidth < 1024) dispatch(closeSidebar());
                        }}
                        className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl transition-all duration-200 group relative ${
                          isActive
                            ? 'bg-gradient-to-r from-red-50/90 to-pink-50/40 text-[#D60041] font-semibold border border-red-100/70 shadow-xs'
                            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50/80 font-medium'
                        }`}
                      >
                        <div className="flex items-center space-x-3 min-w-0">
                          {isActive && (
                            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[#D60041] rounded-r-full shadow-xs" />
                          )}
                          <span className={`transition-all duration-200 shrink-0 ${
                            isActive ? 'text-[#D60041] scale-105' : 'text-gray-400 group-hover:text-gray-600 group-hover:scale-105'
                          }`}>
                            {item.icon}
                          </span>
                          <span className="text-[13px] tracking-tight truncate leading-tight">
                            {item.label}
                          </span>
                        </div>
                        {item.badge && (
                          <span className={`text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded-md shrink-0 shadow-xs ${
                            item.badgeColor || 'bg-red-100 text-[#D60041]'
                          }`}>
                            {item.badge}
                          </span>
                        )}
                      </button>
                    );
                  }

                  // Collapsed View with Tooltip
                  return (
                    <div key={index} className="relative group flex justify-center w-full py-0.5">
                      <button
                        onClick={() => {
                          navigate(item.path);
                          if (window.innerWidth < 1024) dispatch(closeSidebar());
                        }}
                        className={`w-11 h-11 flex items-center justify-center rounded-xl transition-all duration-200 relative ${
                          isActive
                            ? 'bg-red-50 text-[#D60041] shadow-xs border border-red-100/60'
                            : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100/70'
                        }`}
                        aria-label={item.label}
                      >
                        {isActive && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[#D60041] rounded-r-full" />
                        )}
                        <span className={`transition-transform duration-200 ${
                          isActive ? 'text-[#D60041] scale-110' : 'text-gray-400 group-hover:text-gray-700 group-hover:scale-110'
                        }`}>
                          {item.icon}
                        </span>
                        {item.badge && (
                          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#D60041] rounded-full border border-white" />
                        )}
                      </button>

                      {/* Modern floating tooltip */}
                      <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-gray-900/95 backdrop-blur-md text-white text-xs font-semibold rounded-lg shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-all duration-150 pointer-events-none z-50 flex items-center gap-1.5">
                        <span>{item.label}</span>
                        {item.badge && (
                          <span className="bg-[#D60041] text-white text-[9px] px-1 py-0.2 rounded font-bold">
                            {item.badge}
                          </span>
                        )}
                        <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-gray-900/95" />
                      </div>
                    </div>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>

        {/* FOOTER SECTION */}
        <div className="p-3 border-t border-gray-100/80 bg-gray-50/40 shrink-0">
          {isSidebarOpen ? (
            <div className="bg-white border border-gray-100/80 rounded-2xl p-3 shadow-xs space-y-2.5">
              <div className="flex items-center justify-between px-0.5">
                <div className="flex items-center space-x-1.5">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-xs shadow-emerald-500/50" />
                  <span className="text-[11px] font-bold text-gray-700">ARAS Engine</span>
                </div>
                <span className="text-[9px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">
                  Online
                </span>
              </div>
              <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-gray-500">
                <button 
                  onClick={() => navigate(settingsPath)}
                  className="flex items-center space-x-1.5 text-[11px] font-semibold hover:text-[#D60041] transition-colors py-1 px-1.5 rounded-lg hover:bg-gray-50"
                  title="Account Settings"
                >
                  <Settings size={13} />
                  <span>Settings</span>
                </button>
                <button 
                  onClick={() => navigate('/aboutpage')}
                  className="flex items-center space-x-1.5 text-[11px] font-semibold hover:text-[#D60041] transition-colors py-1 px-1.5 rounded-lg hover:bg-gray-50"
                  title="Documentation & Help"
                >
                  <HelpCircle size={13} />
                  <span>Help</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center space-y-2 py-1">
              {/* Collapsed Settings Shortcut with Tooltip */}
              <div className="relative group">
                <button 
                  onClick={() => navigate(settingsPath)}
                  className="p-2 text-gray-400 hover:text-[#D60041] hover:bg-red-50 rounded-xl transition-all"
                  aria-label="Settings"
                >
                  <Settings size={18} />
                </button>
                <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-gray-900/95 backdrop-blur-md text-white text-xs font-semibold rounded-lg shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-all duration-150 pointer-events-none z-50">
                  Settings
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-gray-900/95" />
                </div>
              </div>

              {/* Collapsed Help Shortcut with Tooltip */}
              <div className="relative group">
                <button 
                  onClick={() => navigate('/aboutpage')}
                  className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all"
                  aria-label="Help"
                >
                  <HelpCircle size={18} />
                </button>
                <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-gray-900/95 backdrop-blur-md text-white text-xs font-semibold rounded-lg shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-all duration-150 pointer-events-none z-50">
                  Help Center
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-gray-900/95" />
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Spacer */}
      <div className={`hidden lg:block transition-all duration-300 shrink-0 ${isSidebarOpen ? 'w-64' : 'w-20'}`} />
    </>
  );
};

export default Sidebar;