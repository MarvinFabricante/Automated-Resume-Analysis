import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronUp, Users, ArrowRight, User } from 'lucide-react';
import { getAssetUrl } from '../../../services/api';

const CandidateRow = ({ name, role, skills, match, status, profileImage }) => {
  const statusStyles = {
    pending: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20",
    reviewed: "bg-blue-50 text-blue-700 ring-1 ring-blue-600/20",
    approved: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20",
    rejected: "bg-red-50 text-red-700 ring-1 ring-red-600/20"
  };

  const skillsList = Array.isArray(skills)
    ? skills
    : (typeof skills === 'string' ? skills.split(',').map(s => s.trim()) : []);

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border border-gray-100 bg-white rounded-[24px] hover:border-[#D60041]/30 hover:shadow-md transition-all duration-300 group gap-4">
      <div className="flex items-center gap-4 w-full sm:w-[40%] lg:w-[30%]">
        <div className="w-12 h-12 bg-red-50 rounded-full flex items-center justify-center overflow-hidden shrink-0 group-hover:bg-[#D60041] transition-colors duration-300">
          {profileImage ? (
            <img src={getAssetUrl(profileImage)} alt={name} className="w-full h-full object-cover" />
          ) : (
            <User className="text-[#D60041] h-5 w-5 group-hover:text-white transition-colors" />
          )}
        </div>

        <div className="min-w-0">
          <h3 className="font-bold text-sm md:text-[15px] text-gray-900 truncate group-hover:text-[#D60041] transition-colors">{name}</h3>
          <p className="text-[11px] text-gray-500 font-medium truncate">{role}</p>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-between sm:justify-end gap-4 md:gap-8">
        <div className="hidden lg:flex gap-2 min-w-[150px]">
          {skillsList.slice(0, 2).map((skill, i) => (
            <span key={i} className="px-2.5 py-1 bg-gray-50 rounded-md text-[10px] font-medium text-gray-600 border border-gray-100 whitespace-nowrap">
              {skill}
            </span>
          ))}
          {skillsList.length > 2 && (
            <span className="px-2 py-1 bg-gray-50 rounded-md text-[10px] font-medium text-gray-400 border border-gray-100">
              +{skillsList.length - 2}
            </span>
          )}
        </div>

        <div className="flex flex-col items-center justify-center min-w-[50px]">
          <div className="flex items-baseline gap-0.5">
            <span className="text-base md:text-lg font-black text-gray-900 group-hover:text-[#D60041] transition-colors">{match}</span>
            <span className="text-[10px] font-bold text-gray-400">%</span>
          </div>
          <span className="text-[8px] font-black text-gray-400 uppercase tracking-widest">Match</span>
        </div>

        <div className="hidden xs:flex min-w-[70px] justify-center">
          <span className={`px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-wider ${statusStyles[status.toLowerCase()] || statusStyles.pending}`}>
            {status}
          </span>
        </div>

        <button className="px-4 md:px-6 py-2.5 bg-gray-900 text-white rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-[#D60041] transition-all shadow-md active:scale-95 shrink-0">
          Review
        </button>
      </div>
    </div>
  );
};

const RecentSubmissions = ({ candidates }) => {
  const navigate = useNavigate();

  return (
    <div className="bg-white border border-gray-100 rounded-[24px] shadow-sm p-6 lg:p-8 mb-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4 sm:gap-0">
        <div>
          <h3 className="text-xl font-semibold text-gray-900 tracking-tight">Recent Submissions</h3>
          <p className="text-sm text-gray-500 mt-1">
            Review the latest candidate applications
          </p>
        </div>

        <button 
          onClick={() => navigate('/screening')} 
          className="group flex items-center gap-1.5 text-sm font-medium text-[#D60041] hover:text-[#b50037] transition-colors"
        >
          <span>View All</span>
          <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
        </button>
      </div>

      <div className="space-y-3">
        {candidates.map((can) => (
          <CandidateRow
            key={can.id}
            name={can.name}
            role={can.preferredJob}
            skills={can.skills}
            match={can.matchScore}
            status={can.status}
            profileImage={can.profileImage}
          />
        ))}
      </div>
    </div>
  );
};

export default RecentSubmissions;
