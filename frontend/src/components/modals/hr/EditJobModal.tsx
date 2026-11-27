import React, { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  X, Briefcase, MapPin, Building2, DollarSign, 
  ListChecks, FileText, Loader2, CheckCircle2, 
  AlertCircle, ChevronRight, ChevronLeft, Info,
  Trophy, Target, Sparkles, GraduationCap, Award
} from 'lucide-react';

import { useUpdateJobMutation, useRecalculateJobScoresMutation, useGetMatchingConfigQuery } from '../../../redux/api/apiSlice';
import { useAppSelector } from '../../../redux/store';
import api from '../../../services/api';
import { Job, JobScoringWeights, DEFAULT_JOB_SCORING_WEIGHTS } from '../../../types';
import { cleanRequirementInput } from '../../../utils/criterionStatus';
import JobScoringWeightsEditor, { isWeightsBalanced, areWeightsEqual } from './JobScoringWeightsEditor';
import { SelectWithOther, MultiSelectDropdownWithOther } from '../../common/SelectWithOther';
import {
  COMMON_JOB_TITLES,
  JOB_DEPARTMENTS,
  JOB_WORK_LOCATIONS,
  SALARY_RANGE_OPTIONS,
  SKILL_OPTIONS,
  JOB_EDUCATION_REQUIREMENTS,
  JOB_EXPERIENCE_REQUIREMENTS,
  CERTIFICATION_OPTIONS,
} from '../../../data/formOptions';

interface EditJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: any) => void;
  jobData: Job | null;
}

interface EditFormDataState {
  job_id: string;
  job_title: string;
  department: string;
  location: string;
  job_type: string;
  salary_range: string;
  description: string;
  skills_requirements: string;
  education_requirements: string;
  experience_requirements: string;
  certifications_requirements: string;
  is_active: boolean;
  scoring_weights: JobScoringWeights;
}

const EditJobModal: React.FC<EditJobModalProps> = ({ isOpen, onClose, onSuccess, jobData }) => {
  const role = useAppSelector((state) => state.auth.role);
  const isAdmin = String(role || '').toUpperCase() === 'ADMIN';
  const totalSteps = isAdmin ? 4 : 3;
  const { data: matchingConfig } = useGetMatchingConfigQuery(undefined, {
    skip: !isOpen || !isAdmin,
  });
  const globalDefaultWeights: JobScoringWeights = {
    skills_weight: matchingConfig?.weights?.skills_weight ?? DEFAULT_JOB_SCORING_WEIGHTS.skills_weight,
    experience_weight: matchingConfig?.weights?.experience_weight ?? DEFAULT_JOB_SCORING_WEIGHTS.experience_weight,
    education_weight: matchingConfig?.weights?.education_weight ?? DEFAULT_JOB_SCORING_WEIGHTS.education_weight,
    certifications_weight: matchingConfig?.weights?.certifications_weight ?? DEFAULT_JOB_SCORING_WEIGHTS.certifications_weight,
    completeness_weight: matchingConfig?.weights?.completeness_weight ?? DEFAULT_JOB_SCORING_WEIGHTS.completeness_weight,
  };

  const [updateJob, { isLoading: isUpdating }] = useUpdateJobMutation();
  const [recalculateJobScores, { isLoading: isRecalculating }] = useRecalculateJobScoresMutation();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [status, setStatus] = useState<{ type: 'success' | 'error' | null; message: string }>({ type: null, message: '' });
  const [showRescoreConfirm, setShowRescoreConfirm] = useState<boolean>(false);
  const [rescoreProgress, setRescoreProgress] = useState<{ percent: number; label: string } | null>(null);
  const [formData, setFormData] = useState<EditFormDataState>({
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
    is_active: true,
    scoring_weights: { ...DEFAULT_JOB_SCORING_WEIGHTS }
  });

  const [errors, setErrors] = useState<Record<string, string | null>>({});

  const [prevJobData, setPrevJobData] = useState<Job | null>(null);
  const [prevIsOpen, setPrevIsOpen] = useState<boolean>(isOpen);

  if (isOpen !== prevIsOpen || (isOpen && jobData !== prevJobData)) {
    setPrevIsOpen(isOpen);
    setPrevJobData(jobData);
    if (isOpen && jobData) {
      setFormData({
        job_id: String(jobData.job_id || ''),
        job_title: jobData.job_title || jobData.title || '',
        department: jobData.department || 'Human Resources',
        location: jobData.location || '',
        job_type: jobData.job_type || 'Full-Time',
        salary_range: jobData.salary_range || '',
        description: jobData.description || '',
        skills_requirements: Array.isArray(jobData.skills_requirements) 
          ? jobData.skills_requirements.join(', ') 
          : cleanRequirementInput(jobData.skills_requirements),
        education_requirements: cleanRequirementInput(jobData.education_requirements),
        experience_requirements: cleanRequirementInput(jobData.experience_requirements),
        certifications_requirements: cleanRequirementInput(jobData.certifications_requirements),
        is_active: jobData.is_active ?? true,
        scoring_weights: jobData.scoring_weights
          ? { ...jobData.scoring_weights }
          : { ...globalDefaultWeights }
      });
      setStatus({ type: null, message: '' });
      setCurrentStep(1);
      setErrors({});
      setShowRescoreConfirm(false);
      setRescoreProgress(null);
    }
  }

  const validateStep = (step: number) => {
    const newErrors: Record<string, string | null> = {};
    if (step === 1) {
      if (!formData.job_title) newErrors.job_title = 'Job title is required';
      if (!formData.job_id) newErrors.job_id = 'Job ID is required';
    } else if (step === 2) {
      if (!formData.location) newErrors.location = 'Location is required';
      if (!formData.salary_range) newErrors.salary_range = 'Salary range is required';
    } else if (step === 3) {
      if (!formData.description) newErrors.description = 'Description is required';
      if (!formData.skills_requirements) newErrors.skills_requirements = 'Skills are required';
    } else if (step === 4) {
      if (isAdmin && !isWeightsBalanced(formData.scoring_weights)) {
        newErrors.scoring_weights = 'Scoring weights must add up to 100%.';
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, totalSteps));
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  const formatCurrency = (value: string) => {
    const digits = value.replace(/\D/g, '');
    if (!digits) return '';
    const formatted = new Intl.NumberFormat('en-PH').format(Number(digits));
    return `₱${formatted}`;
  };

  const handleSalaryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
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

    setFormData(prev => ({ ...prev, salary_range: formattedValue }));
    setErrors(prev => (prev.salary_range ? { ...prev, salary_range: null } : prev));
  };

  const initialWeights: JobScoringWeights = jobData?.scoring_weights
    ? { ...jobData.scoring_weights }
    : { ...globalDefaultWeights };
  const weightsWereChanged = isAdmin && !areWeightsEqual(formData.scoring_weights, initialWeights);
  const existingApplicantsCount = jobData?.applicant_count ?? 0;

  const performSave = async (shouldRescoreExisting: boolean) => {
    setStatus({ type: null, message: '' });

    try {
      const normalizedForm = {
        ...formData,
        skills_requirements: cleanRequirementInput(formData.skills_requirements),
        education_requirements: cleanRequirementInput(formData.education_requirements),
        experience_requirements: cleanRequirementInput(formData.experience_requirements),
        certifications_requirements: cleanRequirementInput(formData.certifications_requirements),
      };
      const body = isAdmin
        ? normalizedForm
        : (({ scoring_weights: _ignored, ...rest }) => rest)(normalizedForm);
      const result = await updateJob({
        jobId: formData.job_id,
        body,
      }).unwrap();

      if (shouldRescoreExisting) {
        setRescoreProgress({ percent: 10, label: 'Starting score recalculation...' });
        const recalcRes = await recalculateJobScores(formData.job_id).unwrap();

        if (recalcRes?.task_id) {
          for (let attempt = 0; attempt < 30; attempt++) {
            await new Promise((r) => setTimeout(r, 1000));
            const taskRes = await api.get(`/admins/tasks/${recalcRes.task_id}`);
            const taskData = taskRes.data;
            if (taskData?.progress?.percent !== undefined) {
              setRescoreProgress({
                percent: taskData.progress.percent,
                label: `Updating ${taskData.progress.current} of ${taskData.progress.total} applications...`,
              });
            }
            if (taskData?.status === 'FAILURE' || (taskData?.ready && taskData?.successful === false)) {
              const errDetail =
                typeof taskData?.result === 'string' && taskData.result
                  ? taskData.result
                  : 'Score recalculation failed in background worker.';
              throw new Error(errDetail);
            }
            if (taskData?.ready) {
              setRescoreProgress({ percent: 100, label: 'All application scores updated!' });
              break;
            }
          }
        }
      }

      setShowRescoreConfirm(false);
      setRescoreProgress(null);
      setStatus({
        type: 'success',
        message: shouldRescoreExisting
          ? `Job updated and ${existingApplicantsCount} application score(s) recalculated.`
          : 'Job posting has been updated successfully!',
      });

      setTimeout(() => {
        if (onSuccess) onSuccess(result);
        onClose();
      }, 1500);
    } catch (err: any) {
      setShowRescoreConfirm(false);
      setRescoreProgress(null);
      const errorMessage = err?.data?.detail || 'An error occurred while updating the job.';
      setStatus({ type: 'error', message: errorMessage });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (currentStep < totalSteps) {
      nextStep();
      return;
    }

    if (!validateStep(totalSteps)) return;

    if (weightsWereChanged && existingApplicantsCount > 0) {
      setShowRescoreConfirm(true);
      return;
    }

    await performSave(false);
  };

  if (!isOpen) return null;

  const inputClasses = (hasError?: boolean | string | null) => `w-full px-4 py-3 bg-gray-50 border ${hasError ? 'border-red-300 ring-1 ring-red-50' : 'border-gray-200'} rounded-xl text-sm focus:outline-none focus:border-[#d81159] focus:ring-4 focus:ring-pink-50 transition-all duration-200`;
  const labelClasses = "flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-700 mb-2 ml-1";

  const renderStepIndicator = () => {
    const steps = isAdmin ? [1, 2, 3, 4] : [1, 2, 3];
    const stepLabels: Record<number, string> = {
      1: 'General',
      2: 'Details',
      3: 'Requirements',
      4: 'Weights',
    };
    return (
      <div className="px-4 sm:px-8 pt-4 sm:pt-6 pb-2">
        <div className="flex items-center justify-between relative">
          <div className="absolute top-1/2 left-0 w-full h-0.5 bg-gray-100 -translate-y-1/2 z-0" />
          <div 
            className="absolute top-1/2 left-0 h-0.5 bg-gradient-to-r from-[#d81159] to-pink-400 -translate-y-1/2 z-0 transition-all duration-500 ease-out" 
            style={{ width: `${((currentStep - 1) / (totalSteps - 1)) * 100}%` }}
          />
          
          {steps.map((step) => (
            <div key={step} className="relative z-10 flex flex-col items-center">
              <div 
                className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center border-2 sm:border-4 transition-all duration-300 ${
                  currentStep >= step 
                    ? 'bg-white border-[#d81159] text-[#d81159] shadow-md sm:shadow-lg shadow-pink-100' 
                    : 'bg-white border-gray-100 text-gray-300'
                }`}
              >
                {currentStep > step ? <CheckCircle2 size={16} className="sm:w-5 sm:h-5 fill-[#d81159] text-white" /> : <span className="font-bold text-xs sm:text-sm">{step}</span>}
              </div>
              <span className={`mt-1.5 sm:mt-2 text-[9px] sm:text-[10px] font-bold uppercase tracking-tighter ${currentStep >= step ? 'text-[#d81159]' : 'text-gray-400'}`}>
                {stepLabels[step]}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-md transition-opacity duration-300">
      <Helmet>
        <title>Editing: {formData.job_title || 'Position'} | HR Portal</title>
      </Helmet>
      <div className="bg-white w-full max-w-2xl rounded-2xl sm:rounded-3xl shadow-[0_20px_50px_rgba(0,0,0,0.1)] overflow-hidden animate-in fade-in zoom-in duration-300 max-h-[92vh] sm:max-h-[90vh] flex flex-col relative border border-white/20">
        
        {showRescoreConfirm && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="rescore-confirm-title"
            className="absolute inset-0 z-[110] flex items-center justify-center p-4 sm:p-6 bg-white/95 backdrop-blur-sm animate-in fade-in duration-200"
          >
            <div className="max-w-md w-full p-6 sm:p-8 rounded-2xl sm:rounded-3xl bg-white border border-gray-200 shadow-2xl space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-amber-50 text-amber-600 shrink-0">
                  <AlertCircle size={24} />
                </div>
                <div>
                  <h3 id="rescore-confirm-title" className="text-lg font-black text-gray-900">
                    Update existing application scores?
                  </h3>
                  <p className="text-xs sm:text-sm text-gray-600 mt-1">
                    This will update the match scores of <strong>{existingApplicantsCount}</strong> application{existingApplicantsCount === 1 ? '' : 's'} for this job.
                  </p>
                </div>
              </div>

              <p className="text-xs text-gray-500">
                Application statuses and shortlist rosters will not be changed.
              </p>

              {rescoreProgress && (
                <div className="space-y-1.5 bg-gray-50 p-3 rounded-xl border border-gray-100">
                  <div className="flex justify-between text-xs font-bold text-gray-700">
                    <span>{rescoreProgress.label}</span>
                    <span>{rescoreProgress.percent}%</span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#d81159] transition-all duration-300"
                      style={{ width: `${rescoreProgress.percent}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="flex flex-col gap-2 pt-2">
                <button
                  type="button"
                  disabled={isUpdating || isRecalculating}
                  onClick={() => performSave(true)}
                  className="w-full py-3 px-4 bg-[#d81159] text-white rounded-xl text-xs sm:text-sm font-bold hover:opacity-90 transition-all disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
                >
                  {(isUpdating || isRecalculating) && <Loader2 size={15} className="animate-spin" />}
                  Update scores now
                </button>
                <button
                  type="button"
                  disabled={isUpdating || isRecalculating}
                  onClick={() => performSave(false)}
                  className="w-full py-3 px-4 bg-gray-100 text-gray-800 rounded-xl text-xs sm:text-sm font-bold hover:bg-gray-200 transition-all disabled:opacity-50 cursor-pointer"
                >
                  Apply to new applications only
                </button>
                <button
                  type="button"
                  disabled={isUpdating || isRecalculating}
                  onClick={() => setShowRescoreConfirm(false)}
                  className="w-full py-2 text-xs font-semibold text-gray-400 hover:text-gray-600 cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {status.type && (
          <div className="absolute inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-white/95 backdrop-blur-sm animate-in fade-in duration-300">
            <div className={`relative max-w-sm w-full p-6 sm:p-10 rounded-2xl sm:rounded-3xl text-center shadow-2xl border ${status.type === 'success' ? 'bg-emerald-50/50 border-emerald-100' : 'bg-red-50/50 border-red-100'}`}>
              <button
                onClick={() => setStatus({ type: null, message: '' })}
                className="absolute top-4 right-4 p-2 rounded-full hover:bg-black/5 text-gray-400 transition-colors"
              >
                <X size={18} />
              </button>
              <div className="flex justify-center mb-4 sm:mb-6">
                <div className={`p-3 sm:p-4 rounded-2xl ${status.type === 'success' ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'}`}>
                  {status.type === 'success' ? <Trophy size={36} className="sm:w-12 sm:h-12" /> : <AlertCircle size={36} className="sm:w-12 sm:h-12" />}
                </div>
              </div>
              <h3 className={`text-xl sm:text-2xl font-black mb-2 sm:mb-3 ${status.type === 'success' ? 'text-emerald-900' : 'text-red-900'}`}>
                {status.type === 'success' ? 'Updated!' : 'Oops!'}
              </h3>
              <p className={`text-sm sm:text-base font-medium leading-relaxed ${status.type === 'success' ? 'text-emerald-700/80' : 'text-red-700/80'}`}>
                {status.message}
              </p>
              {status.type === 'error' && (
                <button
                  onClick={() => setStatus({ type: null, message: '' })}
                  className="mt-6 sm:mt-8 w-full py-3 sm:py-4 bg-white border border-red-200 text-red-600 rounded-xl sm:rounded-2xl text-xs sm:text-sm font-bold hover:bg-red-50 transition-all shadow-sm active:scale-95"
                >
                  Try Again
                </button>
              )}
            </div>
          </div>
        )}

        <div className="px-4 sm:px-8 md:px-10 py-4 sm:py-6 md:py-7 border-b border-gray-50 flex justify-between items-center bg-white/80 backdrop-blur-md sticky top-0 z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-6 sm:w-8 h-1 sm:h-1.5 bg-[#d81159] rounded-full" />
              <span className="text-[9px] sm:text-[10px] font-black uppercase tracking-[0.2em] text-[#d81159]">Job Portal</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-gray-900 tracking-tight">Edit Position</h2>
          </div>
          <button 
            onClick={onClose} 
            className="group p-2 sm:p-3 hover:bg-red-50 rounded-xl sm:rounded-2xl transition-all duration-300 text-gray-400 hover:text-red-500 cursor-pointer"
          >
            <X size={20} className="group-hover:rotate-90 transition-transform duration-300" />
          </button>
        </div>

        {renderStepIndicator()}

        <form 
          onSubmit={handleSubmit} 
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.target as HTMLElement).tagName !== 'TEXTAREA') {
              e.preventDefault();
              if (currentStep < totalSteps) {
                nextStep();
              }
            }
          }}
          className="flex-1 overflow-y-auto custom-scrollbar"
        >
          <div className="p-4 sm:p-6 md:p-10">
            {currentStep === 1 && (
              <div className="space-y-4 sm:space-y-6 animate-in slide-in-from-right-4 duration-500">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                  <div className="md:col-span-2">
                    <SelectWithOther
                      id="edit-job-title"
                      label={<span className="inline-flex items-center gap-2"><Briefcase size={12} /> Job Title</span>}
                      labelClassName={labelClasses}
                      selectClassName={`${inputClasses(errors.job_title)} appearance-none pr-10 cursor-pointer`}
                      value={formData.job_title}
                      onChange={(val) => {
                        setFormData(prev => ({ ...prev, job_title: val }));
                        setErrors(prev => (prev.job_title ? { ...prev, job_title: null } : prev));
                      }}
                      options={COMMON_JOB_TITLES}
                      placeholder="Select a job title..."
                      otherPlaceholder="Enter custom job title..."
                      required
                      error={errors.job_title}
                    />
                  </div>

                  <div>
                    <label className={labelClasses}><Target size={12} /> Job ID (Read-only)</label>
                    <input
                      disabled
                      type="text"
                      className={`${inputClasses(errors.job_id)} opacity-60 cursor-not-allowed`}
                      value={formData.job_id}
                    />
                  </div>

                  <div>
                    <SelectWithOther
                      id="edit-job-department"
                      label={<span className="inline-flex items-center gap-2"><Building2 size={12} /> Department</span>}
                      labelClassName={labelClasses}
                      selectClassName={`${inputClasses()} appearance-none pr-10 cursor-pointer`}
                      value={formData.department}
                      onChange={(val) => setFormData(prev => ({ ...prev, department: val }))}
                      options={JOB_DEPARTMENTS}
                      allowEmpty={false}
                      otherPlaceholder="Enter custom department..."
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className={labelClasses}>Job Type</label>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 sm:gap-3">
                      {['Full-Time', 'Part-Time', 'Contract', 'Freelance', 'Internship'].map((type) => (
                        <button
                          key={type}
                          type="button"
                          onClick={() => setFormData(prev => ({ ...prev, job_type: type }))}
                          className={`py-2.5 sm:py-3 px-3 sm:px-4 rounded-xl text-xs font-bold transition-all border ${
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

            {currentStep === 2 && (
              <div className="space-y-4 sm:space-y-6 animate-in slide-in-from-right-4 duration-500">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                  <div className="md:col-span-2">
                    <SelectWithOther
                      id="edit-job-location"
                      label={<span className="inline-flex items-center gap-2"><MapPin size={12} /> Work Location</span>}
                      labelClassName={labelClasses}
                      selectClassName={`${inputClasses(errors.location)} appearance-none pr-10 cursor-pointer`}
                      value={formData.location}
                      onChange={(val) => {
                        setFormData(prev => ({ ...prev, location: val }));
                        setErrors(prev => (prev.location ? { ...prev, location: null } : prev));
                      }}
                      options={JOB_WORK_LOCATIONS}
                      placeholder="Select work location..."
                      otherPlaceholder="e.g. Sto. Tomas, Batangas (On-site)"
                      required
                      error={errors.location}
                    />
                  </div>

                  <div className="md:col-span-2">
                    <SelectWithOther
                      id="edit-job-salary"
                      label={<span className="inline-flex items-center gap-2"><DollarSign size={12} /> Salary Range (Monthly PHP)</span>}
                      labelClassName={labelClasses}
                      selectClassName={`${inputClasses(errors.salary_range)} appearance-none pr-10 cursor-pointer`}
                      value={formData.salary_range}
                      onChange={(val) => {
                        setFormData(prev => ({ ...prev, salary_range: val }));
                        setErrors(prev => (prev.salary_range ? { ...prev, salary_range: null } : prev));
                      }}
                      options={SALARY_RANGE_OPTIONS}
                      placeholder="Select monthly salary bracket..."
                      otherPlaceholder="e.g. ₱50,000 - ₱80,000"
                      required
                      error={errors.salary_range}
                    />
                  </div>

                  <div className="md:col-span-2 mt-2 sm:mt-4">
                    <div className="p-4 sm:p-6 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-100 flex items-center justify-between">
                      <div>
                        <span className="text-xs sm:text-sm font-black text-gray-800 block mb-0.5">Visibility Status</span>
                        <span className="text-[10px] sm:text-[11px] text-gray-400 font-medium">Make this post live immediately?</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, is_active: !prev.is_active }))}
                        className={`relative inline-flex h-6 sm:h-7 w-11 sm:w-12 items-center rounded-full transition-all duration-300 ${
                          formData.is_active ? 'bg-emerald-500 shadow-lg shadow-emerald-100' : 'bg-gray-200'
                        }`}
                      >
                        <span className={`inline-block h-4 sm:h-5 w-4 sm:w-5 transform rounded-full bg-white shadow-sm transition-transform duration-300 ${
                          formData.is_active ? 'translate-x-6 sm:translate-x-6' : 'translate-x-1'
                        }`} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {currentStep === 3 && (
              <div className="space-y-4 sm:space-y-6 animate-in slide-in-from-right-4 duration-500">
                <div>
                  <label className={labelClasses}><FileText size={12} /> Position Description</label>
                  <textarea
                    autoFocus
                    required
                    rows={5}
                    placeholder="Describe the role, responsibilities, and team environment..."
                    className={`${inputClasses(errors.description)} resize-none leading-relaxed`}
                    value={formData.description}
                    onChange={(e) => {
                      const val = e.target.value;
                      setFormData(prev => ({ ...prev, description: val }));
                      setErrors(prev => (prev.description ? { ...prev, description: null } : prev));
                    }}
                  />
                </div>

                <div>
                  <MultiSelectDropdownWithOther
                    id="edit-job-skills"
                    label={<span className="inline-flex items-center gap-2"><ListChecks size={12} /> Key Skills &amp; Requirements</span>}
                    labelClassName={labelClasses}
                    selectClassName={`${inputClasses(errors.skills_requirements)} appearance-none pr-10 cursor-pointer`}
                    selectedItems={formData.skills_requirements.split(',').map((s) => s.trim()).filter(Boolean)}
                    onChange={(items) => {
                      setFormData(prev => ({ ...prev, skills_requirements: items.join(', ') }));
                      setErrors(prev => (prev.skills_requirements ? { ...prev, skills_requirements: null } : prev));
                    }}
                    options={SKILL_OPTIONS}
                    placeholder="Select required skills from dropdown..."
                    otherPlaceholder="Enter custom required skill..."
                    error={errors.skills_requirements}
                    emptyStateText="Select at least one required skill from the dropdown above."
                    chipClassName="inline-flex items-center gap-1.5 px-2.5 py-1 bg-pink-50 text-[#d81159] text-xs font-bold rounded-full border border-pink-100"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6">
                  <div>
                    <SelectWithOther
                      id="edit-job-education"
                      label={<span className="inline-flex items-center gap-2"><GraduationCap size={12} /> Education</span>}
                      labelClassName={labelClasses}
                      selectClassName={`${inputClasses()} appearance-none pr-10 cursor-pointer`}
                      value={formData.education_requirements}
                      onChange={(val) => setFormData(prev => ({ ...prev, education_requirements: val === 'None' ? '' : val }))}
                      options={JOB_EDUCATION_REQUIREMENTS}
                      placeholder="Select education..."
                      otherPlaceholder="Specify required degree..."
                      helperText="Select 'None' if not required."
                    />
                  </div>

                  <div>
                    <SelectWithOther
                      id="edit-job-experience"
                      label={<span className="inline-flex items-center gap-2"><Trophy size={12} /> Experience</span>}
                      labelClassName={labelClasses}
                      selectClassName={`${inputClasses()} appearance-none pr-10 cursor-pointer`}
                      value={formData.experience_requirements}
                      onChange={(val) =>
                        setFormData(prev => ({
                          ...prev,
                          experience_requirements: val.startsWith('None') ? '' : val,
                        }))
                      }
                      options={JOB_EXPERIENCE_REQUIREMENTS}
                      placeholder="Select experience..."
                      otherPlaceholder="e.g. 4+ years in QA"
                      helperText="Select 'None' if open to fresh grads."
                    />
                  </div>

                  <div className="sm:col-span-2 md:col-span-1">
                    <MultiSelectDropdownWithOther
                      id="edit-job-certifications"
                      label={<span className="inline-flex items-center gap-2"><Award size={12} /> Certifications</span>}
                      labelClassName={labelClasses}
                      selectClassName={`${inputClasses()} appearance-none pr-10 cursor-pointer`}
                      selectedItems={formData.certifications_requirements.split(',').map((s) => s.trim()).filter(Boolean)}
                      onChange={(items) =>
                        setFormData(prev => ({ ...prev, certifications_requirements: items.join(', ') }))
                      }
                      options={CERTIFICATION_OPTIONS}
                      placeholder="Select certifications (optional)..."
                      otherPlaceholder="Specify license/certification..."
                      emptyStateText="None required."
                      chipClassName="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 text-slate-700 text-[11px] font-bold rounded-full border border-slate-200"
                    />
                  </div>
                </div>

                {!isAdmin && (
                  <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 flex items-start gap-2.5">
                    <Info size={15} className="text-slate-400 shrink-0 mt-0.5" />
                    <span>
                      Scoring weights for this position are managed by Administrators.
                    </span>
                  </div>
                )}
              </div>
            )}

            {isAdmin && currentStep === 4 && (
              <div className="space-y-4 animate-in slide-in-from-right-4 duration-500">
                <div className="p-4 rounded-2xl bg-pink-50/50 border border-pink-100">
                  <h3 className="text-sm font-black text-gray-900">Per-Job Scoring Weights</h3>
                  <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">
                    Adjust how much each criterion counts toward candidate match scores for this specific job posting.
                  </p>
                </div>

                <JobScoringWeightsEditor
                  weights={formData.scoring_weights}
                  defaultWeights={globalDefaultWeights}
                  defaultExpanded={true}
                  onChange={(next) => {
                    setFormData(prev => ({ ...prev, scoring_weights: next }));
                    setErrors(prev => (prev.scoring_weights ? { ...prev, scoring_weights: null } : prev));
                  }}
                  error={errors.scoring_weights}
                />
              </div>
            )}
          </div>

          <div className="px-4 sm:px-8 md:px-10 py-3.5 sm:py-6 md:py-8 border-t border-gray-50 bg-gray-50/30 flex items-center justify-between sticky bottom-0 z-10 backdrop-blur-md gap-2">
            <div className="flex items-center gap-1 sm:gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 sm:px-6 py-2.5 sm:py-3.5 rounded-xl sm:rounded-2xl text-xs sm:text-sm font-bold text-gray-400 hover:bg-white hover:text-red-500 transition-all active:scale-95 cursor-pointer"
              >
                Cancel
              </button>
              {currentStep > 1 && (
                <button
                  type="button"
                  onClick={prevStep}
                  className="flex items-center gap-1 sm:gap-2 px-3 sm:px-6 py-2.5 sm:py-3.5 rounded-xl sm:rounded-2xl text-xs sm:text-sm font-bold text-gray-500 hover:bg-white hover:text-gray-900 transition-all active:scale-95 border border-transparent hover:border-gray-100 cursor-pointer"
                >
                  <ChevronLeft size={16} /> Back
                </button>
              )}
            </div>

            <div className="flex gap-2 sm:gap-3">
              {currentStep < totalSteps ? (
                <button
                  key="continue-btn"
                  type="button"
                  onClick={nextStep}
                  className="flex items-center gap-1.5 sm:gap-2 px-4 sm:px-8 py-2.5 sm:py-3.5 bg-gray-900 text-white rounded-xl sm:rounded-2xl text-xs sm:text-sm font-bold hover:bg-black transition-all shadow-lg active:scale-95 cursor-pointer"
                >
                  <span>Continue</span> <ChevronRight size={16} />
                </button>
              ) : (
                <button
                  key="submit-btn"
                  type="submit"
                  disabled={isUpdating || (isAdmin && !isWeightsBalanced(formData.scoring_weights))}
                  className="flex items-center gap-1.5 sm:gap-2 px-4 sm:px-10 py-2.5 sm:py-3.5 bg-[#d81159] text-white rounded-xl sm:rounded-2xl text-xs sm:text-sm font-black hover:opacity-90 transition-all shadow-[0_10px_20px_rgba(216,17,89,0.2)] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {isUpdating ? (
                    <><Loader2 size={16} className="animate-spin" /> Saving...</>
                  ) : (
                    <><Sparkles size={16} /> Save Changes</>
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

export default EditJobModal;
