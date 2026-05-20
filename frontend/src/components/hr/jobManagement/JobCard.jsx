import React from 'react';
import { Briefcase } from 'lucide-react';

const JobCard = ({ job, onEdit, onView, onArchive, onUnarchive, onDelete }) => {
  const skillsArray = typeof job.skills_requirements === 'string'
    ? job.skills_requirements.split(',').map(s => s.trim())
    : [];

  return (
    <div className="bg-white p-6 md:p-8 rounded-[32px] border border-gray-100 shadow-sm hover:shadow-xl hover:-translate-y-1 hover:border-pink-100 transition-all duration-300 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 lg:gap-8 group">
      <div className="flex flex-col sm:flex-row gap-5 lg:gap-6 w-full lg:w-auto">
        <div className="w-16 h-16 rounded-2xl overflow-hidden border border-pink-100 bg-gradient-to-br from-pink-50 to-red-50 shadow-inner group-hover:scale-105 transition-transform duration-300 shrink-0 flex items-center justify-center">
          <Briefcase className="w-7 h-7 text-[#D60041]" />
        </div>

        <div className="flex-grow">
          <div className="flex flex-wrap items-center gap-3 mb-1.5">
            <h3 className="text-xl font-bold text-gray-900 group-hover:text-[#D60041] transition-colors">{job.title}</h3>
            <span className={`text-[10px] font-bold px-3 py-1 rounded-full border uppercase tracking-wide shadow-sm ${job.is_active ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-gray-50 text-gray-500 border-gray-200"
              }`}>
              {job.is_active ? "Active" : "Archived"}
            </span>
          </div>

          <p className="text-sm text-gray-500 font-medium mb-3">
            {job.department} • {job.location} • ID: {job.job_id}
          </p>
          <p className="text-sm font-extrabold text-gray-800 mb-4">{job.salary_range} <span className="font-medium text-gray-400">/ month</span></p>

          <div className="flex flex-wrap gap-2">
            {skillsArray.slice(0, 4).map((skill, idx) => (
              <span key={idx} className="bg-gray-50 border border-gray-200 text-gray-600 text-[11px] font-bold px-3 py-1.5 rounded-lg group-hover:border-pink-100 transition-colors shadow-sm">
                {skill}
              </span>
            ))}
            {skillsArray.length > 4 && (
              <span className="bg-gray-50 border border-gray-100 text-gray-400 text-[11px] font-bold px-2 py-1.5 rounded-lg">
                +{skillsArray.length - 4} more
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap flex-row lg:flex-col xl:flex-row gap-3 w-full lg:w-auto shrink-0 mt-4 lg:mt-0 pt-4 lg:pt-0 border-t lg:border-t-0 border-gray-100">
        <button
          onClick={() => onView(job)}
          className="flex-grow lg:flex-grow-0 px-5 py-3 bg-[#D60041] border border-[#D60041] text-white rounded-xl text-xs font-bold hover:bg-[#b50037] hover:border-[#b50037] transition-all duration-300 shadow-sm text-center"
        >
          View Details
        </button>
        <button
          onClick={() => onEdit(job)}
          className="flex-grow lg:flex-grow-0 px-5 py-3 bg-white border border-gray-200 rounded-xl text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all duration-300 shadow-sm text-center"
        >
          Edit Job
        </button>
        {job.is_active ? (
          <button
            onClick={() => onArchive(job.job_id, job.title)}
            className="flex-grow lg:flex-grow-0 px-5 py-3 bg-amber-50 border border-amber-200 rounded-xl text-xs font-bold text-amber-600 hover:bg-amber-600 hover:text-white hover:border-amber-600 transition-all duration-300 shadow-sm text-center"
          >
            Archive
          </button>
        ) : (
          <button
            onClick={() => onUnarchive(job.job_id, job.title)}
            className="flex-grow lg:flex-grow-0 px-5 py-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-600 hover:bg-emerald-600 hover:text-white hover:border-emerald-600 transition-all duration-300 shadow-sm text-center"
          >
            Unarchive
          </button>
        )}
        <button
          onClick={() => onDelete(job.job_id, job.title)}
          className="flex-grow lg:flex-grow-0 px-5 py-3 bg-rose-50 border border-rose-200 rounded-xl text-xs font-bold text-rose-600 hover:bg-rose-600 hover:text-white hover:border-rose-600 transition-all duration-300 shadow-sm text-center"
        >
          Remove
        </button>
      </div>
    </div>
  );
};

export default JobCard;
