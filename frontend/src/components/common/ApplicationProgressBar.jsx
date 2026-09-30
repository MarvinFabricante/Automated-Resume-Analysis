import React from 'react';
import { Check, FileUp, Edit3, Eye, CheckCircle2 } from 'lucide-react';

const DEFAULT_STEPS = [
  {
    number: 1,
    title: 'Upload Resume',
    subtitle: 'Upload & Parse CV',
    icon: FileUp,
  },
  {
    number: 2,
    title: 'Submit Application',
    subtitle: 'Fill & Update Details',
    icon: Edit3,
  },
  {
    number: 3,
    title: 'Review Application',
    subtitle: 'Verify & Match Score',
    icon: Eye,
  },
  {
    number: 4,
    title: 'Confirmation',
    subtitle: 'Application Sent',
    icon: CheckCircle2,
  },
];

const ApplicationProgressBar = ({
  currentStep = 1,
  steps = DEFAULT_STEPS,
  onStepClick = null,
  className = '',
}) => {
  const totalSteps = steps.length;
  const progressPercent = Math.min(
    100,
    Math.round(((currentStep - 1) / (totalSteps - 1)) * 100)
  );

  const currentStepData = steps.find((s) => s.number === currentStep) || steps[0];
  const nextStepData = steps.find((s) => s.number === currentStep + 1);

  return (
    <div
      className={`w-full bg-white rounded-[28px] border border-slate-100 shadow-sm p-5 md:p-6 mb-8 transition-all ${className}`}
    >
      {/* Mobile Stepper View (< md) */}
      <div className="md:hidden space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 bg-pink-50 text-[#D60041] rounded-full text-[10px] font-black uppercase tracking-wider">
              Step {currentStep} of {totalSteps}
            </span>
            <span className="text-xs font-black text-slate-900 truncate">
              {currentStepData.title}
            </span>
          </div>
          <span className="text-xs font-black text-[#D60041]">{progressPercent}%</span>
        </div>

        {/* Progress Track */}
        <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
          <div
            className="bg-gradient-to-r from-[#D60041] to-[#FF4D8D] h-full rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium pt-1">
          <span>{currentStepData.subtitle}</span>
          {nextStepData && (
            <span className="text-slate-500 font-bold">
              Next: <span className="text-slate-700">{nextStepData.title}</span>
            </span>
          )}
        </div>
      </div>

      {/* Desktop Stepper View (>= md) */}
      <div className="hidden md:block">
        <div className="relative flex items-center justify-between">
          {/* Background Connecting Track */}
          <div className="absolute left-8 right-8 top-5 h-1 bg-slate-100 -translate-y-1/2 z-0" />

          {/* Active Gradient Connecting Track */}
          <div
            className="absolute left-8 top-5 h-1 bg-gradient-to-r from-[#D60041] to-[#FF4D8D] -translate-y-1/2 z-0 transition-all duration-500 ease-out"
            style={{
              width: `${(Math.max(0, currentStep - 1) / (totalSteps - 1)) * 100}%`,
              maxWidth: 'calc(100% - 4rem)',
            }}
          />

          {steps.map((step) => {
            const isCompleted = step.number < currentStep;
            const isCurrent = step.number === currentStep;
            const isClickable = onStepClick && isCompleted;
            const StepIcon = step.icon;

            return (
              <div
                key={step.number}
                onClick={() => isClickable && onStepClick(step.number)}
                className={`relative z-10 flex flex-col items-center group ${
                  isClickable ? 'cursor-pointer' : ''
                }`}
                style={{ width: `${100 / totalSteps}%` }}
              >
                {/* Node Circle */}
                <div
                  className={`w-10 h-10 rounded-2xl flex items-center justify-center font-black text-sm transition-all duration-300 ${
                    isCompleted
                      ? 'bg-emerald-500 text-white shadow-md shadow-emerald-100 hover:scale-110'
                      : isCurrent
                      ? 'bg-[#D60041] text-white shadow-lg shadow-pink-200 ring-4 ring-pink-100 scale-105'
                      : 'bg-white text-slate-400 border-2 border-slate-200'
                  }`}
                >
                  {isCompleted ? (
                    <Check size={18} strokeWidth={3} />
                  ) : (
                    <StepIcon size={18} strokeWidth={2.2} />
                  )}
                </div>

                {/* Step Labels */}
                <div className="text-center mt-3 px-1">
                  <div className="flex items-center justify-center gap-1.5 mb-0.5">
                    <span
                      className={`text-[10px] font-black uppercase tracking-wider ${
                        isCurrent
                          ? 'text-[#D60041]'
                          : isCompleted
                          ? 'text-emerald-600'
                          : 'text-slate-400'
                      }`}
                    >
                      Step 0{step.number}
                    </span>
                    {isCompleted && (
                      <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                    )}
                  </div>
                  <h4
                    className={`text-xs md:text-sm font-black transition-colors ${
                      isCurrent
                        ? 'text-slate-900'
                        : isCompleted
                        ? 'text-slate-800'
                        : 'text-slate-400'
                    }`}
                  >
                    {step.title}
                  </h4>
                  <p
                    className={`text-[11px] font-medium hidden lg:block transition-colors ${
                      isCurrent
                        ? 'text-slate-600'
                        : isCompleted
                        ? 'text-slate-400'
                        : 'text-slate-300'
                    }`}
                  >
                    {step.subtitle}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default ApplicationProgressBar;
