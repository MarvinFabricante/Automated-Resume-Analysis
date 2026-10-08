import React from 'react';
import { UserX, RotateCcw } from 'lucide-react';
import CandidateCard from './CandidateCard';
import CandidateTableView from './CandidateTableView';

const CandidateList = ({ 
  candidates = [], 
  viewMode = 'cards',
  selectedIds = [],
  onToggleSelect,
  onSelectAll,
  onOpenDetails, 
  onOpenInterview, 
  onUpdateStatus, 
  onArchiveApplication,
  onRestoreApplication, 
  onDeleteApplication,
  onSkillClick,
  onResetFilters
}) => {
  if (candidates.length === 0) {
    return (
      <div className="text-center py-16 sm:py-20 px-4 sm:px-6 bg-white rounded-2xl sm:rounded-3xl border border-gray-200/80 shadow-sm animate-in fade-in duration-300">
        <div className="w-14 h-14 sm:w-16 sm:h-16 bg-pink-50 text-[#D60041] rounded-2xl flex items-center justify-center mx-auto mb-3.5 border border-pink-100 shadow-xs">
          <UserX className="w-7 h-7 sm:w-8 sm:h-8" />
        </div>
        <h4 className="text-base sm:text-lg font-bold text-gray-900 tracking-tight">No candidates match your criteria</h4>
        <p className="text-xs sm:text-sm text-gray-500 mt-1 max-w-md mx-auto leading-relaxed">
          Try clearing your search query, adjusting the position or score filters, or checking the archived candidate list.
        </p>
        {onResetFilters && (
          <button
            type="button"
            onClick={onResetFilters}
            className="mt-4 sm:mt-5 inline-flex items-center gap-2 px-4 py-2 sm:px-5 sm:py-2.5 bg-gray-50 hover:bg-pink-50 text-gray-700 hover:text-[#D60041] border border-gray-200 hover:border-pink-200 rounded-xl text-xs font-bold transition-all cursor-pointer shadow-xs"
          >
            <RotateCcw size={13} />
            <span>Reset All Filters</span>
          </button>
        )}
      </div>
    );
  }

  if (viewMode === 'table') {
    return (
      <CandidateTableView
        candidates={candidates}
        selectedIds={selectedIds}
        onToggleSelect={onToggleSelect}
        onSelectAll={onSelectAll}
        onOpenDetails={onOpenDetails}
        onOpenInterview={onOpenInterview}
        onUpdateStatus={onUpdateStatus}
        onArchiveApplication={onArchiveApplication}
        onRestoreApplication={onRestoreApplication}
        onDeleteApplication={onDeleteApplication}
        onSkillClick={onSkillClick}
      />
    );
  }

  return (
    <div className="space-y-3.5 sm:space-y-4 animate-in fade-in duration-200">
      {candidates.map((candidate) => (
        <CandidateCard 
          key={candidate.id} 
          candidate={candidate} 
          isSelected={selectedIds.includes(candidate.id)}
          onToggleSelect={onToggleSelect}
          onOpenDetails={onOpenDetails} 
          onOpenInterview={onOpenInterview} 
          onUpdateStatus={onUpdateStatus}
          onArchiveApplication={onArchiveApplication}
          onRestoreApplication={onRestoreApplication}
          onDeleteApplication={onDeleteApplication}
          onSkillClick={onSkillClick}
        />
      ))}
    </div>
  );
};

export default CandidateList;
