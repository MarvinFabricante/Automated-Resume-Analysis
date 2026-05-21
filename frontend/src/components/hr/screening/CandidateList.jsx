import React from 'react';
import { Search } from 'lucide-react';
import CandidateCard from './CandidateCard';

const CandidateList = ({ candidates, onOpenDetails, onOpenInterview, onUpdateStatus, onArchiveApplication, onDeleteApplication }) => {
  if (candidates.length === 0) {
    return (
      <div className="text-center py-16 px-4 bg-white rounded-[32px] border border-gray-100 shadow-sm">
        <div className="w-14 h-14 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto mb-3 border border-gray-100">
          <Search className="w-6 h-6 text-gray-300" />
        </div>
        <h4 className="text-sm font-bold text-gray-900">No candidates found</h4>
        <p className="text-xs text-gray-400 mt-1">Try adjusting your search criteria or filters.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {candidates.map(candidate => (
        <CandidateCard 
          key={candidate.id} 
          candidate={candidate} 
          onOpenDetails={onOpenDetails} 
          onOpenInterview={onOpenInterview} 
          onUpdateStatus={onUpdateStatus}
          onArchiveApplication={onArchiveApplication}
          onDeleteApplication={onDeleteApplication}
        />
      ))}
    </div>
  );
};

export default CandidateList;
