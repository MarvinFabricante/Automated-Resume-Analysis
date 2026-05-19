import React from 'react';
import { Helmet } from 'react-helmet-async';
import { X, MapPin, Briefcase, Calendar, Star, GraduationCap, Mail, Phone } from 'lucide-react';

const ViewCandidateDetailsModal = ({ isOpen, onClose, candidate }) => {
  if (!isOpen || !candidate) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50">
      <Helmet>
        <title>{candidate.name} | Application Review</title>
      </Helmet>
      <div className="bg-white w-full max-w-6xl max-h-[90vh] rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
        
        <div className="px-8 py-5 border-b border-gray-100 flex justify-between items-center bg-white sticky top-0">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">Candidate Profile</span>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400">
            <X size={20} />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          <div className="w-80 bg-gray-50/50 border-r border-gray-100 p-8 overflow-y-auto">
            <div className="text-center mb-8">
              <div className="w-24 h-24 rounded-2xl overflow-hidden border-4 border-white shadow-sm mx-auto mb-4 bg-pink-50">
                {candidate.profileImage ? (
                  <img src={candidate.profileImage} alt={candidate.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-[#d81159] text-3xl font-bold bg-pink-100">
                    {candidate.name.charAt(0)}
                  </div>
                )}
              </div>
              <h2 className="text-xl font-bold text-gray-900">{candidate.name}</h2>
              <p className="text-sm text-gray-500 font-medium">{candidate.preferredJob}</p>
            </div>

            <div className="space-y-6">
              <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm text-center">
                <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">Match Score</p>
                <p className="text-3xl font-black text-emerald-500">{candidate.matchScore}%</p>
              </div>

              <div className="space-y-2">
                <div className="p-3 bg-blue-50 rounded-xl border border-blue-100">
                  <div className="flex justify-between items-center mb-0.5">
                    <p className="text-[9px] font-bold text-blue-400 uppercase">Skills Match</p>
                    <span className="text-[10px] font-black text-blue-600">{candidate.skillsScore || 0}%</span>
                  </div>
                  <p className="text-xs font-medium text-blue-700 leading-tight">{candidate.skills_reason || "Analyzed against job requirements."}</p>
                </div>
                <div className="p-3 bg-purple-50 rounded-xl border border-purple-100">
                  <div className="flex justify-between items-center mb-0.5">
                    <p className="text-[9px] font-bold text-purple-400 uppercase">Experience Match</p>
                    <span className="text-[10px] font-black text-purple-600">{candidate.experienceScore || 0}%</span>
                  </div>
                  <p className="text-xs font-medium text-purple-700 leading-tight">{candidate.experience_reason || "Analyzed based on extracted years."}</p>
                </div>
                <div className="p-3 bg-amber-50 rounded-xl border border-amber-100">
                  <div className="flex justify-between items-center mb-0.5">
                    <p className="text-[9px] font-bold text-amber-400 uppercase">Education Match</p>
                    <span className="text-[10px] font-black text-amber-600">{candidate.educationScore || 0}%</span>
                  </div>
                  <p className="text-xs font-medium text-amber-700 leading-tight">{candidate.education_reason || "Analyzed based on highest degree."}</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-3 text-gray-600">
                  <MapPin size={16} className="text-gray-400" />
                  <span className="text-sm">{candidate.location}</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <Mail size={16} className="text-gray-400" />
                  <span className="text-sm">{candidate.email || "N/A"}</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <Phone size={16} className="text-gray-400" />
                  <span className="text-sm">{candidate.phone || "N/A"}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex-1 p-8 overflow-y-auto bg-white">
            <section className="mb-8">
              <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
                <Star size={16} className="text-[#d81159]" /> Core Expertise
              </h3>
              <div className="flex flex-wrap gap-2">
                {candidate.skills.map((skill, i) => (
                  <span key={i} className="px-4 py-2 bg-gray-50 text-gray-700 rounded-xl border border-gray-100 text-sm font-medium">
                    {skill}
                  </span>
                ))}
              </div>
            </section>

            <section className="mb-8">
              <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
                <Briefcase size={16} className="text-[#d81159]" /> Application Details
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-2xl bg-gray-50 border border-gray-100">
                  <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">Status</p>
                  <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-lg border border-blue-100">
                    {candidate.status}
                  </span>
                </div>
                <div className="p-4 rounded-2xl bg-gray-50 border border-gray-100">
                  <p className="text-[10px] font-bold text-gray-400 uppercase mb-1">Applied Date</p>
                  <span className="text-sm font-semibold text-gray-700">
                    {new Date(candidate.date).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </section>

            <section className="mb-8">
              <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
                <Star size={16} className="text-[#d81159]" /> Analysis Score Explanation
              </h3>
              <div className="bg-emerald-50/50 p-5 rounded-2xl border border-emerald-100">
                <p className="text-emerald-800 text-sm leading-relaxed font-medium">
                  We arrived at the final match score of <span className="font-black text-emerald-600">{candidate.matchScore}%</span> by evaluating the candidate across three weighted categories. This total consists of an <span className="font-bold">Education</span> contribution of <span className="font-black text-emerald-600">{Math.round((candidate.educationScore || 0) * 0.15)}%</span> (out of a possible 15%), a <span className="font-bold">Skills</span> contribution of <span className="font-black text-emerald-600">{Math.round((candidate.skillsScore || 0) * 0.35)}%</span> (out of a possible 35%), and an <span className="font-bold">Experience</span> contribution of <span className="font-black text-emerald-600">{Math.round((candidate.experienceScore || 0) * 0.50)}%</span> (out of a possible 50%).
                </p>
              </div>
            </section>

            <section>
              <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
                <GraduationCap size={16} className="text-[#d81159]" /> Candidate Summary
              </h3>
              <p className="text-gray-600 text-sm leading-relaxed bg-gray-50/50 p-5 rounded-2xl italic border border-dashed border-gray-200">
                "Experienced {candidate.preferredJob} with a strong background in {candidate.skills[0]} and {candidate.skills[1]}. 
                Proven track record of delivering high-quality projects in {candidate.location} with a focus on user experience and scalable architecture."
              </p>
            </section>
          </div>
        </div>

        <div className="p-6 border-t border-gray-100 bg-gray-50/50 flex justify-end gap-3">
          <button onClick={onClose} className="px-6 py-2.5 bg-white border border-gray-200 text-gray-600 rounded-xl text-sm font-bold hover:bg-gray-50 transition-all">
            Close Preview
          </button>
          <button className="px-6 py-2.5 bg-[#d81159] text-white rounded-xl text-sm font-bold hover:shadow-lg hover:shadow-pink-200 transition-all">
            Download Resume
          </button>
        </div>
      </div>
    </div>
  );
};

export default ViewCandidateDetailsModal;