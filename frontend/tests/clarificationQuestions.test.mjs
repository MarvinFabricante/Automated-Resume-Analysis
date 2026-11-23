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
const { deriveClarificationQuestions, buildCandidateMatchPayload, collectClarificationResponses } = await import(compile(source));
const job = { job_id: 'JOB-1', title: 'Support', skills_requirements: 'A, B, C, D, E, CRM software, Data Entry, Problem-Solving' };
const form = { skills: ['Problem Solving'], relevance: '', jobTitle: '', company: '', degree: '', college: '', fullName: 'Test', location: '' };

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
