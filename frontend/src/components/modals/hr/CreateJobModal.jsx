import React, { useState, useEffect } from 'react';

import { 
  X, Briefcase, MapPin, Building2, DollarSign, 
  ListChecks, FileText, Loader2, CheckCircle2, 
  AlertCircle, ChevronRight, ChevronLeft, Info,
  Trophy, Target, Sparkles, GraduationCap, Award
} from 'lucide-react';

import { useCreateJobMutation } from '../../../redux/api/apiSlice';

const CreateJobModal = ({ isOpen, onClose, onSuccess }) => {
  const [createJob, { isLoading: isCreating }] = useCreateJobMutation();
  const [currentStep, setCurrentStep] = useState(1);
  const [status, setStatus] = useState({ type: null, message: '' });
  const [formData, setFormData] = useState({
    job_id: '',
    job_title: '',
    department: 'Human Resources',
    location: '',
    job_type: 'Full-Time',
    salary_range: '',
    description: '',
    skills_requirements: '',
    education_requirements: '',
    experience_requirements: '',
    certifications_requirements: '',
    is_active: true
  });

  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (isOpen && !formData.job_id) {
      const generatedId = `JOB-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
      setFormData(prev => ({ ...prev, job_id: generatedId }));
    }
    if (!isOpen) {
      setStatus({ type: null, message: '' });
      setCurrentStep(1);
      setErrors({});
    }
  }, [isOpen]);

  const validateStep = (step) => {
    const newErrors = {};
    if (step === 1) {
      if (!formData.job_title) newErrors.job_title = 'Job title is required';
      if (!formData.job_id) newErrors.job_id = 'Job ID is required';
    } else if (step === 2) {
      if (!formData.location) newErrors.location = 'Location is required';
      if (!formData.salary_range) newErrors.salary_range = 'Salary range is required';
    } else if (step === 3) {
      if (!formData.description) newErrors.description = 'Description is required';
      if (!formData.skills_requirements) newErrors.skills_requirements = 'Skills are required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, 3));
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  const formatCurrency = (value) => {
    const digits = value.replace(/\D/g, '');
    if (!digits) return '';
    const formatted = new Intl.NumberFormat('en-PH').format(digits);
    return `₱${formatted}`;
  };

  const handleSalaryChange = (e) => {
    const rawValue = e.target.value;
    const parts = rawValue.split('-').map(part => part.trim());

    let formattedValue = '';
    if (parts.length > 1) {
      const min = formatCurrency(parts[0]);
      const max = formatCurrency(parts[1]);
      formattedValue = min && max ? `${min} - ${max}` : rawValue;
    } else {
      formattedValue = formatCurrency(parts[0]);
    }

    setFormData({ ...formData, salary_range: formattedValue });
    if (errors.salary_range) setErrors({ ...errors, salary_range: null });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (currentStep < 3) {
      nextStep();
      return;
    }

    if (!validateStep(3)) return;

    setStatus({ type: null, message: '' });

    try {
      const result = await createJob(formData).unwrap();
      
      setStatus({ type: 'success', message: 'Job posting has been created successfully!' });

      setTimeout(() => {
        if (onSuccess) onSuccess(result);
        onClose();
        // Reset form
        setFormData({
          job_id: '', job_title: '', department: 'Human Resources',
          location: '', job_type: 'Full-Time', salary_range: '',
          description: '', skills_requirements: '', 
          education_requirements: '', experience_requirements: '',
          certifications_requirements: '',
          is_active: true
        });
      }, 2000);
    } catch (err) {
      const errorMessage = err.data?.detail || 'An error occurred while creating the job.';
      setStatus({ type: 'error', message: errorMessage });
    }
  };

  if (!isOpen) return null;

  const inputClasses = (hasError) => `w-full px-4 py-3 bg-gray-50 border ${hasError ? 'border-red-300 ring-1 ring-red-50' : 'border-gray-200'} rounded-xl text-sm focus:outline-none focus:border-[#d81159] focus:ring-4 focus:ring-pink-50 transition-all duration-200`;
  const labelClasses = "flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2 ml-1";

  const renderStepIndicator = () => (
    <div className="px-8 pt-6 pb-2">
      <div className="flex items-center justify-between relative">
        {/* Progress Line */}
        <div className="absolute top-1/2 left-0 w-full h-0.5 bg-gray-100 -translate-y-1/2 z-0" />
        <div 
          className="absolute top-1/2 left-0 h-0.5 bg-gradient-to-r from-[#d81159] to-pink-400 -translate-y-1/2 z-0 transition-all duration-500 ease-out" 
          style={{ width: `${((currentStep - 1) / 2) * 100}%` }}
        />
        
        {[1, 2, 3].map((step) => (
          <div key={step} className="relative z-10 flex flex-col items-center">
            <div 
              className={`w-10 h-10 rounded-full flex items-center justify-center border-4 transition-all duration-300 ${
                currentStep >= step 
                  ? 'bg-white border-[#d81159] text-[#d81159] shadow-lg shadow-pink-100' 
                  : 'bg-white border-gray-100 text-gray-300'
              }`}
            >
              {currentStep > step ? <CheckCircle2 size={20} className="fill-[#d81159] text-white" /> : <span className="font-bold text-sm">{step}</span>}
            </div>
            <span className={`mt-2 text-[10px] font-bold uppercase tracking-tighter ${currentStep >= step ? 'text-[#d81159]' : 'text-gray-400'}`}>
              {step === 1 ? 'General' : step === 2 ? 'Details' : 'Requirements'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md transition-opacity duration-300">
      <div className="bg-white w-full max-w-2xl rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.1)] overflow-hidden animate-in fade-in zoom-in duration-300 max-h-[90vh] flex flex-col relative border border-white/20">
        
        {/* Status Overlay */}
        {status.type && (
          <div className="absolute inset-0 z-[100] flex items-center justify-center p-6 bg-white/95 backdrop-blur-sm animate-in fade-in duration-300">
            <div className={`relative max-w-sm w-full p-10 rounded-3xl text-center shadow-2xl border ${status.type === 'success' ? 'bg-emerald-50/50 border-emerald-100' : 'bg-red-50/50 border-red-100'}`}>
              <button
                onClick={() => setStatus({ type: null, message: '' })}
                className="absolute top-4 right-4 p-2 rounded-full hover:bg-black/5 text-gray-400 transition-colors"
              >
                <X size={18} />
              </button>
              <div className="flex justify-center mb-6">
                <div className={`p-4 rounded-2xl ${status.type === 'success' ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'}`}>
                  {status.type === 'success' ? <Trophy size={48} /> : <AlertCircle size={48} />}
                </div>
              </div>
              <h3 className={`text-2xl font-black mb-3 ${status.type === 'success' ? 'text-emerald-900' : 'text-red-900'}`}>
                {status.type === 'success' ? 'Excellent!' : 'Oops!'}
              </h3>
              <p className={`text-base font-medium leading-relaxed ${status.type === 'success' ? 'text-emerald-700/80' : 'text-red-700/80'}`}>
                {status.message}
              </p>
              {status.type === 'error' && (
                <button
                  onClick={() => setStatus({ type: null, message: '' })}
                  className="mt-8 w-full py-4 bg-white border border-red-200 text-red-600 rounded-2xl text-sm font-bold hover:bg-red-50 transition-all shadow-sm active:scale-95"
                >
                  Try Again
                </button>
              )}
            </div>
          </div>
        )}

        {/* Modal Header */}
        <div className="px-10 py-7 border-b border-gray-50 flex justify-between items-center bg-white/80 backdrop-blur-md sticky top-0 z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-8 h-1.5 bg-[#d81159] rounded-full" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-[#d81159]">Job Portal</span>
            </div>
            <h2 className="text-2xl font-black text-gray-900 tracking-tight">Create Position</h2>
          </div>
          <button 
            onClick={onClose} 
            className="group p-3 hover:bg-red-50 rounded-2xl transition-all duration-300 text-gray-400 hover:text-red-500"
          >
            <X size={20} className="group-hover:rotate-90 transition-transform duration-300" />
          </button>
        </div>

        {renderStepIndicator()}

        <form 
          onSubmit={handleSubmit} 
          onKeyDown={(e) => {
            if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
              e.preventDefault();
              if (currentStep < 3) {
                nextStep();
              }
            }
          }}
          className="flex-1 overflow-y-auto custom-scrollbar"
        >
          <div className="p-10">
            {/* Step 1: General Info */}
            {currentStep === 1 && (
              <div className="space-y-6 animate-in slide-in-from-right-4 duration-500">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="md:col-span-2">
                    <label className={labelClasses}><Briefcase size={12} /> Job Title</label>
                    <input
                      autoFocus
                      required
                      type="text"
                      placeholder="e.g. Senior Full-Stack Engineer"
                      className={inputClasses(errors.job_title)}
                      value={formData.job_title}
                      onChange={(e) => {
                        setFormData({ ...formData, job_title: e.target.value });
                        if (errors.job_title) setErrors({ ...errors, job_title: null });
                      }}
                    />
                    {errors.job_title && <p className="text-[10px] text-red-500 mt-1.5 ml-1 font-bold">{errors.job_title}</p>}
                  </div>

                  <div>
                    <label className={labelClasses}><Target size={12} /> Job ID</label>
                    <input
                      required
                      type="text"
                      className={inputClasses(errors.job_id)}
                      value={formData.job_id}
                      onChange={(e) => {
                        setFormData({ ...formData, job_id: e.target.value });
                        if (errors.job_id) setErrors({ ...errors, job_id: null });
                      }}
                    />
                  </div>

                  <div>
                    <label className={labelClasses}><Building2 size={12} /> Department</label>
                    <select
                      className={inputClasses()}
                      value={formData.department}
                      onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    >
                      <option>Human Resources</option>
                      <option>Engineering</option>
                      <option>Information Technology</option>
                      <option>Marketing</option>
                      <option>Finance</option>
                      <option>Operations</option>
                      <option>Quality Assurance</option>
                      <option>Maintenance</option>
                      <option>Environmental</option>
                    </select>
                  </div>

                  <div className="md:col-span-2">
                    <label className={labelClasses}>Job Type</label>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {['Full-Time', 'Part-Time', 'Contract', 'Freelance', 'Internship'].map((type) => (
                        <button
                          key={type}
                          type="button"
                          onClick={() => setFormData({ ...formData, job_type: type })}
                          className={`py-3 px-4 rounded-xl text-xs font-bold transition-all border ${
                            formData.job_type === type 
                              ? 'bg-[#d81159] border-[#d81159] text-white shadow-lg shadow-pink-100' 
                              : 'bg-white border-gray-100 text-gray-500 hover:border-pink-200'
                          }`}
                        >
                          {type}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Details */}
            {currentStep === 2 && (
              <div className="space-y-6 animate-in slide-in-from-right-4 duration-500">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="md:col-span-2">
                    <label className={labelClasses}><MapPin size={12} /> Work Location</label>
                    <input
                      autoFocus
                      required
                      type="text"
                      placeholder="e.g. BGC, Taguig City (On-site)"
                      className={inputClasses(errors.location)}
                      value={formData.location}
                      onChange={(e) => {
                        setFormData({ ...formData, location: e.target.value });
                        if (errors.location) setErrors({ ...errors, location: null });
                      }}
                    />
                    {errors.location && <p className="text-[10px] text-red-500 mt-1.5 ml-1 font-bold">{errors.location}</p>}
                  </div>

                  <div className="md:col-span-2">
                    <label className={labelClasses}><DollarSign size={12} /> Salary Range (Monthly)</label>
                    <div className="relative">
                      <input
                        required
                        type="text"
                        placeholder="e.g. 50,000 - 80,000"
                        className={inputClasses(errors.salary_range)}
                        value={formData.salary_range}
                        onChange={handleSalaryChange}
                      />
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-1.5 pointer-events-none">
                        <span className="text-[10px] font-black text-gray-300 uppercase">PHP</span>
                      </div>
                    </div>
                    <p className="mt-2 text-[10px] text-gray-400 flex items-center gap-1.5 ml-1">
                      <Info size={10} /> Enter as "Min - Max" for range
                    </p>
                  </div>

                  <div className="md:col-span-2 mt-4">
                    <div className="p-6 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-100 flex items-center justify-between">
                      <div>
                        <span className="text-sm font-black text-gray-800 block mb-0.5">Visibility Status</span>
                        <span className="text-[11px] text-gray-400 font-medium">Make this post live immediately?</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, is_active: !formData.is_active })}
                        className={`relative inline-flex h-7 w-12 items-center rounded-full transition-all duration-300 ${
                          formData.is_active ? 'bg-emerald-500 shadow-lg shadow-emerald-100' : 'bg-gray-200'
                        }`}
                      >
                        <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform duration-300 ${
                          formData.is_active ? 'translate-x-6' : 'translate-x-1'
                        }`} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Requirements */}
            {currentStep === 3 && (
              <div className="space-y-6 animate-in slide-in-from-right-4 duration-500">
                <div>
                  <label className={labelClasses}><FileText size={12} /> Position Description</label>
                  <textarea
                    autoFocus
                    required
                    rows="6"
                    placeholder="Describe the role, responsibilities, and team environment..."
                    className={`${inputClasses(errors.description)} resize-none leading-relaxed`}
                    value={formData.description}
                    onChange={(e) => {
                      setFormData({ ...formData, description: e.target.value });
                      if (errors.description) setErrors({ ...errors, description: null });
                    }}
                  />
                </div>

                <div>
                  <label className={labelClasses}><ListChecks size={12} /> Key Skills & Requirements</label>
                  <input
                    required
                    type="text"
                    placeholder="e.g. React, Node.js, AWS, System Design (Comma separated)"
                    className={inputClasses(errors.skills_requirements)}
                    value={formData.skills_requirements}
                    onChange={(e) => {
                      setFormData({ ...formData, skills_requirements: e.target.value });
                      if (errors.skills_requirements) setErrors({ ...errors, skills_requirements: null });
                    }}
                  />
                  <div className="mt-3 flex flex-wrap gap-2">
                    {formData.skills_requirements.split(',').filter(s => s.trim()).slice(0, 5).map((skill, i) => (
                      <span key={i} className="px-3 py-1 bg-pink-50 text-[#d81159] text-[10px] font-bold rounded-full border border-pink-100">
                        {skill.trim()}
                      </span>
                    ))}
                    {formData.skills_requirements.split(',').filter(s => s.trim()).length > 5 && (
                      <span className="px-3 py-1 bg-gray-50 text-gray-400 text-[10px] font-bold rounded-full">
                        +{formData.skills_requirements.split(',').filter(s => s.trim()).length - 5} more
                      </span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <label className={labelClasses}><GraduationCap size={12} /> Education Requirements</label>
                    <input
                      type="text"
                      placeholder="e.g. Bachelor's Degree"
                      className={inputClasses()}
                      value={formData.education_requirements}
                      onChange={(e) => setFormData({ ...formData, education_requirements: e.target.value })}
                    />
                  </div>

                  <div>
                    <label className={labelClasses}><Trophy size={12} /> Experience Requirements</label>
                    <input
                      type="text"
                      placeholder="e.g. 3+ years"
                      className={inputClasses()}
                      value={formData.experience_requirements}
                      onChange={(e) => setFormData({ ...formData, experience_requirements: e.target.value })}
                    />
                  </div>

                  <div>
                    <label className={labelClasses}><Award size={12} /> Certifications</label>
                    <input
                      type="text"
                      placeholder="e.g. PMP, AWS"
                      className={inputClasses()}
                      value={formData.certifications_requirements}
                      onChange={(e) => setFormData({ ...formData, certifications_requirements: e.target.value })}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="px-10 py-8 border-t border-gray-50 bg-gray-50/30 flex items-center justify-between sticky bottom-0 z-10 backdrop-blur-md">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-6 py-3.5 rounded-2xl text-sm font-bold text-gray-400 hover:bg-white hover:text-red-500 transition-all active:scale-95"
              >
                Cancel
              </button>
              {currentStep > 1 && (
                <button
                  type="button"
                  onClick={prevStep}
                  className="flex items-center gap-2 px-6 py-3.5 rounded-2xl text-sm font-bold text-gray-500 hover:bg-white hover:text-gray-900 transition-all active:scale-95 border border-transparent hover:border-gray-100"
                >
                  <ChevronLeft size={18} /> Back
                </button>
              )}
            </div>

            <div className="flex gap-3">
              {currentStep < 3 ? (
                <button
                  key="continue-btn"
                  type="button"
                  onClick={nextStep}
                  className="flex items-center gap-2 px-8 py-3.5 bg-gray-900 text-white rounded-2xl text-sm font-bold hover:bg-black transition-all shadow-lg active:scale-95"
                >
                  Continue <ChevronRight size={18} />
                </button>
              ) : (
                <button
                  key="submit-btn"
                  type="submit"
                  disabled={isCreating}
                  className="flex items-center gap-2 px-10 py-3.5 bg-[#d81159] text-white rounded-2xl text-sm font-black hover:opacity-90 transition-all shadow-[0_10px_20px_rgba(216,17,89,0.2)] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCreating ? (
                    <><Loader2 size={18} className="animate-spin" /> Publishing...</>
                  ) : (
                    <><Sparkles size={18} /> Publish Position</>
                  )}
                </button>
              )}
            </div>
          </div>
        </form>
      </div>
      
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #f1f1f1;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #e5e5e5;
        }
      `}</style>
    </div>
  );
};

export default CreateJobModal;