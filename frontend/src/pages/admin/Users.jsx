import React, { useState, useMemo, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  Search, 
  UserPlus, 
  MoreHorizontal, 
  Mail, 
  Shield, 
  ShieldCheck, 
  UserCheck, 
  UserX, 
  ChevronLeft, 
  ChevronRight, 
  ChevronDown,
  Clock, 
  Archive, 
  RotateCcw, 
  Activity, 
  X, 
  Trash2, 
  Edit, 
  User, 
  Eye, 
  EyeOff,
  Download, 
  Filter, 
  CheckCircle2, 
  AlertTriangle, 
  Phone, 
  MapPin, 
  Sparkles, 
  Check, 
  ArrowUpDown,
  Briefcase
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { 
  useGetUsersQuery, 
  useArchiveUserMutation, 
  useUnarchiveUserMutation,
  useChangeUserRoleMutation,
  useCreateUserMutation,
  useUpdateUserMutation,
  useDeleteUserMutation
} from '../../redux/api/apiSlice';
import { useSelector } from 'react-redux';

const UsersPage = () => {
  const { data: users = [], isLoading, isFetching } = useGetUsersQuery();
  const [archiveUser] = useArchiveUserMutation();
  const [unarchiveUser] = useUnarchiveUserMutation();
  const [createUser] = useCreateUserMutation();
  const [updateUser] = useUpdateUserMutation();
  const [deleteUser] = useDeleteUserMutation();
  const [changeUserRole] = useChangeUserRoleMutation();
  
  const currentUserEmail = useSelector((state) => state.auth.user);
  
  // Filter & Search States
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL"); // ALL, ADMIN, HR, CANDIDATE
  const [statusFilter, setStatusFilter] = useState("ALL"); // ALL, ACTIVE, ARCHIVED
  const [sortBy, setSortBy] = useState("RECENT"); // RECENT, NAME_ASC, NAME_DESC, ROLE
  
  // Active dropdown menu for table row actions
  const [activeMenu, setActiveMenu] = useState(null);
  
  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  
  // Modals & Drawers
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [viewingUser, setViewingUser] = useState(null);
  const [editUserData, setEditUserData] = useState(null);
  const [showPassword, setShowPassword] = useState(false);

  // Forms
  const [formData, setFormData] = useState({ fullname: '', email: '', role: 'HR', password: '' });
  const [formSubmitting, setFormSubmitting] = useState(false);

  // Custom Toast Notification State
  const [toast, setToast] = useState(null);

  // Custom Confirmation Modal State
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    confirmText: 'Confirm',
    confirmType: 'danger', // danger, primary, warning
    icon: null,
    onConfirm: null
  });

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setActiveMenu(null);
    window.addEventListener('click', handleClickOutside);
    return () => window.removeEventListener('click', handleClickOutside);
  }, []);

  // Reset pagination on filter change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, roleFilter, statusFilter, sortBy]);

  // Derived counts for metric KPI cards
  const metrics = useMemo(() => {
    const total = users.length;
    const active = users.filter(u => !u.is_archived).length;
    const archived = users.filter(u => u.is_archived).length;
    const admins = users.filter(u => u.role === 'ADMIN').length;
    const hr = users.filter(u => u.role === 'HR').length;
    const candidates = users.filter(u => u.role === 'CANDIDATE').length;
    const online = users.filter(u => u.is_online && !u.is_archived).length;

    return { total, active, archived, admins, hr, candidates, online };
  }, [users]);

  // Filtering & Sorting
  const filteredUsers = useMemo(() => {
    let result = users.filter(user => {
      // Search matching across name, email, role, phone, location
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const nameMatch = user.fullname?.toLowerCase().includes(q);
        const emailMatch = user.email?.toLowerCase().includes(q);
        const roleMatch = user.role?.toLowerCase().includes(q);
        const phoneMatch = user.phone?.toLowerCase().includes(q);
        const locMatch = user.location?.toLowerCase().includes(q);
        if (!nameMatch && !emailMatch && !roleMatch && !phoneMatch && !locMatch) return false;
      }

      // Role Filter
      if (roleFilter !== "ALL" && user.role !== roleFilter) {
        return false;
      }

      // Status Filter
      if (statusFilter === "ACTIVE" && user.is_archived) return false;
      if (statusFilter === "ARCHIVED" && !user.is_archived) return false;

      return true;
    });

    // Sorting
    result.sort((a, b) => {
      if (sortBy === 'NAME_ASC') {
        return (a.fullname || '').localeCompare(b.fullname || '');
      }
      if (sortBy === 'NAME_DESC') {
        return (b.fullname || '').localeCompare(a.fullname || '');
      }
      if (sortBy === 'ROLE') {
        return (a.role || '').localeCompare(b.role || '');
      }
      // Default: RECENT (sort by online status or last_active or id desc)
      if (a.is_online && !b.is_online) return -1;
      if (!a.is_online && b.is_online) return 1;
      const dateA = a.last_active ? new Date(a.last_active).getTime() : 0;
      const dateB = b.last_active ? new Date(b.last_active).getTime() : 0;
      if (dateA !== dateB) return dateB - dateA;
      return (b.id || 0) - (a.id || 0);
    });

    return result;
  }, [users, searchQuery, roleFilter, statusFilter, sortBy]);

  // Hidden archived matches notice when filtering by ACTIVE
  const hiddenArchivedMatchCount = useMemo(() => {
    if (!searchQuery.trim() || statusFilter !== 'ACTIVE') return 0;
    const q = searchQuery.toLowerCase().trim();
    return users.filter(u => u.is_archived && (
      u.fullname?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q) ||
      u.role?.toLowerCase().includes(q)
    )).length;
  }, [users, searchQuery, statusFilter]);

  // Paginated records
  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / itemsPerPage));
  const paginatedUsers = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredUsers.slice(start, start + itemsPerPage);
  }, [filteredUsers, currentPage, itemsPerPage]);

  // Action Handlers with in-app confirmation modal
  const handleArchiveConfirm = (user) => {
    setConfirmModal({
      isOpen: true,
      title: 'Suspend User Account',
      message: `Are you sure you want to suspend access for ${user.fullname} (${user.email})? They will be immediately prevented from logging into the platform.`,
      confirmText: 'Suspend Account',
      confirmType: 'warning',
      icon: <Archive className="text-orange-500" size={24} />,
      onConfirm: async () => {
        try {
          await archiveUser(user.id).unwrap();
          showToast(`Account for ${user.fullname} has been suspended.`, 'success');
          if (viewingUser?.id === user.id) setViewingUser(prev => ({ ...prev, is_archived: true }));
        } catch (err) {
          showToast(err.data?.detail || 'Failed to suspend account.', 'error');
        }
      }
    });
  };

  const handleUnarchiveConfirm = (user) => {
    setConfirmModal({
      isOpen: true,
      title: 'Restore User Account',
      message: `Restore active access for ${user.fullname} (${user.email})? They will regain immediate platform access.`,
      confirmText: 'Restore Account',
      confirmType: 'primary',
      icon: <RotateCcw className="text-emerald-500" size={24} />,
      onConfirm: async () => {
        try {
          await unarchiveUser(user.id).unwrap();
          showToast(`Account for ${user.fullname} has been restored.`, 'success');
          if (viewingUser?.id === user.id) setViewingUser(prev => ({ ...prev, is_archived: false }));
        } catch (err) {
          showToast(err.data?.detail || 'Failed to restore account.', 'error');
        }
      }
    });
  };

  const handleRoleChangeConfirm = (user, newRole) => {
    setConfirmModal({
      isOpen: true,
      title: 'Modify Access Role',
      message: `Assign the ${newRole} role to ${user.fullname}? This changes their portal permissions and operational capabilities.`,
      confirmText: `Confirm Role Change to ${newRole}`,
      confirmType: 'primary',
      icon: <ShieldCheck className="text-indigo-600" size={24} />,
      onConfirm: async () => {
        try {
          await changeUserRole({ userId: user.id, role: newRole }).unwrap();
          showToast(`User role updated to ${newRole} successfully.`, 'success');
          if (viewingUser?.id === user.id) setViewingUser(prev => ({ ...prev, role: newRole }));
        } catch (err) {
          showToast(err.data?.detail || 'Failed to update user role.', 'error');
        }
      }
    });
  };

  const handleDeleteConfirm = (user) => {
    setConfirmModal({
      isOpen: true,
      title: 'Permanently Delete User',
      message: `Are you sure you want to permanently delete ${user.fullname} (${user.email})? This action cannot be reversed and removes all associated records.`,
      confirmText: 'Permanently Delete',
      confirmType: 'danger',
      icon: <Trash2 className="text-red-600" size={24} />,
      onConfirm: async () => {
        try {
          await deleteUser(user.id).unwrap();
          showToast(`User ${user.fullname} was permanently deleted.`, 'success');
          if (viewingUser?.id === user.id) setViewingUser(null);
        } catch (err) {
          showToast(err.data?.detail || 'Failed to delete user.', 'error');
        }
      }
    });
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setFormSubmitting(true);
    try {
      await createUser(formData).unwrap();
      setIsCreateModalOpen(false);
      setFormData({ fullname: '', email: '', role: 'HR', password: '' });
      showToast(`User account created successfully for ${formData.fullname}.`, 'success');
    } catch (err) {
      showToast(err.data?.detail || 'Failed to create user account.', 'error');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFormSubmitting(true);
    try {
      const updateData = { ...formData };
      if (!updateData.password) {
        delete updateData.password;
      }
      await updateUser({ userId: editUserData.id, body: updateData }).unwrap();
      setIsEditModalOpen(false);
      if (viewingUser?.id === editUserData.id) {
        setViewingUser(prev => ({ ...prev, ...updateData }));
      }
      setEditUserData(null);
      showToast('User details updated successfully.', 'success');
    } catch (err) {
      showToast(err.data?.detail || 'Failed to update user.', 'error');
    } finally {
      setFormSubmitting(false);
    }
  };

  const openEditModal = (user) => {
    setEditUserData(user);
    setFormData({
      fullname: user.fullname,
      email: user.email,
      role: user.role,
      password: ''
    });
    setShowPassword(false);
    setIsEditModalOpen(true);
  };

  // CSV Export utility
  const handleExportCSV = () => {
    if (filteredUsers.length === 0) {
      showToast("No users match the current filter to export.", "error");
      return;
    }
    const headers = ['ID', 'Full Name', 'Email', 'Role', 'Status', 'Phone', 'Location', 'Last Active'];
    const rows = filteredUsers.map(u => [
      u.id,
      `"${(u.fullname || '').replace(/"/g, '""')}"`,
      `"${(u.email || '').replace(/"/g, '""')}"`,
      u.role,
      u.is_archived ? 'Suspended' : (u.is_online ? 'Active Now' : 'Offline'),
      `"${(u.phone || '').replace(/"/g, '""')}"`,
      `"${(u.location || '').replace(/"/g, '""')}"`,
      u.last_active ? new Date(u.last_active).toLocaleString() : 'Never'
    ]);
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `user_directory_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast(`Exported ${filteredUsers.length} users to CSV.`, 'success');
  };

  // Render role badge helper
  const renderRoleBadge = (role) => {
    switch (role) {
      case 'ADMIN':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-xl bg-purple-50 text-purple-700 border border-purple-200/60 shadow-xs">
            <ShieldCheck size={13} className="text-purple-600" />
            Administrator
          </span>
        );
      case 'HR':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200/60 shadow-xs">
            <UserCheck size={13} className="text-indigo-600" />
            HR Specialist
          </span>
        );
      case 'CANDIDATE':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-xl bg-slate-100 text-slate-700 border border-slate-200/80 shadow-xs">
            <User size={13} className="text-slate-500" />
            Candidate
          </span>
        );
    }
  };

  return (
    <div className="bg-[#FAFAFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col relative overflow-x-hidden">
      {/* Decorative subtle background gradient */}
      <div className="absolute top-0 left-0 w-full h-[320px] bg-gradient-to-b from-[#D10043]/5 via-[#D10043]/2 to-transparent pointer-events-none z-0"></div>
      
      <Helmet>
        <title>User Directory | Admin Portal</title>
      </Helmet>
      
      <Header />
      
      {/* Floating Toast Notification */}
      {toast && (
        <div className="fixed top-20 right-6 z-50 flex items-center gap-3 px-4 py-3 bg-white/95 backdrop-blur-md rounded-2xl shadow-xl border border-gray-100 text-sm font-semibold transition-all duration-300 animate-in fade-in slide-in-from-top-3">
          {toast.type === 'success' ? (
            <CheckCircle2 className="text-emerald-500 shrink-0" size={20} />
          ) : (
            <AlertTriangle className="text-red-500 shrink-0" size={20} />
          )}
          <span className="text-gray-800">{toast.message}</span>
          <button 
            onClick={() => setToast(null)}
            className="text-gray-400 hover:text-gray-600 p-1 rounded-lg transition-colors ml-2"
          >
            <X size={15} />
          </button>
        </div>
      )}

      <div className="flex flex-1 z-10 relative">
        <Sidebar />
        
        <main className="flex-1 max-w-[1500px] mx-auto px-4 sm:px-8 lg:px-10 py-8 sm:py-10 w-full overflow-hidden flex flex-col gap-8">
          
          {/* Header Title & Primary Action */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-gray-200/80 shadow-xs text-[11px] font-black text-gray-500 mb-2.5 tracking-wider uppercase">
                <ShieldCheck size={13} className="text-[#D10043]" />
                Access Control & Directory
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900">
                User Directory
              </h1>
              <p className="text-sm text-gray-500 font-medium mt-1.5 max-w-2xl leading-relaxed">
                Centralized registry of all platform accounts. Provision credentials, assign operational roles, audit real-time activity, and oversee security policies.
              </p>
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto shrink-0">
              <button
                type="button"
                onClick={handleExportCSV}
                className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-2xl bg-white hover:bg-gray-50 text-gray-700 border border-gray-200/90 shadow-xs hover:border-gray-300 text-sm font-semibold transition-all cursor-pointer"
                title="Export filtered directory to CSV format"
              >
                <Download size={16} className="text-gray-500" />
                <span>Export CSV</span>
              </button>

              <button 
                type="button"
                onClick={() => {
                  setFormData({ fullname: '', email: '', role: 'HR', password: '' });
                  setShowPassword(false);
                  setIsCreateModalOpen(true);
                }}
                className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 bg-gradient-to-r from-[#D10043] to-[#B00038] hover:from-[#c2003e] hover:to-[#9e0032] text-white px-5 py-2.5 rounded-2xl text-sm font-bold shadow-md shadow-red-500/20 hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer"
              >
                <UserPlus size={16} />
                <span>Create Account</span>
              </button>
            </div>
          </div>

          {/* KPI Metrics Cards (Interactive Quick Filters) */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
            {/* Card: Total */}
            <div 
              onClick={() => { setRoleFilter("ALL"); setStatusFilter("ALL"); }}
              className={`p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden group ${
                roleFilter === "ALL" && statusFilter === "ALL" 
                  ? "bg-white border-[#D10043] shadow-md shadow-[#D10043]/10 ring-2 ring-[#D10043]/10" 
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Total</span>
                <span className="p-1.5 rounded-xl bg-gray-100 text-gray-600 group-hover:scale-110 transition-transform">
                  <User size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.total}</div>
              <div className="text-[11px] font-medium text-gray-400 mt-0.5">All accounts</div>
            </div>

            {/* Card: Active Users */}
            <div 
              onClick={() => { setStatusFilter("ACTIVE"); setRoleFilter("ALL"); }}
              className={`p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden group ${
                statusFilter === "ACTIVE" && roleFilter === "ALL"
                  ? "bg-white border-emerald-500 shadow-md shadow-emerald-500/10 ring-2 ring-emerald-500/10" 
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-emerald-600 uppercase tracking-wider">Active</span>
                <span className="p-1.5 rounded-xl bg-emerald-50 text-emerald-600 group-hover:scale-110 transition-transform">
                  <UserCheck size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.active}</div>
              <div className="text-[11px] font-medium text-emerald-600/80 mt-0.5 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                {metrics.online} online now
              </div>
            </div>

            {/* Card: Administrators */}
            <div 
              onClick={() => { setRoleFilter("ADMIN"); setStatusFilter("ALL"); }}
              className={`p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden group ${
                roleFilter === "ADMIN" 
                  ? "bg-white border-purple-500 shadow-md shadow-purple-500/10 ring-2 ring-purple-500/10" 
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-purple-600 uppercase tracking-wider">Admins</span>
                <span className="p-1.5 rounded-xl bg-purple-50 text-purple-600 group-hover:scale-110 transition-transform">
                  <ShieldCheck size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.admins}</div>
              <div className="text-[11px] font-medium text-gray-400 mt-0.5">System owners</div>
            </div>

            {/* Card: HR Specialists */}
            <div 
              onClick={() => { setRoleFilter("HR"); setStatusFilter("ALL"); }}
              className={`p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden group ${
                roleFilter === "HR" 
                  ? "bg-white border-indigo-500 shadow-md shadow-indigo-500/10 ring-2 ring-indigo-500/10" 
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-indigo-600 uppercase tracking-wider">HR Staff</span>
                <span className="p-1.5 rounded-xl bg-indigo-50 text-indigo-600 group-hover:scale-110 transition-transform">
                  <Briefcase size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.hr}</div>
              <div className="text-[11px] font-medium text-gray-400 mt-0.5">Talent managers</div>
            </div>

            {/* Card: Candidates */}
            <div 
              onClick={() => { setRoleFilter("CANDIDATE"); setStatusFilter("ALL"); }}
              className={`p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden group ${
                roleFilter === "CANDIDATE" 
                  ? "bg-white border-slate-600 shadow-md shadow-slate-500/10 ring-2 ring-slate-500/10" 
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">Candidates</span>
                <span className="p-1.5 rounded-xl bg-slate-100 text-slate-600 group-hover:scale-110 transition-transform">
                  <User size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.candidates}</div>
              <div className="text-[11px] font-medium text-gray-400 mt-0.5">Registered applicants</div>
            </div>

            {/* Card: Suspended */}
            <div 
              onClick={() => { setStatusFilter("ARCHIVED"); setRoleFilter("ALL"); }}
              className={`p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden group ${
                statusFilter === "ARCHIVED" 
                  ? "bg-white border-orange-500 shadow-md shadow-orange-500/10 ring-2 ring-orange-500/10" 
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-orange-600 uppercase tracking-wider">Suspended</span>
                <span className="p-1.5 rounded-xl bg-orange-50 text-orange-600 group-hover:scale-110 transition-transform">
                  <UserX size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.archived}</div>
              <div className="text-[11px] font-medium text-gray-400 mt-0.5">Access disabled</div>
            </div>
          </div>

          {/* Filtering & Search Toolbar */}
          <div className="bg-white rounded-3xl p-4 sm:p-5 border border-gray-200/80 shadow-xs flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
            
            {/* Search Input */}
            <div className="relative flex-1 min-w-[260px] group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-[#D10043] transition-colors" size={17} />
              <input 
                type="text" 
                placeholder="Search by name, email, phone, location..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-gray-50/80 hover:bg-gray-50 border border-gray-200 rounded-2xl py-2.5 pl-11 pr-10 text-sm font-medium text-gray-800 placeholder-gray-400 focus:bg-white focus:ring-3 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all outline-none"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 rounded-full transition-colors cursor-pointer"
                >
                  <X size={14} />
                </button>
              )}
            </div>

            {/* Controls Filter Group */}
            <div className="flex flex-wrap sm:flex-nowrap items-center gap-3">
              
              {/* Role Filter Dropdown */}
              <div className="relative shrink-0">
                <select 
                  value={roleFilter} 
                  onChange={(e) => setRoleFilter(e.target.value)}
                  className="bg-gray-50/80 hover:bg-gray-50 border border-gray-200 text-gray-700 text-xs font-bold rounded-2xl pl-3.5 pr-8 py-2.5 outline-none focus:ring-3 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all cursor-pointer appearance-none"
                >
                  <option value="ALL">All Roles ({metrics.total})</option>
                  <option value="ADMIN">Administrators ({metrics.admins})</option>
                  <option value="HR">HR Specialists ({metrics.hr})</option>
                  <option value="CANDIDATE">Candidates ({metrics.candidates})</option>
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>

              {/* Status Filter Segment */}
              <div className="flex items-center bg-gray-100/80 p-1 rounded-2xl shrink-0">
                <button
                  type="button"
                  onClick={() => setStatusFilter("ALL")}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    statusFilter === "ALL" ? "bg-white text-gray-900 shadow-xs" : "text-gray-500 hover:text-gray-800"
                  }`}
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={() => setStatusFilter("ACTIVE")}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    statusFilter === "ACTIVE" ? "bg-white text-emerald-700 shadow-xs" : "text-gray-500 hover:text-gray-800"
                  }`}
                >
                  Active
                </button>
                <button
                  type="button"
                  onClick={() => setStatusFilter("ARCHIVED")}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    statusFilter === "ARCHIVED" ? "bg-white text-orange-600 shadow-xs" : "text-gray-500 hover:text-gray-800"
                  }`}
                >
                  Suspended
                </button>
              </div>

              {/* Sort Selector */}
              <div className="relative shrink-0">
                <select 
                  value={sortBy} 
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-gray-50/80 hover:bg-gray-50 border border-gray-200 text-gray-700 text-xs font-bold rounded-2xl pl-3.5 pr-8 py-2.5 outline-none focus:ring-3 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all cursor-pointer appearance-none"
                >
                  <option value="RECENT">Sort: Activity / Newest</option>
                  <option value="NAME_ASC">Name (A → Z)</option>
                  <option value="NAME_DESC">Name (Z → A)</option>
                  <option value="ROLE">Role Priority</option>
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>

            </div>
          </div>

          {/* Search notice if suspended accounts matched while searching in Active view */}
          {hiddenArchivedMatchCount > 0 && (
            <div className="flex items-center justify-between p-3.5 bg-orange-50/80 border border-orange-200/90 rounded-2xl text-xs sm:text-sm text-orange-900 shadow-xs">
              <div className="flex items-center gap-2.5">
                <Archive size={16} className="text-orange-600 shrink-0" />
                <span>
                  Notice: Found <strong>{hiddenArchivedMatchCount}</strong> suspended user(s) matching your query.
                </span>
              </div>
              <button
                type="button"
                onClick={() => setStatusFilter("ARCHIVED")}
                className="px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white font-bold rounded-xl text-xs transition-all cursor-pointer shrink-0 shadow-xs"
              >
                Show Suspended
              </button>
            </div>
          )}

          {/* Main User Directory Table Container */}
          <div className="bg-white rounded-3xl border border-gray-200/80 shadow-sm overflow-hidden flex flex-col">
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[760px]">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/60">
                    <th className="px-6 py-4 text-[11px] font-black uppercase tracking-wider text-gray-400">User Identity</th>
                    <th className="px-6 py-4 text-[11px] font-black uppercase tracking-wider text-gray-400">Role & Access</th>
                    <th className="px-6 py-4 text-[11px] font-black uppercase tracking-wider text-gray-400">Status & Activity</th>
                    <th className="px-6 py-4 text-[11px] font-black uppercase tracking-wider text-gray-400 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {isLoading ? (
                    <tr>
                      <td colSpan="4" className="px-6 py-20 text-center">
                        <div className="flex flex-col items-center justify-center">
                          <div className="relative w-10 h-10 mb-3">
                            <div className="absolute inset-0 border-3 border-[#D10043]/20 rounded-full"></div>
                            <div className="absolute inset-0 border-3 border-[#D10043] rounded-full border-t-transparent animate-spin"></div>
                          </div>
                          <p className="text-sm font-bold text-gray-800">Synchronizing Directory...</p>
                          <p className="text-xs text-gray-400 mt-1 font-medium">Loading user profiles and account records.</p>
                        </div>
                      </td>
                    </tr>
                  ) : paginatedUsers.length > 0 ? (
                    paginatedUsers.map((user) => {
                      const isCurrentUser = user.email === currentUserEmail;

                      return (
                        <tr 
                          key={user.id} 
                          className={`group hover:bg-gray-50/60 transition-colors ${
                            user.is_archived ? 'bg-orange-50/25' : ''
                          }`}
                        >
                          {/* User Identity Column */}
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3.5">
                              <div className="relative shrink-0">
                                <div className={`w-10 h-10 rounded-2xl flex items-center justify-center overflow-hidden border shadow-xs text-sm font-bold ${
                                  user.profile_image_url
                                    ? 'border-gray-200'
                                    : user.is_archived
                                    ? 'bg-orange-100 text-orange-700 border-orange-200'
                                    : user.role === 'ADMIN'
                                    ? 'bg-purple-50 text-purple-700 border-purple-200'
                                    : user.role === 'HR'
                                    ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                                    : 'bg-red-50 text-[#D10043] border-red-100'
                                }`}>
                                  {user.profile_image_url ? (
                                    <img src={user.profile_image_url} alt={user.fullname} className="w-full h-full object-cover" />
                                  ) : (
                                    user.fullname?.charAt(0).toUpperCase() || 'U'
                                  )}
                                </div>
                                {user.is_online && !user.is_archived && (
                                  <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 border-2 border-white rounded-full shadow-xs" title="Online now"></span>
                                )}
                              </div>
                              
                              <div className="flex flex-col min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span 
                                    onClick={() => setViewingUser(user)}
                                    className="text-sm font-bold text-gray-900 group-hover:text-[#D10043] transition-colors cursor-pointer truncate max-w-[200px] sm:max-w-xs"
                                    title="Click to view full user profile"
                                  >
                                    {user.fullname}
                                  </span>
                                  {isCurrentUser && (
                                    <span className="text-[10px] font-black bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full uppercase tracking-wider">
                                      You
                                    </span>
                                  )}
                                  {user.is_archived && (
                                    <span className="text-[10px] font-black bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full uppercase tracking-wider border border-orange-200/60">
                                      Suspended
                                    </span>
                                  )}
                                </div>

                                <div className="flex items-center gap-3 text-xs text-gray-500 font-medium mt-0.5 truncate">
                                  <span className="flex items-center gap-1 truncate">
                                    <Mail size={12} className="text-gray-400 shrink-0" />
                                    {user.email}
                                  </span>
                                  {user.location && (
                                    <span className="hidden sm:flex items-center gap-1 text-gray-400 truncate">
                                      <MapPin size={11} className="shrink-0" />
                                      {user.location}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* Role & Access Column */}
                          <td className="px-6 py-4">
                            <div className="flex flex-col items-start gap-1">
                              {renderRoleBadge(user.role)}
                            </div>
                          </td>

                          {/* Status & Activity Column */}
                          <td className="px-6 py-4">
                            <div className="flex flex-col gap-1">
                              {user.is_archived ? (
                                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-orange-700">
                                  <div className="w-1.5 h-1.5 bg-orange-500 rounded-full"></div>
                                  Access Suspended
                                </span>
                              ) : user.is_online ? (
                                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700">
                                  <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
                                  Active Now
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-gray-500">
                                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full"></div>
                                  Offline
                                </span>
                              )}
                              
                              <p className="text-[11px] text-gray-400 font-medium flex items-center gap-1.5">
                                <Clock size={11} className="text-gray-400" />
                                {user.last_active ? (
                                  new Date(user.last_active).toLocaleString(undefined, { 
                                    month: 'short', 
                                    day: 'numeric', 
                                    hour: '2-digit', 
                                    minute: '2-digit' 
                                  })
                                ) : (
                                  'No recent session'
                                )}
                              </p>
                            </div>
                          </td>

                          {/* Row Actions Column */}
                          <td className="px-6 py-4 text-right">
                            <div className="inline-flex items-center gap-1">
                              {/* Quick Inspect Button */}
                              <button
                                type="button"
                                onClick={() => setViewingUser(user)}
                                className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-colors cursor-pointer"
                                title="View User Details"
                              >
                                <Eye size={16} />
                              </button>

                              {/* Quick Edit Button */}
                              <button
                                type="button"
                                onClick={() => openEditModal(user)}
                                className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-colors cursor-pointer"
                                title="Edit User"
                              >
                                <Edit size={16} />
                              </button>

                              {/* Dropdown Menu for Role Change, Suspend/Restore, Delete */}
                              <div className="relative">
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveMenu(activeMenu === user.id ? null : user.id);
                                  }}
                                  className={`p-2 rounded-xl transition-colors cursor-pointer ${
                                    activeMenu === user.id 
                                      ? 'bg-gray-100 text-gray-900 shadow-xs' 
                                      : 'text-gray-400 hover:text-gray-700 hover:bg-gray-100'
                                  }`}
                                  title="More User Options"
                                >
                                  <MoreHorizontal size={16} />
                                </button>

                                {activeMenu === user.id && (
                                  <div 
                                    onClick={(e) => e.stopPropagation()}
                                    className="absolute right-0 top-10 w-56 bg-white rounded-2xl shadow-xl border border-gray-100 py-2 z-40 text-left animate-in fade-in zoom-in-95 duration-150"
                                  >
                                    <div className="px-4 py-1.5 border-b border-gray-50 mb-1">
                                      <p className="text-[10px] font-black text-gray-400 uppercase tracking-wider">Account Actions</p>
                                    </div>

                                    <button
                                      type="button"
                                      onClick={() => {
                                        setActiveMenu(null);
                                        setViewingUser(user);
                                      }}
                                      className="w-full px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 flex items-center gap-2.5 transition-colors cursor-pointer"
                                    >
                                      <Eye size={14} className="text-gray-400" />
                                      View Profile Card
                                    </button>

                                    <button
                                      type="button"
                                      onClick={() => {
                                        setActiveMenu(null);
                                        openEditModal(user);
                                      }}
                                      className="w-full px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 flex items-center gap-2.5 transition-colors cursor-pointer"
                                    >
                                      <Edit size={14} className="text-gray-400" />
                                      Edit Credentials
                                    </button>

                                    {/* Role Assignment Options */}
                                    <div className="border-t border-gray-50 my-1.5"></div>
                                    <div className="px-4 py-1 text-[10px] font-black text-gray-400 uppercase tracking-wider">
                                      Assign Role
                                    </div>

                                    {['ADMIN', 'HR', 'CANDIDATE'].map((role) => (
                                      user.role !== role && (
                                        <button
                                          key={role}
                                          type="button"
                                          onClick={() => {
                                            setActiveMenu(null);
                                            handleRoleChangeConfirm(user, role);
                                          }}
                                          className="w-full px-4 py-1.5 text-xs font-semibold text-gray-600 hover:bg-indigo-50 hover:text-indigo-700 flex items-center justify-between transition-colors cursor-pointer"
                                        >
                                          <span>Set as {role === 'ADMIN' ? 'Administrator' : role === 'HR' ? 'HR Specialist' : 'Candidate'}</span>
                                        </button>
                                      )
                                    ))}

                                    {/* Suspend or Restore */}
                                    <div className="border-t border-gray-50 my-1.5"></div>
                                    {!isCurrentUser ? (
                                      <>
                                        {user.is_archived ? (
                                          <button
                                            type="button"
                                            onClick={() => {
                                              setActiveMenu(null);
                                              handleUnarchiveConfirm(user);
                                            }}
                                            className="w-full px-4 py-2 text-xs font-bold text-emerald-600 hover:bg-emerald-50 flex items-center gap-2.5 transition-colors cursor-pointer"
                                          >
                                            <RotateCcw size={14} className="text-emerald-500" />
                                            Restore Account Access
                                          </button>
                                        ) : (
                                          <button
                                            type="button"
                                            onClick={() => {
                                              setActiveMenu(null);
                                              handleArchiveConfirm(user);
                                            }}
                                            className="w-full px-4 py-2 text-xs font-bold text-orange-600 hover:bg-orange-50 flex items-center gap-2.5 transition-colors cursor-pointer"
                                          >
                                            <Archive size={14} className="text-orange-500" />
                                            Suspend Account Access
                                          </button>
                                        )}

                                        <button
                                          type="button"
                                          onClick={() => {
                                            setActiveMenu(null);
                                            handleDeleteConfirm(user);
                                          }}
                                          className="w-full px-4 py-2 text-xs font-bold text-red-600 hover:bg-red-50 flex items-center gap-2.5 transition-colors cursor-pointer"
                                        >
                                          <Trash2 size={14} className="text-red-500" />
                                          Delete Permanently
                                        </button>
                                      </>
                                    ) : (
                                      <div className="px-4 py-2 text-[11px] text-gray-400 italic">
                                        Self-action restricted
                                      </div>
                                    )}

                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="4" className="px-6 py-16 text-center">
                        <div className="flex flex-col items-center justify-center max-w-md mx-auto">
                          <div className="w-14 h-14 bg-gray-50 rounded-2xl flex items-center justify-center mb-3 text-gray-400">
                            <Search size={22} />
                          </div>
                          <p className="text-base font-bold text-gray-900">No users match your filters</p>
                          <p className="text-xs text-gray-500 mt-1 text-center">
                            {searchQuery ? (
                              <span>No results for <strong className="text-gray-700">"{searchQuery}"</strong>. Try clearing search or adjusting your status filters.</span>
                            ) : (
                              <span>No user records found under the selected criteria.</span>
                            )}
                          </p>
                          <button
                            type="button"
                            onClick={() => {
                              setSearchQuery("");
                              setRoleFilter("ALL");
                              setStatusFilter("ALL");
                            }}
                            className="mt-4 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-bold rounded-xl transition-colors cursor-pointer"
                          >
                            Reset All Filters
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Functional Pagination Bar */}
            <div className="px-6 py-4 border-t border-gray-100 bg-gray-50/50 flex flex-col sm:flex-row items-center justify-between gap-4">
              
              <div className="flex items-center gap-4 text-xs text-gray-500 font-semibold">
                <span>
                  Showing {filteredUsers.length === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1} - {Math.min(currentPage * itemsPerPage, filteredUsers.length)} of {filteredUsers.length} members
                </span>
                
                <div className="flex items-center gap-1.5">
                  <span className="text-gray-400">Rows per page:</span>
                  <select
                    value={itemsPerPage}
                    onChange={(e) => {
                      setItemsPerPage(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="bg-white border border-gray-200 rounded-lg px-2 py-1 text-xs font-bold text-gray-700 outline-none cursor-pointer focus:border-[#D10043]"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                  </select>
                </div>
              </div>

              {totalPages > 1 && (
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="p-1.5 rounded-xl border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-xs"
                    title="Previous page"
                  >
                    <ChevronLeft size={16} />
                  </button>

                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
                    .map((page, idx, arr) => {
                      const prevPage = arr[idx - 1];
                      const showEllipsis = prevPage && page - prevPage > 1;

                      return (
                        <React.Fragment key={page}>
                          {showEllipsis && <span className="px-1 text-gray-400 text-xs">...</span>}
                          <button
                            type="button"
                            onClick={() => setCurrentPage(page)}
                            className={`min-w-[32px] h-8 rounded-xl text-xs font-bold transition-all ${
                              currentPage === page
                                ? 'bg-[#D10043] text-white shadow-xs'
                                : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
                            }`}
                          >
                            {page}
                          </button>
                        </React.Fragment>
                      );
                    })}

                  <button
                    type="button"
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    className="p-1.5 rounded-xl border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-xs"
                    title="Next page"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              )}

            </div>

          </div>

        </main>
      </div>

      {/* User Details Modal (Drawer) */}
      {viewingUser && (
        <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 w-full max-w-lg shadow-2xl relative border border-gray-100 animate-in fade-in zoom-in-95 duration-200">
            <button 
              onClick={() => setViewingUser(null)}
              className="absolute top-5 right-5 w-8 h-8 flex items-center justify-center rounded-full bg-gray-50 text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer"
            >
              <X size={18} />
            </button>

            {/* Profile Header */}
            <div className="flex items-center gap-4 mb-6 pb-6 border-b border-gray-100">
              <div className="relative">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center overflow-hidden border shadow-sm text-xl font-black ${
                  viewingUser.profile_image_url
                    ? 'border-gray-200'
                    : viewingUser.is_archived
                    ? 'bg-orange-100 text-orange-700 border-orange-200'
                    : viewingUser.role === 'ADMIN'
                    ? 'bg-purple-50 text-purple-700 border-purple-200'
                    : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                }`}>
                  {viewingUser.profile_image_url ? (
                    <img src={viewingUser.profile_image_url} alt={viewingUser.fullname} className="w-full h-full object-cover" />
                  ) : (
                    viewingUser.fullname?.charAt(0).toUpperCase() || 'U'
                  )}
                </div>
                {viewingUser.is_online && !viewingUser.is_archived && (
                  <span className="absolute -bottom-1 -right-1 w-4 h-4 bg-emerald-500 border-2 border-white rounded-full shadow-xs"></span>
                )}
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-extrabold text-gray-900">{viewingUser.fullname}</h3>
                  {viewingUser.is_archived && (
                    <span className="text-[10px] font-black bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full uppercase tracking-wider">
                      Suspended
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 font-medium mt-0.5">{viewingUser.email}</p>
                <div className="mt-2">{renderRoleBadge(viewingUser.role)}</div>
              </div>
            </div>

            {/* Profile Detailed Info Grid */}
            <div className="space-y-4 mb-6">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3.5 bg-gray-50/80 rounded-2xl border border-gray-100">
                  <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider">Account ID</span>
                  <p className="text-sm font-bold text-gray-800 mt-0.5">#{viewingUser.id}</p>
                </div>
                <div className="p-3.5 bg-gray-50/80 rounded-2xl border border-gray-100">
                  <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider">Status</span>
                  <p className="text-sm font-bold text-gray-800 mt-0.5 flex items-center gap-1.5">
                    {viewingUser.is_archived ? (
                      <span className="text-orange-600">Access Suspended</span>
                    ) : viewingUser.is_online ? (
                      <span className="text-emerald-600 flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        Active Now
                      </span>
                    ) : (
                      <span className="text-gray-600">Offline</span>
                    )}
                  </p>
                </div>
              </div>

              {viewingUser.phone && (
                <div className="p-3.5 bg-gray-50/80 rounded-2xl border border-gray-100 flex items-center gap-3">
                  <Phone size={16} className="text-gray-400" />
                  <div>
                    <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider block">Phone</span>
                    <span className="text-xs font-semibold text-gray-800">{viewingUser.phone}</span>
                  </div>
                </div>
              )}

              {viewingUser.location && (
                <div className="p-3.5 bg-gray-50/80 rounded-2xl border border-gray-100 flex items-center gap-3">
                  <MapPin size={16} className="text-gray-400" />
                  <div>
                    <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider block">Location</span>
                    <span className="text-xs font-semibold text-gray-800">{viewingUser.location}</span>
                  </div>
                </div>
              )}

              {viewingUser.bio && (
                <div className="p-3.5 bg-gray-50/80 rounded-2xl border border-gray-100">
                  <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider block mb-1">Biography / Notes</span>
                  <p className="text-xs text-gray-600 leading-relaxed font-medium">{viewingUser.bio}</p>
                </div>
              )}

              <div className="p-3.5 bg-gray-50/80 rounded-2xl border border-gray-100 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-black uppercase text-gray-400 tracking-wider block">Last Platform Activity</span>
                  <span className="text-xs font-semibold text-gray-800">
                    {viewingUser.last_active ? new Date(viewingUser.last_active).toLocaleString() : 'Never logged in'}
                  </span>
                </div>
                <Clock size={16} className="text-gray-400" />
              </div>
            </div>

            {/* Quick Actions inside modal */}
            <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
              <button
                type="button"
                onClick={() => {
                  const target = viewingUser;
                  setViewingUser(null);
                  openEditModal(target);
                }}
                className="flex-1 py-2.5 px-4 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-bold transition-colors flex items-center justify-center gap-2 cursor-pointer"
              >
                <Edit size={14} />
                Edit Account
              </button>

              {viewingUser.email !== currentUserEmail && (
                <>
                  {viewingUser.is_archived ? (
                    <button
                      type="button"
                      onClick={() => handleUnarchiveConfirm(viewingUser)}
                      className="py-2.5 px-4 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-bold transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <RotateCcw size={14} />
                      Restore
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleArchiveConfirm(viewingUser)}
                      className="py-2.5 px-4 rounded-xl bg-orange-50 hover:bg-orange-100 text-orange-700 text-xs font-bold transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Archive size={14} />
                      Suspend
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => handleDeleteConfirm(viewingUser)}
                    className="p-2.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 text-xs font-bold transition-colors cursor-pointer"
                    title="Delete Permanently"
                  >
                    <Trash2 size={16} />
                  </button>
                </>
              )}
            </div>

          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {confirmModal.isOpen && (
        <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-7 w-full max-w-md shadow-2xl border border-gray-100 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3.5 mb-4">
              <div className="p-3 bg-gray-50 rounded-2xl shrink-0">
                {confirmModal.icon || <AlertTriangle className="text-orange-500" size={24} />}
              </div>
              <div>
                <h3 className="text-lg font-extrabold text-gray-900">{confirmModal.title}</h3>
                <p className="text-xs text-gray-400 font-medium">Please review carefully</p>
              </div>
            </div>

            <p className="text-xs sm:text-sm text-gray-600 leading-relaxed font-medium mb-6">
              {confirmModal.message}
            </p>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
                className="flex-1 py-3 px-4 rounded-xl border border-gray-200 text-gray-700 hover:bg-gray-50 text-xs font-bold transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  const fn = confirmModal.onConfirm;
                  setConfirmModal(prev => ({ ...prev, isOpen: false }));
                  if (fn) await fn();
                }}
                className={`flex-1 py-3 px-4 rounded-xl text-white text-xs font-bold transition-all shadow-md cursor-pointer ${
                  confirmModal.confirmType === 'danger'
                    ? 'bg-red-600 hover:bg-red-700 shadow-red-500/20'
                    : confirmModal.confirmType === 'warning'
                    ? 'bg-orange-500 hover:bg-orange-600 shadow-orange-500/20'
                    : 'bg-[#D10043] hover:bg-[#b00038] shadow-[#D10043]/20'
                }`}
              >
                {confirmModal.confirmText}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Provision Account Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 w-full max-w-md shadow-2xl relative border border-gray-100 animate-in fade-in zoom-in-95 duration-150">
            <button 
              onClick={() => setIsCreateModalOpen(false)}
              className="absolute top-5 right-5 w-8 h-8 flex items-center justify-center rounded-full bg-gray-50 text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer"
            >
              <X size={18} />
            </button>
            
            <div className="mb-6">
              <div className="w-12 h-12 bg-red-50 rounded-2xl flex items-center justify-center mb-3 text-[#D10043]">
                <UserPlus size={22} />
              </div>
              <h3 className="text-xl font-extrabold text-gray-900">Provision User Account</h3>
              <p className="text-xs text-gray-500 font-medium mt-1">Configure credentials and grant operational access.</p>
            </div>
            
            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">Full Name</label>
                <input 
                  type="text" required
                  value={formData.fullname}
                  onChange={(e) => setFormData({...formData, fullname: e.target.value})}
                  className="w-full bg-gray-50/80 border border-gray-200 rounded-xl px-4 py-2.5 text-sm font-medium focus:bg-white focus:ring-3 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all outline-none"
                  placeholder="e.g. Sarah Jenkins"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">Email Address</label>
                <input 
                  type="email" required
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full bg-gray-50/80 border border-gray-200 rounded-xl px-4 py-2.5 text-sm font-medium focus:bg-white focus:ring-3 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all outline-none"
                  placeholder="sarah@company.com"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">Initial Password</label>
                <div className="relative">
                  <input 
                    type={showPassword ? "text" : "password"} required
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    className="w-full bg-gray-50/80 border border-gray-200 rounded-xl px-4 py-2.5 pr-10 text-sm font-medium focus:bg-white focus:ring-3 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all outline-none"
                    placeholder="Minimum 8 characters"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(prev => !prev)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 cursor-pointer"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">Access Role</label>
                <div className="relative">
                  <select 
                    value={formData.role}
                    onChange={(e) => setFormData({...formData, role: e.target.value})}
                    className="w-full bg-gray-50/80 border border-gray-200 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 focus:bg-white focus:ring-3 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all outline-none appearance-none cursor-pointer"
                  >
                    <option value="HR">HR Specialist — Candidates, Screening & Scheduling</option>
                    <option value="ADMIN">System Administrator — Full Platform Controls</option>
                    <option value="CANDIDATE">Candidate — Career Portal & Applications</option>
                  </select>
                  <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
                </div>
              </div>
              
              <div className="pt-3">
                <button 
                  type="submit" 
                  disabled={formSubmitting}
                  className="w-full bg-gradient-to-r from-[#D10043] to-[#B00038] text-white py-3 rounded-xl text-sm font-bold hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 transition-all shadow-md shadow-red-500/20 cursor-pointer"
                >
                  {formSubmitting ? 'Creating Account...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {isEditModalOpen && (
        <div className="fixed inset-0 bg-gray-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-6 sm:p-8 w-full max-w-md shadow-2xl relative border border-gray-100 animate-in fade-in zoom-in-95 duration-150">
            <button 
              onClick={() => setIsEditModalOpen(false)}
              className="absolute top-5 right-5 w-8 h-8 flex items-center justify-center rounded-full bg-gray-50 text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer"
            >
              <X size={18} />
            </button>
            
            <div className="mb-6">
              <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center mb-3 text-indigo-600">
                <Edit size={22} />
              </div>
              <h3 className="text-xl font-extrabold text-gray-900">Update User Account</h3>
              <p className="text-xs text-gray-500 font-medium mt-1">Modify profile details, role, or reset password.</p>
            </div>
            
            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">Full Name</label>
                <input 
                  type="text" required
                  value={formData.fullname}
                  onChange={(e) => setFormData({...formData, fullname: e.target.value})}
                  className="w-full bg-gray-50/80 border border-gray-200 rounded-xl px-4 py-2.5 text-sm font-medium focus:bg-white focus:ring-3 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">Email Address</label>
                <input 
                  type="email" required
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full bg-gray-50/80 border border-gray-200 rounded-xl px-4 py-2.5 text-sm font-medium focus:bg-white focus:ring-3 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all outline-none"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="block text-xs font-bold text-gray-700">New Password</label>
                  <span className="text-[10px] font-bold text-gray-400">Leave empty to keep existing</span>
                </div>
                <div className="relative">
                  <input 
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    className="w-full bg-gray-50/80 border border-gray-200 rounded-xl px-4 py-2.5 pr-10 text-sm font-medium focus:bg-white focus:ring-3 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all outline-none"
                    placeholder="Enter new password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(prev => !prev)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 cursor-pointer"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">Access Role</label>
                <div className="relative">
                  <select 
                    value={formData.role}
                    onChange={(e) => setFormData({...formData, role: e.target.value})}
                    className="w-full bg-gray-50/80 border border-gray-200 rounded-xl px-4 py-2.5 text-sm font-bold text-gray-900 focus:bg-white focus:ring-3 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all outline-none appearance-none cursor-pointer"
                  >
                    <option value="HR">HR Specialist</option>
                    <option value="ADMIN">System Administrator</option>
                    <option value="CANDIDATE">Candidate</option>
                  </select>
                  <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
                </div>
              </div>
              
              <div className="pt-3">
                <button 
                  type="submit" 
                  disabled={formSubmitting}
                  className="w-full bg-gray-900 hover:bg-black text-white py-3 rounded-xl text-sm font-bold hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 transition-all shadow-md cursor-pointer"
                >
                  {formSubmitting ? 'Saving Changes...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

export default UsersPage;