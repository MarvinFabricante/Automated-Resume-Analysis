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
  Settings2,
  Clock,
  Archive,
  RotateCcw,
  Activity
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { X, Trash2, Edit } from 'lucide-react';
import { 
  useGetUsersQuery, 
  useArchiveUserMutation, 
  useUnarchiveUserMutation,
  useChangeUserRoleMutation,
  useCreateUserMutation,
  useUpdateUserMutation,
  useDeleteUserMutation
} from '../../redux/api/apiSlice';

const UsersPage = () => {
  const { data: users = [], isLoading } = useGetUsersQuery();
  const [archiveUser] = useArchiveUserMutation();
  const [unarchiveUser] = useUnarchiveUserMutation();
  const [createUser] = useCreateUserMutation();
  const [updateUser] = useUpdateUserMutation();
  const [deleteUser] = useDeleteUserMutation();
  
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
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
      <Helmet>
        <title>Admin Page - User Management</title>
      </Helmet>
      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 max-w-[1400px] mx-auto px-10 py-10">

        <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-4">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-gray-900">User Management</h2>
            <p className="text-sm text-gray-400 font-medium tracking-wide mt-1">
              Manage team access levels, permissions, and account security.
            </p>
          </div>

          <div className="flex space-x-3 w-full md:w-auto">
            <div className="relative flex-1 md:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
              <input 
                type="text" 
                placeholder="Search by name or email..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white border border-gray-200 rounded-xl py-2.5 pl-10 pr-4 text-xs focus:ring-2 focus:ring-red-100 transition-all outline-none shadow-sm"
              />
            </div>
            <button 
              onClick={() => {
                setFormData({ fullname: '', email: '', role: 'HR', password: '' });
                setIsCreateModalOpen(true);
              }}
              className="bg-[#D10043] text-white px-5 py-2.5 rounded-xl hover:bg-[#b00038] transition-all text-xs font-bold tracking-tight flex items-center justify-center shadow-lg shadow-red-100"
            >
              <UserPlus className="h-4 w-4 mr-2" />
              Create Account
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

          <div className="lg:col-span-3">
            <div className="bg-white border border-gray-100 rounded-[32px] shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-gray-50 uppercase text-[10px] tracking-[0.1em] text-gray-400 font-bold bg-gray-50/30">
                      <th className="px-8 py-5">User Profile</th>
                      <th className="px-6 py-5">Role & Access</th>
                      <th className="px-6 py-5">Account Status</th>
                      <th className="px-6 py-5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {isLoading ? (
                      <tr>
                        <td colSpan="4" className="px-8 py-12 text-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#D10043] mx-auto mb-4"></div>
                          <p className="text-sm text-gray-400 font-bold">Loading users...</p>
                        </td>
                      </tr>
                    ) : filteredUsers.map((user) => (
                      <tr key={user.id} className={`group hover:bg-gray-50/50 transition-colors ${user.is_archived ? 'opacity-60' : ''}`}>
                        <td className="px-8 py-6">
                          <div className="flex items-center gap-4">
                            <div className={`relative w-10 h-10 rounded-2xl flex items-center justify-center overflow-hidden border border-gray-100 ${!user.profile_image_url ? (user.is_archived ? 'bg-gray-100 text-gray-400' : 'bg-[#D10043]/10 text-[#D10043]') : ''}`}>
                              {user.profile_image_url ? (
                                <img src={user.profile_image_url} alt={user.fullname} className="w-full h-full object-cover" />
                              ) : (
                                <span className="font-bold text-sm">{user.fullname?.charAt(0) || 'U'}</span>
                              )}
                              {user.is_online && !user.is_archived && (
                                <span className="absolute -top-1 -right-1 w-3 h-3 bg-emerald-500 border-2 border-white rounded-full"></span>
                              )}
                            </div>
                            <div>
                              <p className="text-sm font-bold text-gray-900">{user.fullname} {user.is_archived && <span className="text-[10px] bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded ml-1">ARCHIVED</span>}</p>
                              <p className="text-[11px] text-gray-400 font-medium flex items-center gap-1.5">
                                <Mail size={12} /> {user.email}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-6">
                          <div className="flex flex-col gap-1">
                            <div className="flex items-center gap-2">
                              <Shield size={14} className={user.is_archived ? 'text-gray-400' : 'text-[#D10043]'} />
                              <span className="text-xs font-semibold text-gray-700">{user.role}</span>
                            </div>
                            <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Level 4 Access</p>
                          </div>
                        </td>
                        <td className="px-6 py-6">
                          <div className="flex flex-col gap-1.5">
                            {user.is_online && !user.is_archived ? (
                              <span className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 w-fit">
                                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
                                ONLINE NOW
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full bg-gray-50 text-gray-400 w-fit">
                                OFFLINE
                              </span>
                            )}
                            {user.last_active && (
                              <p className="text-[10px] text-gray-400 flex items-center gap-1">
                                <Clock size={10} /> {new Date(user.last_active).toLocaleDateString()}
                              </p>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-6 text-right relative">
                          <button 
                            onClick={() => setActiveMenu(activeMenu === user.id ? null : user.id)}
                            className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 transition-colors"
                          >
                            <MoreHorizontal size={18} />
                          </button>
                          
                          {activeMenu === user.id && (
                            <div className="absolute right-8 top-16 w-48 bg-white border border-gray-100 rounded-2xl shadow-xl z-20 py-2 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                                <button 
                                  onClick={() => openEditModal(user)}
                                  className="w-full px-4 py-2 text-left text-xs font-bold text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                                >
                                  <Edit size={14} /> Edit Account
                                </button>
                                <div className="border-t border-gray-100 my-1"></div>
                                <div className="px-4 py-1 text-[10px] font-bold text-gray-400 uppercase">Change Role</div>
                                {['ADMIN', 'HR', 'CANDIDATE'].map((role) => (
                                  user.role !== role && (
                                    <button 
                                      key={role}
                                      onClick={() => handleRoleChange(user.id, role)}
                                      className="w-full px-4 py-1.5 text-left text-[11px] font-semibold text-gray-600 hover:bg-gray-50 hover:text-[#D10043] flex items-center gap-2"
                                    >
                                      Make {role}
                                    </button>
                                  )
                                ))}
                                <div className="border-t border-gray-100 my-1"></div>
                                {user.is_archived ? (
                                <button 
                                  onClick={() => handleUnarchive(user.id)}
                                  className="w-full px-4 py-2 text-left text-xs font-bold text-emerald-600 hover:bg-emerald-50 flex items-center gap-2"
                                >
                                  <RotateCcw size={14} /> Unarchive User
                                </button>
                              ) : (
                                <button 
                                  onClick={() => handleArchive(user.id)}
                                  className="w-full px-4 py-2 text-left text-xs font-bold text-red-600 hover:bg-red-50 flex items-center gap-2"
                                >
                                  <Archive size={14} /> Archive User
                                </button>
                              )}
                              <div className="border-t border-gray-100 my-1"></div>
                              <button 
                                onClick={() => handleDelete(user.id)}
                                className="w-full px-4 py-2 text-left text-xs font-bold text-red-600 hover:bg-red-50 flex items-center gap-2"
                              >
                                <Trash2 size={14} /> Remove Account
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                    {!isLoading && filteredUsers.length === 0 && (
                      <tr>
                        <td colSpan="4" className="px-8 py-12 text-center text-gray-400 font-medium">
                          No users matching "{searchQuery}" found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              
              <div className="p-6 border-t border-gray-50 flex items-center justify-between">
                <div className="flex gap-2">
                  <button className="p-2 border border-gray-100 rounded-lg text-gray-400 hover:bg-gray-50"><ChevronLeft size={18} /></button>
                  <button className="p-2 border border-gray-100 rounded-lg text-gray-400 hover:bg-gray-50"><ChevronRight size={18} /></button>
                </div>
                <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Showing {filteredUsers.length} Users</p>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white border border-gray-100 rounded-[32px] p-8 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-6 flex items-center gap-2">
                <Activity size={18} className="text-[#D10043]" /> User Insights
              </h4>
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Total Members</p>
                    <p className="text-xl font-bold text-gray-900">{users.length}</p>
                  </div>
                  <UserCheck className="text-emerald-500 opacity-20" size={32} />
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Archived</p>
                    <p className="text-xl font-bold text-gray-900">{users.filter(u => u.is_archived).length}</p>
                  </div>
                  <UserX className="text-red-500 opacity-20" size={32} />
                </div>
                <hr className="border-gray-50" />
                <div className="p-4 bg-red-50/50 rounded-2xl border border-red-100/50">
                   <p className="text-[11px] font-bold text-[#D10043] flex items-center gap-2 mb-1">
                     <Shield size={12} /> Security Tip
                   </p>
                   <p className="text-[10px] text-gray-600 leading-relaxed font-medium">
                     Archive users who are no longer part of the team to maintain security hygiene.
                   </p>
                </div>
              </div>
            </div>

            <div className="bg-[#111] rounded-[32px] p-8 text-white relative overflow-hidden group shadow-xl">
              <div className="relative z-10">
                <h4 className="text-lg font-bold mb-2">Access Reviews</h4>
                <p className="text-gray-400 text-xs leading-relaxed mb-6">
                  Perform a bulk audit of user roles and system permissions.
                </p>
                <button className="w-full bg-[#D10043] hover:bg-[#b00038] py-3 rounded-xl text-xs font-bold transition-all shadow-lg shadow-red-900/20">
                  Start Audit Trail
                </button>
              </div>
              <div className="absolute -right-10 -bottom-10 w-32 h-32 bg-[#D10043] rounded-full blur-[80px] opacity-20 group-hover:opacity-40 transition-opacity"></div>
            </div>
          </div>

        </div>
        </main>
      </div>

      {/* Create Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button 
              onClick={() => setIsCreateModalOpen(false)}
              className="absolute top-6 right-6 text-gray-400 hover:text-gray-600"
            >
              <X size={20} />
            </button>
            <h3 className="text-xl font-bold text-gray-900 mb-6">Create New Account</h3>
            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Full Name</label>
                <input 
                  type="text" required
                  value={formData.fullname}
                  onChange={(e) => setFormData({...formData, fullname: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-red-100 outline-none"
                  placeholder="John Doe"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Email</label>
                <input 
                  type="email" required
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-red-100 outline-none"
                  placeholder="john@example.com"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Password</label>
                <input 
                  type="password" required
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-red-100 outline-none"
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Role</label>
                <select 
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-red-100 outline-none"
                >
                  <option value="HR">HR</option>
                  <option value="ADMIN">Admin</option>
                  <option value="CANDIDATE">Candidate</option>
                </select>
              </div>
              <button 
                type="submit" 
                className="w-full bg-[#D10043] text-white py-3 rounded-xl font-bold hover:bg-[#b00038] transition-colors mt-6 shadow-lg shadow-red-100"
              >
                Create Account
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isEditModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button 
              onClick={() => setIsEditModalOpen(false)}
              className="absolute top-6 right-6 text-gray-400 hover:text-gray-600"
            >
              <X size={20} />
            </button>
            <h3 className="text-xl font-bold text-gray-900 mb-6">Edit Account</h3>
            <form onSubmit={handleEditSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Full Name</label>
                <input 
                  type="text" required
                  value={formData.fullname}
                  onChange={(e) => setFormData({...formData, fullname: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-red-100 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Email</label>
                <input 
                  type="email" required
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-red-100 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">New Password (Optional)</label>
                <input 
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-red-100 outline-none"
                  placeholder="Leave blank to keep current"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Role</label>
                <select 
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-red-100 outline-none"
                >
                  <option value="HR">HR</option>
                  <option value="ADMIN">Admin</option>
                  <option value="CANDIDATE">Candidate</option>
                </select>
              </div>
              <button 
                type="submit" 
                className="w-full bg-[#D10043] text-white py-3 rounded-xl font-bold hover:bg-[#b00038] transition-colors mt-6 shadow-lg shadow-red-100"
              >
                Update Account
              </button>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

export default UsersPage;