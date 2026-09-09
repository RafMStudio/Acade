'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const Core = require('../src/core.js');

const {
  GRADE_DEFS,
  blankSectionFor,
  expectedCombinedSnapshot,
  combinedIntegrityAudit,
  enforceCombinedIntegrity,
  gradeInflationForSection,
  reportGradeInflation,
  reportCloGaps,
  pooledGradeDistribution,
  reportAverageAttainment,
  calculatePloRollups,
  validateReport
} = Core;

function grades(overrides = {}) {
  return Object.fromEntries(GRADE_DEFS.map(([label]) => [label, overrides[label] || 0]));
}

function section({ start = 10, complete = 10, g = {}, actual = 75, comment = 'ok', gradeComment = 'Comment', gradeRecommendation = 'Recommendation' } = {}) {
  return {
    studentsStart: start,
    studentsComplete: complete,
    grades: grades(g),
    gradeComment,
    gradeRecommendation,
    cloRecommendation: '',
    cloResults: { '1.1': { actual, comment } }
  };
}

function report(overrides = {}) {
  const base = {
    id: 'r', courseCode: 'HIM401', courseName: 'Test Course', academicYear: '2026–2027', semester: 'S1',
    instructor: 'Test Instructor', reportDate: '2026-09-09', sectionMode: 'all', status: 'Draft',
    clos: [{ code: '1.1', domain: 'K', text: 'Explain something', plo: 'K1', method: 'Exam', target: 70 }],
    sectionData: {
      male: section({ start: 20, complete: 20, g: { 'A+': 4, A: 4, 'B+': 4, B: 4, C: 4 } }),
      female: section({ start: 15, complete: 15, g: { 'A+': 3, A: 3, 'B+': 3, B: 3, C: 3 } }),
      combined: section({ start: 0, complete: 0, g: {} })
    },
    improvements: []
  };
  return { ...base, ...overrides, sectionData: overrides.sectionData || base.sectionData, clos: overrides.clos || base.clos };
}

test('Combined adds every grade/status count exactly', () => {
  const r = report();
  const labels = GRADE_DEFS.map(([label]) => label);
  labels.forEach((label, index) => {
    r.sectionData.male.grades[label] = index + 1;
    r.sectionData.female.grades[label] = (index + 1) * 2;
  });
  const combined = expectedCombinedSnapshot(r);
  labels.forEach((label, index) => assert.equal(combined.grades[label], (index + 1) * 3, label));
});

test('Combined reproduces the reported 20 A+ + 15 A+ = 35 A+ case', () => {
  const r = report();
  r.sectionData.male.grades = grades({ 'A+': 20 });
  r.sectionData.female.grades = grades({ 'A+': 15 });
  assert.equal(expectedCombinedSnapshot(r).grades['A+'], 35);
});

test('Combined adds starting and completed student counts', () => {
  const r = report();
  r.sectionData.male.studentsStart = 23;
  r.sectionData.female.studentsStart = 31;
  r.sectionData.male.studentsComplete = 20;
  r.sectionData.female.studentsComplete = 29;
  const combined = expectedCombinedSnapshot(r);
  assert.equal(combined.studentsStart, 54);
  assert.equal(combined.studentsComplete, 49);
});

test('Combined CLO actual is weighted by completed students', () => {
  const r = report();
  r.sectionData.male.studentsComplete = 10;
  r.sectionData.female.studentsComplete = 20;
  r.sectionData.male.cloResults['1.1'].actual = 60;
  r.sectionData.female.cloResults['1.1'].actual = 90;
  assert.equal(expectedCombinedSnapshot(r).cloResults['1.1'].actual, 80);
});

test('Combined CLO stays blank until both source actuals exist', () => {
  const r = report();
  r.sectionData.male.cloResults['1.1'].actual = 80;
  r.sectionData.female.cloResults['1.1'].actual = '';
  assert.equal(expectedCombinedSnapshot(r).cloResults['1.1'].actual, '');
});

test('Combined comments preserve both distinct source comments', () => {
  const r = report();
  r.sectionData.male.gradeComment = 'Male note';
  r.sectionData.female.gradeComment = 'Female note';
  assert.equal(expectedCombinedSnapshot(r).gradeComment, 'Male: Male note\nFemale: Female note');
});

test('Combined audit detects corrupted numeric and text data', () => {
  const r = report();
  enforceCombinedIntegrity(r);
  r.sectionData.combined.grades['A+'] += 1;
  r.sectionData.combined.gradeComment = 'stale';
  const audit = combinedIntegrityAudit(r);
  assert.equal(audit.ok, false);
  assert.ok(audit.errors.some((e) => e.startsWith('A+:')));
  assert.ok(audit.errors.some((e) => e.startsWith('gradeComment:')));
});

test('A+ at exactly 20% triggers grade inflation', () => {
  const s = section({ start: 10, complete: 10, g: { 'A+': 2, B: 8 } });
  assert.equal(gradeInflationForSection(s).inflated, true);
});

test('A and above at exactly 60% does not trigger unless A+ rule also triggers', () => {
  const s = section({ start: 10, complete: 10, g: { 'A+': 1, A: 5, B: 4 } });
  const result = gradeInflationForSection(s);
  assert.equal(result.aOrAbovePct, 60);
  assert.equal(result.inflated, false);
});

test('A and above above 60% triggers grade inflation', () => {
  const s = section({ start: 10, complete: 10, g: { 'A+': 1, A: 6, B: 3 } });
  assert.equal(gradeInflationForSection(s).inflated, true);
});

test('All-scope Combined inflation requires source comments and recommendations', () => {
  const r = report();
  // Male 50% A-and-above, female 80%; Combined 65% while Male itself is not inflated.
  r.sectionData.male = section({ start: 10, complete: 10, g: { 'A+': 1, A: 4, B: 5 }, gradeComment: '', gradeRecommendation: '' });
  r.sectionData.female = section({ start: 10, complete: 10, g: { 'A+': 1, A: 7, B: 2 }, gradeComment: 'Female comment', gradeRecommendation: 'Female rec' });
  const errors = validateReport(r, { ploCodes: ['K1'] });
  assert.ok(reportGradeInflation(r).inflated);
  assert.ok(errors.some((e) => e.includes('Male Comment on Student Grades')));
  assert.ok(errors.some((e) => e.includes('Male Recommendations on Grades')));
});

test('Submission validation catches grade/status total mismatch', () => {
  const r = report({ sectionMode: 'combined' });
  r.sectionData.combined = section({ start: 10, complete: 10, g: { A: 9, B: 0 } });
  const errors = validateReport(r, { ploCodes: ['K1'] });
  assert.ok(errors.some((e) => e.includes('grade/status total (9) must equal students starting (10)')));
});

test('Submission validation reconciles completed students with terminal grades', () => {
  const r = report({ sectionMode: 'combined' });
  r.sectionData.combined = section({ start: 10, complete: 9, g: { A: 10 } });
  const errors = validateReport(r, { ploCodes: ['K1'] });
  assert.ok(errors.some((e) => e.includes('completed-grade total (10) must equal students completed (9)')));
});

test('Submission validation rejects fractional and negative grade counts', () => {
  const r = report({ sectionMode: 'combined' });
  r.sectionData.combined = section({ start: 10, complete: 10, g: { A: 10 } });
  r.sectionData.combined.grades.A = 9.5;
  r.sectionData.combined.grades.B = -0.5;
  const errors = validateReport(r, { ploCodes: ['K1'] });
  assert.ok(errors.some((e) => e.includes('A count must be a non-negative whole number')));
  assert.ok(errors.some((e) => e.includes('B count must be a non-negative whole number')));
});

test('Submission validation rejects bad CLO definitions', () => {
  const r = report({ sectionMode: 'combined' });
  r.sectionData.combined = section({ start: 10, complete: 10, g: { B: 10 } });
  r.clos[0] = { code: '1.1', domain: 'K', text: '', plo: 'UNKNOWN', method: '', target: 110 };
  r.sectionData.combined.cloResults['1.1'] = { actual: 70, comment: '' };
  const errors = validateReport(r, { ploCodes: ['K1'] });
  assert.ok(errors.some((e) => e.includes('description is required')));
  assert.ok(errors.some((e) => e.includes('assessment method is required')));
  assert.ok(errors.some((e) => e.includes('unknown PLO')));
  assert.ok(errors.some((e) => e.includes('target must be 0–100')));
});

test('CLO gap detection flags actual below target', () => {
  const r = report({ sectionMode: 'combined' });
  r.sectionData.combined = section({ start: 10, complete: 10, g: { B: 10 }, actual: 69 });
  assert.equal(reportCloGaps(r).length, 1);
});

test('Average CLO attainment reads the effective section, not stale flat fields', () => {
  const r = report({ sectionMode: 'combined' });
  r.clos[0].actual = 5; // stale flat value
  r.sectionData.combined = section({ start: 10, complete: 10, g: { B: 10 }, actual: 80 });
  assert.equal(reportAverageAttainment(r), 80);
});

test('PLO rollup uses approved reports only and weights by completed students', () => {
  const a = report({ id: 'a', status: 'Approved', sectionMode: 'combined' });
  a.sectionData.combined = section({ start: 10, complete: 10, g: { B: 10 }, actual: 60 });
  const b = report({ id: 'b', status: 'Approved', sectionMode: 'combined' });
  b.sectionData.combined = section({ start: 30, complete: 30, g: { B: 30 }, actual: 80 });
  const draft = report({ id: 'c', status: 'Draft', sectionMode: 'combined' });
  draft.sectionData.combined = section({ start: 100, complete: 100, g: { B: 100 }, actual: 0 });
  const result = calculatePloRollups([a, b, draft], [{ code: 'K1', name: 'K1', target: 70 }], '2026–2027', 'Annual')[0];
  assert.equal(result.actual, 75);
  assert.equal(result.rows.length, 2);
});

test('PLO rollup keeps semesters separate', () => {
  const s1 = report({ id: 's1', status: 'Approved', sectionMode: 'combined', semester: 'S1' });
  s1.sectionData.combined = section({ start: 10, complete: 10, g: { B: 10 }, actual: 60 });
  const s2 = report({ id: 's2', status: 'Approved', sectionMode: 'combined', semester: 'S2' });
  s2.sectionData.combined = section({ start: 10, complete: 10, g: { B: 10 }, actual: 90 });
  const plos = [{ code: 'K1', name: 'K1', target: 70 }];
  assert.equal(calculatePloRollups([s1, s2], plos, '2026–2027', 'S1')[0].actual, 60);
  assert.equal(calculatePloRollups([s1, s2], plos, '2026–2027', 'S2')[0].actual, 90);
  assert.equal(calculatePloRollups([s1, s2], plos, '2026–2027', 'Annual')[0].actual, 75);
});

test('Pooled grade distribution is student-weighted across courses', () => {
  const a = report({ sectionMode: 'combined' });
  a.sectionData.combined = section({ start: 10, complete: 10, g: { A: 10 } });
  const b = report({ sectionMode: 'combined' });
  b.sectionData.combined = section({ start: 30, complete: 30, g: { B: 30 } });
  const pooled = pooledGradeDistribution([a, b]);
  assert.equal(pooled.denominator, 40);
  assert.equal(pooled.percentages.A, 25);
  assert.equal(pooled.percentages.B, 75);
});

test('Average CLO attainment distinguishes no data from a real 0%', () => {
  const noData = report({ sectionMode: 'combined' });
  noData.sectionData.combined = section({ start: 10, complete: 10, g: { B: 10 }, actual: '' });
  assert.equal(reportAverageAttainment(noData), null);

  const zero = report({ sectionMode: 'combined' });
  zero.sectionData.combined = section({ start: 10, complete: 10, g: { B: 10 }, actual: 0 });
  assert.equal(reportAverageAttainment(zero), 0);
});

test('Grade inflation ignores non-letter status rows in its denominator', () => {
  const s = section({ start: 20, complete: 10, g: { 'A+': 2, B: 8, Withdrawn: 10 } });
  const result = gradeInflationForSection(s);
  assert.equal(result.denominator, 10);
  assert.equal(result.aPlusPct, 20);
  assert.equal(result.inflated, true);
});

test('Combined integrity remains stable across repeated recomputation', () => {
  const r = report();
  r.sectionData.male.grades = grades({ 'A+': 20 });
  r.sectionData.female.grades = grades({ 'A+': 15 });
  enforceCombinedIntegrity(r);
  enforceCombinedIntegrity(r);
  assert.equal(r.sectionData.combined.grades['A+'], 35);
  assert.equal(combinedIntegrityAudit(r).ok, true);
});

