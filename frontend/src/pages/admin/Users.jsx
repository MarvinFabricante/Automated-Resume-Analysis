import React, { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  Search, 
  UserPlus, 
  MoreHorizontal, 
  Mail, 
  Shield, 
  UserCheck, 
  UserX, 
  ChevronLeft, 
  ChevronRight,
  Clock,
  Archive,
  RotateCcw,
  Activity,
  X, 
  Trash2, 
  Edit,
  ShieldCheck,
  User,
  Zap
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
  const { data: users = [], isLoading } = useGetUsersQuery();
  const [archiveUser] = useArchiveUserMutation();
  const [unarchiveUser] = useUnarchiveUserMutation();
  const [createUser] = useCreateUserMutation();
  const [updateUser] = useUpdateUserMutation();
  const [deleteUser] = useDeleteUserMutation();
  const currentUserEmail = useSelector((state) => state.auth.user);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [activeMenu, setActiveMenu] = useState(null);
  
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editUserData, setEditUserData] = useState(null);

  const [formData, setFormData] = useState({ fullname: '', email: '', role: 'HR', password: '' });
  
  const [changeUserRole] = useChangeUserRoleMutation();

  const filteredUsers = users.filter(user => 
    user.fullname?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.email?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleArchive = async (userId) => {
    if (window.confirm("Are you sure you want to archive this user? They will no longer be able to log in.")) {
      await archiveUser(userId);
      setActiveMenu(null);
    }
  };

  const handleUnarchive = async (userId) => {
    await unarchiveUser(userId);
    setActiveMenu(null);
  };

  const handleRoleChange = async (userId, newRole) => {
    if (window.confirm(`Are you sure you want to change this user's role to ${newRole}?`)) {
      await changeUserRole({ userId, role: newRole });
      setActiveMenu(null);
    }
  };

  const handleDelete = async (userId) => {
    if (window.confirm("Are you sure you want to permanently delete this user? This action cannot be undone.")) {
      await deleteUser(userId);
      setActiveMenu(null);
    }
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    try {
      await createUser(formData).unwrap();
      setIsCreateModalOpen(false);
      setFormData({ fullname: '', email: '', role: 'HR', password: '' });
    } catch (err) {
      alert(err.data?.detail || 'Failed to create user');
    }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    try {
      const updateData = { ...formData };
      if (!updateData.password) {
        delete updateData.password;
      }
      await updateUser({ userId: editUserData.id, body: updateData }).unwrap();
      setIsEditModalOpen(false);
      setEditUserData(null);
    } catch (err) {
      alert(err.data?.detail || 'Failed to update user');
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
    setIsEditModalOpen(true);
    setActiveMenu(null);
  };

  return (
    <div className="bg-[#FAFAFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col relative overflow-hidden">
      {/* Decorative background elements */}
      <div className="absolute top-0 left-0 w-full h-[300px] bg-gradient-to-b from-[#D10043]/5 to-transparent pointer-events-none z-0"></div>
      
      <Helmet>
        <title>Admin Portal - User Management</title>
      </Helmet>
      
      <Header />
      
      <div className="flex flex-1 z-10 relative">
        <Sidebar />
        <main className="flex-1 max-w-[1400px] mx-auto px-6 sm:px-10 py-10 w-full">

          <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end mb-10 gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-gray-100 shadow-sm text-xs font-bold text-gray-500 mb-3 tracking-wide">
                <ShieldCheck size={14} className="text-[#D10043]" />
                ADMINISTRATION MODULE
              </div>
              <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900 bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600">
                User Management
              </h2>
              <p className="text-sm text-gray-500 font-medium tracking-wide mt-2 max-w-xl">
                Oversee platform access, configure role-based permissions, and manage the security posture of your organization's user accounts.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3 w-full lg:w-auto shrink-0">
              <div className="relative flex-1 sm:w-72 group">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-[#D10043] transition-colors duration-300" size={18} />
                <input 
                  type="text" 
                  placeholder="Search by name, email, or role..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-white/80 backdrop-blur-sm border border-gray-200 hover:border-gray-300 rounded-2xl py-3 pl-11 pr-4 text-sm font-medium focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all outline-none shadow-sm"
                />
              </div>
              <button 
                onClick={() => {
                  setFormData({ fullname: '', email: '', role: 'HR', password: '' });
                  setIsCreateModalOpen(true);
                }}
                className="bg-gradient-to-r from-[#D10043] to-[#B00038] text-white px-6 py-3 rounded-2xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 text-sm font-bold tracking-tight flex items-center justify-center shadow-lg shadow-red-500/25 group"
              >
                <UserPlus className="h-4 w-4 mr-2 group-hover:animate-bounce" />
                Create Account
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
            
            <div className="xl:col-span-3 flex flex-col h-full">
              <div className="bg-white/80 backdrop-blur-xl border border-gray-100 rounded-[32px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-visible flex-1 flex flex-col">
                
                <div className="overflow-x-auto flex-1">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="px-8 py-6 text-[11px] font-extrabold uppercase tracking-widest text-gray-400 bg-gray-50/50 rounded-tl-[32px]">User Profile</th>
                        <th className="px-6 py-6 text-[11px] font-extrabold uppercase tracking-widest text-gray-400 bg-gray-50/50">Role & Access</th>
                        <th className="px-6 py-6 text-[11px] font-extrabold uppercase tracking-widest text-gray-400 bg-gray-50/50">Activity Status</th>
                        <th className="px-8 py-6 text-[11px] font-extrabold uppercase tracking-widest text-gray-400 bg-gray-50/50 text-right rounded-tr-[32px]">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50/80">
                      {isLoading ? (
                        <tr>
                          <td colSpan="4" className="px-8 py-20 text-center">
                            <div className="flex flex-col items-center justify-center">
                              <div className="relative w-12 h-12 mb-4">
                                <div className="absolute inset-0 border-4 border-[#D10043]/20 rounded-full"></div>
                                <div className="absolute inset-0 border-4 border-[#D10043] rounded-full border-t-transparent animate-spin"></div>
                              </div>
                              <p className="text-sm font-bold text-gray-600">Synchronizing Users...</p>
                              <p className="text-xs text-gray-400 mt-1 font-medium">Fetching the latest directory data.</p>
                            </div>
                          </td>
                        </tr>
                      ) : filteredUsers.length > 0 ? (
                        filteredUsers.map((user) => (
                          <tr key={user.id} className={`group hover:bg-gray-50/50 transition-all duration-300 ${user.is_archived ? 'opacity-50 grayscale-[50%]' : ''}`}>
                            <td className="px-8 py-5">
                              <div className="flex items-center gap-4">
                                <div className={`relative w-11 h-11 rounded-[14px] flex items-center justify-center overflow-hidden border shadow-sm transition-transform group-hover:scale-105 duration-300 ${!user.profile_image_url ? (user.is_archived ? 'bg-gray-100 border-gray-200 text-gray-400' : 'bg-gradient-to-br from-red-50 to-pink-50 border-red-100 text-[#D10043]') : 'border-gray-200'}`}>
                                  {user.profile_image_url ? (
                                    <img src={user.profile_image_url} alt={user.fullname} className="w-full h-full object-cover" />
                                  ) : (
                                    <span className="font-extrabold text-sm">{user.fullname?.charAt(0) || 'U'}</span>
                                  )}
                                  {user.is_online && !user.is_archived && (
                                    <span className="absolute -bottom-1 -right-1 w-3.5 h-3.5 bg-emerald-500 border-2 border-white rounded-full z-10 shadow-sm"></span>
                                  )}
                                </div>
                                <div className="flex flex-col">
                                  <div className="flex items-center gap-2">
                                    <p className="text-sm font-bold text-gray-900 leading-none group-hover:text-[#D10043] transition-colors">{user.fullname}</p>
                                    {user.is_archived && <span className="text-[9px] font-black bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded uppercase tracking-wider">Archived</span>}
                                  </div>
                                  <p className="text-xs text-gray-500 font-medium mt-1 flex items-center gap-1.5 group-hover:text-gray-600 transition-colors">
                                    <Mail size={12} className="opacity-70" /> {user.email}
                                  </p>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-5">
                              <div className="flex flex-col items-start gap-1.5">
                                <span className={`inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-lg ${
                                  user.role === 'ADMIN' ? 'bg-purple-50 text-purple-700 border border-purple-100/50' :
                                  user.role === 'HR' ? 'bg-blue-50 text-blue-700 border border-blue-100/50' :
                                  'bg-orange-50 text-orange-700 border border-orange-100/50'
                                }`}>
                                  {user.role === 'ADMIN' ? <ShieldCheck size={14} /> : user.role === 'HR' ? <UserCheck size={14} /> : <User size={14} />}
                                  {user.role}
                                </span>
                                <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest pl-1">
                                  {user.role === 'ADMIN' ? 'System Owner' : user.role === 'HR' ? 'Management Level' : 'Standard User'}
                                </p>
                              </div>
                            </td>
                            <td className="px-6 py-5">
                              <div className="flex flex-col gap-1.5">
                                {user.is_online && !user.is_archived ? (
                                  <span className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100/50 w-fit">
                                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
                                    Active Now
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-lg bg-gray-50 text-gray-500 border border-gray-200/50 w-fit">
                                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full"></div>
                                    Offline
                                  </span>
                                )}
                                {user.last_active && (
                                  <p className="text-[10px] text-gray-400 flex items-center gap-1.5 font-medium pl-1">
                                    <Clock size={10} className="opacity-70" /> {new Date(user.last_active).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                  </p>
                                )}
                              </div>
                            </td>
                            <td className="px-8 py-5 text-right relative">
                              {user.email !== currentUserEmail ? (
                                <>
                                  <button 
                                    onClick={() => setActiveMenu(activeMenu === user.id ? null : user.id)}
                                    className={`p-2 rounded-xl transition-all duration-200 ${activeMenu === user.id ? 'bg-gray-100 text-gray-900 shadow-inner' : 'text-gray-400 hover:bg-white hover:shadow-md hover:text-gray-700 border border-transparent hover:border-gray-200'}`}
                                  >
                                    <MoreHorizontal size={18} />
                                  </button>
                                  
                                  {activeMenu === user.id && (
                                    <div className="absolute right-8 top-16 w-52 bg-white/95 backdrop-blur-xl border border-gray-100 rounded-2xl shadow-[0_10px_40px_rgb(0,0,0,0.08)] z-50 py-2 overflow-hidden animate-in fade-in slide-in-from-top-2 zoom-in-95 duration-200">
                                        <div className="px-4 py-2 border-b border-gray-50 mb-1">
                                          <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">User Actions</p>
                                        </div>
                                        <button 
                                          onClick={() => openEditModal(user)}
                                          className="w-full px-4 py-2.5 text-left text-xs font-bold text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition-colors"
                                        >
                                          <Edit size={14} className="text-gray-400" /> Edit Details
                                        </button>
                                        
                                        <div className="border-t border-gray-50 my-1"></div>
                                        <div className="px-4 py-1.5 text-[10px] font-black text-gray-400 uppercase tracking-widest mt-1">Role Assignment</div>
                                        <div className="px-2">
                                          {['ADMIN', 'HR', 'CANDIDATE'].map((role) => (
                                            user.role !== role && (
                                              <button 
                                                key={role}
                                                onClick={() => handleRoleChange(user.id, role)}
                                                className="w-full px-3 py-2 text-left text-xs font-bold text-gray-600 hover:bg-[#D10043]/5 hover:text-[#D10043] rounded-lg flex items-center justify-between transition-colors group"
                                              >
                                                Make {role}
                                                <ChevronRight size={12} className="opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300" />
                                              </button>
                                            )
                                          ))}
                                        </div>

                                        <div className="border-t border-gray-50 my-2"></div>
                                        {user.is_archived ? (
                                        <button 
                                          onClick={() => handleUnarchive(user.id)}
                                          className="w-full px-4 py-2.5 text-left text-xs font-bold text-emerald-600 hover:bg-emerald-50 flex items-center gap-3 transition-colors"
                                        >
                                          <RotateCcw size={14} className="text-emerald-500" /> Restore Account
                                        </button>
                                      ) : (
                                        <button 
                                          onClick={() => handleArchive(user.id)}
                                          className="w-full px-4 py-2.5 text-left text-xs font-bold text-orange-600 hover:bg-orange-50 flex items-center gap-3 transition-colors"
                                        >
                                          <Archive size={14} className="text-orange-500" /> Suspend Access
                                        </button>
                                      )}
                                      <div className="border-t border-gray-50 my-1"></div>
                                      <button 
                                        onClick={() => handleDelete(user.id)}
                                        className="w-full px-4 py-2.5 text-left text-xs font-bold text-red-600 hover:bg-red-50 flex items-center gap-3 transition-colors"
                                      >
                                        <Trash2 size={14} className="text-red-500" /> Delete Permanently
                                      </button>
                                    </div>
                                  )}
                                </>
                              ) : (
                                <span className="inline-flex items-center justify-center px-3 py-1.5 rounded-lg bg-gray-50 border border-gray-100 text-[10px] font-bold text-gray-400 uppercase tracking-widest whitespace-nowrap">
                                  Current User
                                </span>
                              )}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="4" className="px-8 py-20 text-center">
                            <div className="flex flex-col items-center justify-center max-w-sm mx-auto">
                              <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
                                <Search size={24} className="text-gray-300" />
                              </div>
                              <p className="text-base font-bold text-gray-900">No users found</p>
                              <p className="text-sm text-gray-500 mt-2 text-center leading-relaxed">
                                We couldn't find any user matching <span className="font-bold text-gray-700">"{searchQuery}"</span>. Try adjusting your search term.
                              </p>
                              <button 
                                onClick={() => setSearchQuery("")}
                                className="mt-6 px-4 py-2 bg-white border border-gray-200 rounded-xl text-xs font-bold text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors shadow-sm"
                              >
                                Clear Search
                              </button>
                            </div>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                
                <div className="p-5 border-t border-gray-100 bg-gray-50/50 rounded-b-[32px] flex items-center justify-between mt-auto">
                  <div className="flex items-center gap-2">
                    <p className="text-xs font-bold text-gray-500">
                      Showing <span className="text-gray-900 font-extrabold">{filteredUsers.length}</span> out of <span className="text-gray-900 font-extrabold">{users.length}</span> members
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button className="p-2 bg-white border border-gray-200 rounded-xl text-gray-400 hover:text-gray-900 hover:border-gray-300 shadow-sm transition-all hover:-translate-x-0.5"><ChevronLeft size={16} /></button>
                    <button className="p-2 bg-white border border-gray-200 rounded-xl text-gray-400 hover:text-gray-900 hover:border-gray-300 shadow-sm transition-all hover:translate-x-0.5"><ChevronRight size={16} /></button>
                  </div>
                </div>

              </div>
            </div>

            <div className="xl:col-span-1 space-y-6">
              
              <div className="bg-white/80 backdrop-blur-xl border border-gray-100 rounded-[32px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-pink-100/50 to-transparent rounded-bl-full pointer-events-none transition-transform duration-700 group-hover:scale-110"></div>
                
                <h4 className="font-extrabold text-gray-900 mb-6 flex items-center gap-2.5 text-lg relative z-10">
                  <div className="p-2 bg-pink-50 rounded-xl text-[#D10043]">
                    <Activity size={18} />
                  </div>
                  Directory Insights
                </h4>
                
                <div className="space-y-6 relative z-10">
                  <div className="flex items-center justify-between p-4 rounded-2xl bg-gray-50/80 border border-gray-100 hover:border-gray-200 transition-colors">
                    <div className="flex flex-col">
                      <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Total Members</p>
                      <p className="text-3xl font-extrabold text-gray-900">{users.length}</p>
                    </div>
                    <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm">
                      <UserCheck className="text-emerald-500" size={20} />
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between p-4 rounded-2xl bg-gray-50/80 border border-gray-100 hover:border-gray-200 transition-colors">
                    <div className="flex flex-col">
                      <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Suspended / Archived</p>
                      <p className="text-3xl font-extrabold text-gray-900">{users.filter(u => u.is_archived).length}</p>
                    </div>
                    <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm">
                      <UserX className="text-orange-400" size={20} />
                    </div>
                  </div>
                  
                  <div className="p-5 bg-gradient-to-br from-red-50 to-pink-50/30 rounded-2xl border border-red-100/60 shadow-inner">
                     <p className="text-xs font-bold text-[#D10043] flex items-center gap-2 mb-2">
                       <Shield size={14} /> Security Recommendation
                     </p>
                     <p className="text-xs text-gray-600 leading-relaxed font-medium">
                       Routinely audit elevated permissions. Archiving dormant accounts enhances system security and data hygiene.
                     </p>
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-[32px] p-8 text-white relative overflow-hidden group shadow-xl">
                <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-[#D10043]/30 to-transparent rounded-full blur-3xl pointer-events-none group-hover:opacity-100 group-hover:scale-125 transition-all duration-1000 opacity-60"></div>
                <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-blue-500/20 rounded-full blur-3xl pointer-events-none"></div>
                
                <div className="relative z-10">
                  <div className="w-12 h-12 bg-white/10 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6 shadow-inner border border-white/10">
                    <Zap className="text-yellow-400" size={24} />
                  </div>
                  <h4 className="text-xl font-extrabold mb-3 text-white tracking-tight">Access Control Audit</h4>
                  <p className="text-gray-300 text-sm leading-relaxed mb-8 font-medium">
                    Initiate a comprehensive system review to validate role assignments and identify anomalous permission structures.
                  </p>
                  <button className="w-full bg-white text-gray-900 hover:bg-gray-100 py-3.5 rounded-xl text-sm font-bold transition-all shadow-lg hover:shadow-xl active:scale-95 flex items-center justify-center gap-2">
                    Execute Bulk Audit
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
              
            </div>

          </div>
        </main>
      </div>

      {/* Create Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-md z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded-[32px] p-8 w-full max-w-md shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button 
              onClick={() => setIsCreateModalOpen(false)}
              className="absolute top-6 right-6 w-8 h-8 flex items-center justify-center rounded-full bg-gray-50 text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <X size={18} />
            </button>
            
            <div className="mb-8">
              <div className="w-12 h-12 bg-pink-50 rounded-2xl flex items-center justify-center mb-4 text-[#D10043]">
                <UserPlus size={24} />
              </div>
              <h3 className="text-2xl font-extrabold text-gray-900">New Account</h3>
              <p className="text-sm text-gray-500 font-medium mt-1">Provision a new user and assign permissions.</p>
            </div>
            
            <form onSubmit={handleCreateSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-2">Full Name</label>
                <input 
                  type="text" required
                  value={formData.fullname}
                  onChange={(e) => setFormData({...formData, fullname: e.target.value})}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-sm font-medium focus:bg-white focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all outline-none"
                  placeholder="e.g. Jane Doe"
                />
              </div>
              <div>
                <label className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-2">Email Address</label>
                <input 
                  type="email" required
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-sm font-medium focus:bg-white focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all outline-none"
                  placeholder="name@company.com"
                />
              </div>
              <div>
                <label className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-2">Initial Password</label>
                <input 
                  type="password" required
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-sm font-medium focus:bg-white focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all outline-none"
                  placeholder="Min. 8 characters"
                />
              </div>
              <div>
                <label className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-2">Access Role</label>
                <div className="relative">
                  <select 
                    value={formData.role}
                    onChange={(e) => setFormData({...formData, role: e.target.value})}
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-sm font-bold text-gray-900 focus:bg-white focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all outline-none appearance-none"
                  >
                    <option value="HR">HR Professional</option>
                    <option value="ADMIN">System Administrator</option>
                    <option value="CANDIDATE">Candidate</option>
                  </select>
                  <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
                </div>
              </div>
              
              <div className="pt-2">
                <button 
                  type="submit" 
                  className="w-full bg-gradient-to-r from-[#D10043] to-[#B00038] text-white py-4 rounded-xl text-sm font-bold hover:scale-[1.02] active:scale-[0.98] transition-all shadow-lg shadow-red-500/25"
                >
                  Provision Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isEditModalOpen && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-md z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded-[32px] p-8 w-full max-w-md shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button 
              onClick={() => setIsEditModalOpen(false)}
              className="absolute top-6 right-6 w-8 h-8 flex items-center justify-center rounded-full bg-gray-50 text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
            >
              <X size={18} />
            </button>
            
            <div className="mb-8">
              <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center mb-4 text-blue-500">
                <Edit size={24} />
              </div>
              <h3 className="text-2xl font-extrabold text-gray-900">Modify Account</h3>
              <p className="text-sm text-gray-500 font-medium mt-1">Update profile details and access rights.</p>
            </div>
            
            <form onSubmit={handleEditSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-2">Full Name</label>
                <input 
                  type="text" required
                  value={formData.fullname}
                  onChange={(e) => setFormData({...formData, fullname: e.target.value})}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-sm font-medium focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-2">Email Address</label>
                <input 
                  type="email" required
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-sm font-medium focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all outline-none"
                />
              </div>
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-xs font-black text-gray-500 uppercase tracking-widest">New Password</label>
                  <span className="text-[10px] font-bold text-gray-400">Optional</span>
                </div>
                <input 
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-sm font-medium focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all outline-none"
                  placeholder="Leave blank to preserve current"
                />
              </div>
              <div>
                <label className="block text-xs font-black text-gray-500 uppercase tracking-widest mb-2">Access Role</label>
                <div className="relative">
                  <select 
                    value={formData.role}
                    onChange={(e) => setFormData({...formData, role: e.target.value})}
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-sm font-bold text-gray-900 focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all outline-none appearance-none"
                  >
                    <option value="HR">HR Professional</option>
                    <option value="ADMIN">System Administrator</option>
                    <option value="CANDIDATE">Candidate</option>
                  </select>
                  <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
                </div>
              </div>
              
              <div className="pt-2">
                <button 
                  type="submit" 
                  className="w-full bg-gray-900 text-white py-4 rounded-xl text-sm font-bold hover:bg-black hover:scale-[1.02] active:scale-[0.98] transition-all shadow-lg shadow-gray-900/20"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

// Simple ChevronDown icon since it wasn't imported from lucide-react in original
const ChevronDown = ({ className, size }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
);

export default UsersPage;