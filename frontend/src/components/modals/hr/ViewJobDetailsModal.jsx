import React from 'react';
import { Helmet } from 'react-helmet-async';
import {
  X, Briefcase, MapPin, Building2, DollarSign,
  ListChecks, FileText, Clock, CheckCircle2,
  AlertCircle, Globe, Wallet, GraduationCap, Trophy
} from 'lucide-react';

const ViewJobDetailsModal = ({ isOpen, onClose, job }) => {
  if (!isOpen || !job) return null;

  const skillsArray = typeof job.skills_requirements === 'string'
    ? job.skills_requirements.split(',').map(s => s.trim())
    : job.skills_requirements || [];

  const DetailCard = ({ icon: Icon, label, value, colorClass = "text-gray-400" }) => (
    <div className="group p-6 rounded-[24px] bg-gray-50/50 border border-gray-100/50 hover:bg-white hover:border-pink-100 hover:shadow-xl hover:shadow-pink-50/50 transition-all duration-300 flex items-center gap-5">
      <div className={`w-14 h-14 rounded-2xl bg-white border border-gray-100 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-500 ${colorClass}`}>
        <Icon size={24} />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-400 mb-1">{label}</p>
        <p className="text-base font-black text-gray-900 truncate">{value || 'N/A'}</p>
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md transition-opacity duration-300">
      <Helmet>
        <title>{job.job_title || job.title} | Job Details</title>
      </Helmet>
      <div className="bg-white w-full max-w-7xl rounded-[40px] shadow-[0_20px_50px_rgba(0,0,0,0.1)] overflow-hidden animate-in fade-in zoom-in duration-300 max-h-[90vh] flex flex-col relative border border-white/20">

        {/* Modal Header */}
        <div className="px-10 py-8 border-b border-gray-50 flex justify-between items-center bg-white/80 backdrop-blur-md sticky top-0 z-10">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <div className="w-8 h-1.5 bg-[#d81159] rounded-full" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-[#d81159]">Job Portal</span>
              <span className="mx-2 w-1 h-1 rounded-full bg-gray-300" />
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Preview Mode</span>
            </div>
            <div className="flex items-center gap-3">
              <h2 className="text-3xl font-black text-gray-900 tracking-tight">{job.job_title || job.title}</h2>
              <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase border tracking-tighter ${job.is_active
                  ? 'bg-emerald-50 text-emerald-600 border-emerald-100'
                  : 'bg-gray-50 text-gray-400 border-gray-100'
                }`}>
                <div className={`w-1.5 h-1.5 rounded-full ${job.is_active ? 'bg-emerald-500 animate-pulse' : 'bg-gray-300'}`} />
                {job.is_active ? 'Active Posting' : 'Inactive'}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="group p-3 hover:bg-red-50 rounded-2xl transition-all duration-300 text-gray-400 hover:text-red-500"
          >
            <X size={24} className="group-hover:rotate-90 transition-transform duration-300" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="p-10 space-y-10">

            {/* Quick Stats Grid - 2x2 Layout for prominence */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <DetailCard icon={Building2} label="Department" value={job.department} colorClass="text-blue-500" />
              <DetailCard icon={Clock} label="Job Type" value={job.job_type} colorClass="text-orange-500" />
              <DetailCard icon={MapPin} label="Location" value={job.location} colorClass="text-emerald-500" />
              <DetailCard icon={Wallet} label="Salary" value={job.salary_range} colorClass="text-[#d81159]" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
              {/* Left Column: Main Content */}
              <div className="lg:col-span-2 space-y-12">
                <section>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2.5 rounded-xl bg-pink-50 text-[#d81159]">
                      <FileText size={18} />
                    </div>
                    <h3 className="text-lg font-black text-gray-900">Position Description</h3>
                  </div>
                  <div className="relative">
                    <div className="absolute -left-6 top-0 bottom-0 w-1 bg-gray-50 rounded-full" />
                    <p className="text-base text-gray-600 leading-relaxed whitespace-pre-line pl-2">
                      {job.description || "No description provided for this position."}
                    </p>
                  </div>
                </section>

                <section className="p-8 rounded-3xl bg-gray-900 text-white shadow-xl relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-[#d81159]/10 rounded-full blur-3xl -mr-16 -mt-16 group-hover:scale-150 transition-transform duration-700" />
                  <div className="relative z-10">
                    <div className="flex items-center gap-3 mb-6">
                      <ListChecks size={20} className="text-[#d81159]" />
                      <h3 className="text-sm font-bold uppercase tracking-widest">Key Requirements</h3>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {skillsArray.length > 0 ? (
                        skillsArray.map((skill, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1.5 bg-white/10 border border-white/10 text-white text-[10px] font-bold rounded-lg hover:bg-[#d81159] hover:border-[#d81159] transition-colors cursor-default"
                          >
                            {skill}
                          </span>
                        ))
                      ) : (
                        <p className="text-xs text-gray-500 italic">No specific skills listed.</p>
                      )}
                    </div>
                  </div>
                </section>
              </div>

              {/* Right Column: Sidebar Info */}
              <div className="space-y-8">
                <div className="p-6 rounded-3xl border-2 border-dashed border-gray-100 text-center">
                  <p className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-2">Internal Reference</p>
                  <code className="text-sm font-mono font-bold text-gray-800">{job.job_id}</code>
                </div>

                {job.education_requirements && (
                  <div className="p-6 rounded-3xl bg-blue-50/50 border border-blue-100/50">
                    <div className="flex items-center gap-2.5 mb-2.5 text-blue-600">
                      <GraduationCap size={18} />
                      <span className="text-[10px] font-black uppercase tracking-widest">Education Needed</span>
                    </div>
                    <p className="text-sm text-gray-800 font-bold leading-normal">
                      {job.education_requirements}
                    </p>
                  </div>
                )}

                {job.experience_requirements && (
                  <div className="p-6 rounded-3xl bg-orange-50/50 border border-orange-100/50">
                    <div className="flex items-center gap-2.5 mb-2.5 text-orange-600">
                      <Trophy size={18} />
                      <span className="text-[10px] font-black uppercase tracking-widest">Experience Needed</span>
                    </div>
                    <p className="text-sm text-gray-800 font-bold leading-normal">
                      {job.experience_requirements}
                    </p>
                  </div>
                )}

                <div className="p-6 rounded-3xl bg-pink-50 border border-pink-100/50">
                  <div className="flex items-center gap-2 mb-3 text-[#d81159]">
                    <CheckCircle2 size={16} />
                    <span className="text-[10px] font-black uppercase tracking-widest">Verified Role</span>
                  </div>
                  <p className="text-[11px] text-gray-600 font-medium leading-relaxed">
                    This position has been verified by the HR department and is currently open for applications.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>


        {/* Footer */}
        <div className="px-10 py-8 border-t border-gray-50 bg-gray-50/30 flex justify-end items-center sticky bottom-0 z-10 backdrop-blur-md">
          <button
            onClick={onClose}
            className="px-10 py-4 bg-gray-900 text-white rounded-2xl text-sm font-black hover:bg-black transition-all shadow-lg active:scale-95"
          >
            Close Preview
          </button>
        </div>
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #f1f1f1;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #e5e5e5;
        }
      `}</style>
    </div>
  );
};

export default ViewJobDetailsModal;