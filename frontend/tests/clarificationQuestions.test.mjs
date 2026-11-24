import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const compile = source => `data:text/javascript;base64,${Buffer.from(ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
}).outputText).toString('base64')}`;
const criterionUrl = compile(await readFile(new URL('../src/utils/criterionStatus.ts', import.meta.url), 'utf8'));
const source = (await readFile(new URL('../src/utils/clarificationQuestions.ts', import.meta.url), 'utf8'))
  .replace("'./criterionStatus'", JSON.stringify(criterionUrl));
const { deriveClarificationQuestions, buildCandidateMatchPayload, collectClarificationResponses, hasCompleteJobRequirements } = await import(compile(source));
const job = { job_id: 'JOB-1', title: 'Support', skills_requirements: 'A, B, C, D, E, CRM software, Data Entry, Problem-Solving' };
const form = { skills: ['Problem Solving'], relevance: '', jobTitle: '', company: '', degree: '', college: '', fullName: 'Test', location: '' };

test('a skills-only job snapshot still needs full requirements fetched', () => {
  assert.equal(hasCompleteJobRequirements(job), false);
  assert.equal(hasCompleteJobRequirements({ ...job, certifications_requirements: null, experience_requirements: '' }), true);
});

test('fallback includes every unresolved requirement without substring matches or a five-item cap', () => {
  const questions = deriveClarificationQuestions({ job }, form);
  const skills = questions.find(q => q.field === 'skills');
  assert.equal(skills.type, 'requirement_group');
  assert.deepEqual(skills.items.map(i => i.requirement), ['A', 'B', 'C', 'D', 'E', 'CRM software', 'Data Entry']);
});

test('backend grouped items and possible-match evidence survive question normalization', () => {
  const items = [{ field: 'skills', requirement: 'CRM software', status: 'Possible match', evidence: ['Kustomer'] }];
  const questions = deriveClarificationQuestions({ job, matchData: { job_id: 'JOB-1', followup_questions: [
    { id: 'crm', field: 'skills', type: 'requirement_group', question: 'Confirm skills', items },
  ] } }, form);
  assert.deepEqual(questions[0].items, items);
  const allItems = questions.flatMap(q => q.items || []).map(item => item.requirement);
  assert.ok(allItems.includes('Data Entry'));
  assert.equal(allItems.filter(item => item === 'CRM software').length, 1);
});

test('legacy text questions cannot suppress the full requirement checklist', () => {
  const questions = deriveClarificationQuestions({ job, matchData: { job_id: 'JOB-1', followup_questions: [
    { id: 'clarify_job_1_skills', field: 'skills', question: 'Do you know A, B, C, D or E?' },
  ] } }, form);
  const requirements = questions.flatMap(q => q.items || []).map(item => item.requirement);
  assert.ok(requirements.includes('CRM software'));
  assert.ok(requirements.includes('Data Entry'));
  assert.equal(new Set(questions.map(q => q.id)).size, questions.length);
});

test('partial groups keep their answer ids and merge missing items without duplicates', () => {
  const questions = deriveClarificationQuestions({ job, matchData: { job_id: 'JOB-1', followup_questions: [
    { id: 'clarify_job_1_skills', field: 'skills', type: 'requirement_group', question: 'Confirm skills',
      items: [{ field: 'skills', requirement: 'CRM software', status: 'Possible match', evidence: ['Kustomer'] }] },
  ] } }, form);
  const groups = questions.filter(q => q.type === 'requirement_group' && q.field === 'skills');
  assert.equal(groups.length, 1);
  assert.equal(groups[0].items.length, 7);
  assert.deepEqual(collectClarificationResponses(questions, {
    clarify_job_1_skills: JSON.stringify({ 'CRM software': { answer: 'yes' } }),
  }), [{ field: 'skills', requirement: 'CRM software', answer: 'yes' }]);
});

test('confident server certification evidence is not asked again by fallback coverage', () => {
  const target = { ...job, certifications_requirements: 'safety training (OSHA or BOSH)' };
  const questions = deriveClarificationQuestions({ job: target, matchData: { job_id: 'JOB-1', followup_questions: [
    { id: 'old', field: 'relevance', question: 'Describe your role' },
  ], requirement_evaluations: [
    { field: 'certifications', requirement: 'safety training (OSHA or BOSH)', source: 'Resume', status: 'Meets requirement' },
  ] } }, form);
  assert.ok(!questions.some(q => q.field === 'certifications'));
});

test('yes, some, no and optional details reach the API; edits do not leave stale positive skills', () => {
  const questions = deriveClarificationQuestions({ job }, form);
  const q = questions.find(q => q.field === 'skills');
  const answers = { [q.id]: JSON.stringify({ 'CRM software': { answer: 'yes', details: 'Kustomer', years: 2 }, 'Data Entry': { answer: 'some' } }) };
  let payload = buildCandidateMatchPayload(form, questions, answers, {});
  assert.equal(payload.clarification_responses.length, 2);
  assert.equal(payload.clarification_responses[0].details, 'Kustomer');
  answers[q.id] = JSON.stringify({ 'CRM software': { answer: 'no' } });
  payload = buildCandidateMatchPayload(form, questions, answers, {});
  assert.deepEqual(payload.skills_list, ['Problem Solving']);
  assert.deepEqual(payload.clarification_responses, [{ requirement: 'CRM software', field: 'skills', answer: 'no' }]);
  assert.deepEqual(collectClarificationResponses(questions, {}), []);
});

test('legacy skill answers use the same separators and hyphen normalization', () => {
  const questions = [{ id: 'legacy', field: 'skills', question: 'Skills?' }];
  const payload = buildCandidateMatchPayload(form, questions, {
    legacy: 'Problem-Solving / Wi-Fi • E-commerce; Point-of-Sale',
  }, {});
  assert.deepEqual(payload.skills_list, ['Problem Solving', 'Wi-Fi', 'E-commerce', 'Point-of-Sale']);
});
