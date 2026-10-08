import React from 'react';
import { Search, RotateCcw, UserX } from 'lucide-react';
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
      <div className="text-center py-20 px-6 bg-white rounded-2xl sm:rounded-[32px] border border-gray-100 shadow-sm animate-in fade-in duration-300">
        <div className="w-16 h-16 bg-pink-50 text-[#D60041] rounded-2xl flex items-center justify-center mx-auto mb-4 border border-pink-100 shadow-sm">
          <UserX className="w-8 h-8" />
        </div>
        <h4 className="text-base sm:text-lg font-bold text-gray-900">No candidates match your filters</h4>
        <p className="text-xs sm:text-sm text-gray-500 mt-1 max-w-md mx-auto leading-relaxed">
          We couldn't find any candidate applications matching your current search criteria, job selection, or status filter.
        </p>
        {onResetFilters && (
          <button
            type="button"
            onClick={onResetFilters}
            className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 bg-gray-50 hover:bg-pink-50 text-gray-700 hover:text-[#D60041] border border-gray-200 hover:border-pink-200 rounded-xl text-xs font-bold transition-all cursor-pointer shadow-sm"
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
    <div className="space-y-4 sm:space-y-5 animate-in fade-in duration-200">
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
