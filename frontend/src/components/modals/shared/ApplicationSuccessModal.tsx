import React from 'react';
import { CheckCircle2 } from 'lucide-react';

interface ApplicationSuccessModalProps {
  isOpen: boolean;
  onConfirm: () => void;
}

const ApplicationSuccessModal: React.FC<ApplicationSuccessModalProps> = ({ isOpen, onConfirm }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-300">
      <div className="bg-white rounded-[40px] shadow-2xl w-full max-w-md p-10 transform transition-all animate-in zoom-in-95 duration-300">
        <div className="flex flex-col items-center text-center">
          <div className="w-20 h-20 rounded-3xl bg-green-50 flex items-center justify-center mb-8 shadow-inner">
            <CheckCircle2 className="w-10 h-10 text-green-500" strokeWidth={2.5} />
          </div>
          <h3 className="text-2xl font-black text-slate-900 mb-3 tracking-tight">
            Submission Ready!
          </h3>
          <p className="text-slate-500 font-medium mb-10 leading-relaxed px-4">
            Your application details have been saved and optimized. We're now ready to finalize your submission.
          </p>
          <button
            onClick={onConfirm}
            className="w-full bg-[#D10043] hover:bg-slate-900 text-white font-black uppercase tracking-widest text-xs py-5 rounded-[24px] transition-all shadow-xl shadow-pink-100 active:scale-[0.98]"
          >
            Confirm & Finalize
          </button>
        </div>
      </div>
    </div>
  );
};

export default ApplicationSuccessModal;
