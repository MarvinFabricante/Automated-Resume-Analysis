import React from 'react';
import { X } from 'lucide-react';
import { useNavigate } from '@/utils/navigation';
import ApplicationThreadPanel from '../../chat/ApplicationThreadPanel';

interface MessageApplicantModalProps {
  isOpen: boolean;
  onClose: () => void;
  applicationId: number | string | null;
  candidateName?: string;
  jobTitle?: string;
}

const MessageApplicantModal: React.FC<MessageApplicantModalProps> = ({
  isOpen,
  onClose,
  applicationId,
  candidateName,
  jobTitle,
}) => {
  const navigate = useNavigate();

  if (!isOpen || !applicationId) return null;

  return (
    <div
      className="fixed inset-0 z-[70] bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 animate-in fade-in duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-2xl bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden animate-in zoom-in-95 duration-150">
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-white">
          <div>
            <h3 className="text-sm sm:text-base font-black text-slate-900 tracking-tight">
              Message applicant
            </h3>
            <p className="text-[11px] text-slate-500">
              {candidateName || 'Applicant'} • {jobTitle || 'Application'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close message dialog"
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-4 bg-slate-50/40">
          <ApplicationThreadPanel
            applicationId={applicationId}
            candidateName={candidateName}
            jobTitle={jobTitle}
            viewerRole="HR"
            compact
            onOpenFullInbox={(threadId, appId) => {
              onClose();
              const role = (typeof localStorage !== 'undefined' ? localStorage.getItem('role') : 'HR') || 'HR';
              const base = role.toUpperCase() === 'ADMIN' ? '/admin/messages' : '/hr/messages';
              const query = threadId
                ? `?thread=${threadId}`
                : appId
                ? `?application=${appId}`
                : '';
              navigate(`${base}${query}`);
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default MessageApplicantModal;
