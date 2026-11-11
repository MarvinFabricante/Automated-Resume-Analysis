'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import jobService from '../services/jobService';
import {
  ClarificationQuestion,
  deriveClarificationQuestions,
  getJobScopedState,
  mergeInitialJobMatch,
} from '../utils/clarificationQuestions';

interface UseJobClarificationsParams {
  jobId?: string;
  locationState: any;
  onJobChanged?: (scopedMatch: any) => void;
}

export function useJobClarifications({
  jobId,
  locationState,
  onJobChanged,
}: UseJobClarificationsParams) {
  const initialScoped = getJobScopedState(locationState, jobId);
  const [activeJob, setActiveJob] = useState<any>(initialScoped.job);
  const [initialJobMatch, setInitialJobMatch] = useState<any>(initialScoped.match);
  const [jobTitle, setJobTitle] = useState<string>(
    initialScoped.job?.job_title || initialScoped.job?.title || 'Position'
  );
  const [clarificationAnswers, setClarificationAnswers] = useState<Record<string, string>>(
    locationState?.clarificationAnswers || {}
  );

  const prevJobIdRef = useRef<string | undefined>(jobId);
  const onJobChangedRef = useRef(onJobChanged);
  onJobChangedRef.current = onJobChanged;

  useEffect(() => {
    let isMounted = true;
    const scoped = getJobScopedState(locationState, jobId);
    const jobChanged = prevJobIdRef.current !== jobId;

    if (jobChanged) {
      prevJobIdRef.current = jobId;
      setActiveJob(scoped.job);
      setInitialJobMatch(scoped.match);
      setClarificationAnswers(locationState?.clarificationAnswers || {});
      setJobTitle(scoped.job?.job_title || scoped.job?.title || 'Position');
      onJobChangedRef.current?.(scoped.match);
    } else {
      if (scoped.job) {
        setActiveJob((prev: any) => (prev?.skills_requirements ? prev : scoped.job));
      }
      if (scoped.match) {
        setInitialJobMatch((prev: any) => mergeInitialJobMatch(prev, scoped.match, jobId));
      }
    }

    const syncJobDetails = async () => {
      if (!jobId || jobId === 'smart') return;
      if (scoped.job?.job_title || scoped.job?.title) {
        setJobTitle(scoped.job.job_title || scoped.job.title);
      }
      if (scoped.job?.skills_requirements) return;

      try {
        const response = await jobService.getJobById(jobId);
        if (!isMounted || !response.data) return;
        const fetchedJob = {
          ...(scoped.job || {}),
          ...response.data,
          title: response.data.job_title || scoped.job?.title || 'Position',
        };
        setActiveJob(fetchedJob);
        setJobTitle(fetchedJob.title);
      } catch (err) {
        console.error('Failed to fetch job details for clarification questions:', err);
      }
    };

    syncJobDetails();
    return () => {
      isMounted = false;
    };
  }, [jobId, locationState]);

  const clarificationQuestions = useMemo<ClarificationQuestion[]>(() => {
    const initialSnapshot = {
      jobTitle:
        locationState?.experience?.title && locationState.experience.title !== 'null'
          ? locationState.experience.title
          : '',
      company:
        locationState?.experience?.company && locationState.experience.company !== 'null'
          ? locationState.experience.company
          : '',
      relevance:
        locationState?.experience?.relevance &&
        locationState.experience.relevance !== 'Experience not extracted'
          ? locationState.experience.relevance
          : '',
      degree:
        locationState?.education?.degree && locationState.education.degree !== 'null'
          ? locationState.education.degree
          : '',
      skills:
        Array.isArray(locationState?.skills) && locationState.skills[0] !== 'Extraction in progress'
          ? locationState.skills
          : [],
    };
    return deriveClarificationQuestions(locationState, initialSnapshot, activeJob, initialJobMatch);
  }, [activeJob, initialJobMatch, locationState]);

  const recordInitialMatch = useCallback(
    (nextMatch: any) => {
      setInitialJobMatch((prev: any) => mergeInitialJobMatch(prev, nextMatch, jobId));
    },
    [jobId]
  );

  return {
    activeJob,
    jobTitle,
    clarificationQuestions,
    clarificationAnswers,
    setClarificationAnswers,
    recordInitialMatch,
  };
}

