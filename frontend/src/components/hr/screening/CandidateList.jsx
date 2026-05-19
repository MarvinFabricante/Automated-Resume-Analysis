import React from 'react';
import { Search } from 'lucide-react';
import CandidateCard from './CandidateCard';

const CandidateList = ({ candidates, onOpenDetails, onOpenInterview, onUpdateStatus, onArchiveApplication, onDeleteApplication }) => {
  if (candidates.length === 0) {
    return (
      <div className="text-center py-24 bg-white rounded-[32px] border-2 border-dashed border-gray-200 text-gray-400 shadow-sm">
        <Search className="h-10 w-10 mx-auto text-gray-300 mb-4" />
        <p className="text-lg font-bold text-gray-500">No candidates found</p>
        <p className="text-sm mt-1">Try adjusting your search criteria</p>
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
