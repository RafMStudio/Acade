(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.EduItqanCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const TERMS = Object.freeze(['S1', 'S2', 'Summer']);
  const LETTER_GRADE_LABELS = Object.freeze(['A+', 'A', 'B+', 'B', 'C+', 'C', 'D+', 'D', 'F']);
  const GRADE_DEFS = Object.freeze([
    ['A+', 'a_plus_students', 'a_plus_percentage'],
    ['A', 'a_students', 'a_percentage'],
    ['B+', 'b_plus_students', 'b_plus_percentage'],
    ['B', 'b_students', 'b_percentage'],
    ['C+', 'c_plus_students', 'c_plus_percentage'],
    ['C', 'c_students', 'c_percentage'],
    ['D+', 'd_plus_students', 'd_plus_percentage'],
    ['D', 'd_students', 'd_percentage'],
    ['F', 'f_students', 'f_percentage'],
    ['Denied', 'denied', 'denied_percentage'],
    ['In Progress', 'in_progress', 'in_progress_percentage'],
    ['Incomplete', 'incomplete', 'incomplete_percentage'],
    ['Pass', 'pass', 'pass_percentage'],
    ['Fail', 'fail', 'fail_percentage'],
    ['Withdrawn', 'withdrawn', 'withdrawn_percentage']
  ]);
  const ALL_GRADE_LABELS = Object.freeze(GRADE_DEFS.map(([label]) => label));
  const COMPLETION_GRADE_LABELS = Object.freeze([...LETTER_GRADE_LABELS, 'Pass', 'Fail']);

  const sectionLabel = (key) => ({ male: 'Male', female: 'Female', combined: 'Combined', all: 'All' })[key] || 'Combined';
  const isBlank = (value) => value === '' || value == null;
  const numeric = (value) => Number(value);
  const numberOrZero = (value) => Number(value) || 0;
  const round1 = (value) => Math.round(Number(value) * 10) / 10;
  const formatPercent = (value) => `${round1(value)}%`;
  const clone = (value) => JSON.parse(JSON.stringify(value));

  function blankGrades() {
    return Object.fromEntries(ALL_GRADE_LABELS.map((label) => [label, 0]));
  }

  function blankSectionFor(report) {
    return {
      studentsStart: 0,
      studentsComplete: 0,
      grades: blankGrades(),
      gradeComment: '',
      gradeRecommendation: '',
      cloRecommendation: '',
      cloResults: Object.fromEntries((report.clos || []).map((clo) => [clo.code, { actual: '', comment: '' }]))
    };
  }

  function normalizeSectionData(report, section) {
    const source = section && typeof section === 'object' ? section : {};
    const normalized = {
      ...source,
      studentsStart: numberOrZero(source.studentsStart),
      studentsComplete: numberOrZero(source.studentsComplete),
      grades: { ...blankGrades(), ...(source.grades || {}) },
      gradeComment: source.gradeComment || '',
      gradeRecommendation: source.gradeRecommendation || '',
      cloRecommendation: source.cloRecommendation || '',
      cloResults: source.cloResults && typeof source.cloResults === 'object' ? { ...source.cloResults } : {}
    };
    for (const clo of report.clos || []) {
      normalized.cloResults[clo.code] = { actual: '', comment: '', ...(normalized.cloResults[clo.code] || {}) };
    }
    return normalized;
  }

  function effectiveSectionKey(report) {
    return report.sectionMode === 'all' ? 'combined' : report.sectionMode;
  }

  function activeSectionKeys(report) {
    return report.sectionMode === 'all' ? ['male', 'female', 'combined'] : [effectiveSectionKey(report)];
  }

  function combineText(male, female) {
    const a = String(male || '').trim();
    const b = String(female || '').trim();
    if (a && b && a !== b) return `Male: ${a}\nFemale: ${b}`;
    return a || b || '';
  }

  function weightedActual(maleActual, femaleActual, maleWeight, femaleWeight) {
    if (isBlank(maleActual) || isBlank(femaleActual)) return '';
    const male = numeric(maleActual);
    const female = numeric(femaleActual);
    if (!Number.isFinite(male) || !Number.isFinite(female)) return '';
    const wm = Math.max(0, numberOrZero(maleWeight));
    const wf = Math.max(0, numberOrZero(femaleWeight));
    const total = wm + wf;
    return round1(total ? (male * wm + female * wf) / total : (male + female) / 2);
  }

  function expectedCombinedSnapshot(report) {
    const male = normalizeSectionData(report, report.sectionData?.male || blankSectionFor(report));
    const female = normalizeSectionData(report, report.sectionData?.female || blankSectionFor(report));
    const combined = blankSectionFor(report);

    combined.studentsStart = male.studentsStart + female.studentsStart;
    combined.studentsComplete = male.studentsComplete + female.studentsComplete;
    for (const label of ALL_GRADE_LABELS) {
      combined.grades[label] = numberOrZero(male.grades[label]) + numberOrZero(female.grades[label]);
    }
    for (const clo of report.clos || []) {
      const m = male.cloResults[clo.code] || {};
      const f = female.cloResults[clo.code] || {};
      combined.cloResults[clo.code] = {
        actual: weightedActual(m.actual, f.actual, male.studentsComplete, female.studentsComplete),
        comment: combineText(m.comment, f.comment)
      };
    }
    combined.gradeComment = combineText(male.gradeComment, female.gradeComment);
    combined.gradeRecommendation = combineText(male.gradeRecommendation, female.gradeRecommendation);
    combined.cloRecommendation = combineText(male.cloRecommendation, female.cloRecommendation);
    return combined;
  }

  function sectionSnapshot(report, key) {
    if (key === 'combined' && report.sectionMode === 'all') return expectedCombinedSnapshot(report);
    return normalizeSectionData(report, report.sectionData?.[key] || blankSectionFor(report));
  }

  function applySectionToFlat(report, key) {
    const section = sectionSnapshot(report, key);
    report.studentsStart = section.studentsStart;
    report.studentsComplete = section.studentsComplete;
    report.grades = { ...section.grades };
    report.gradeComment = section.gradeComment;
    report.gradeRecommendation = section.gradeRecommendation;
    report.cloRecommendation = section.cloRecommendation;
    for (const clo of report.clos || []) {
      const result = section.cloResults[clo.code] || {};
      clo.actual = result.actual ?? '';
      clo.comment = result.comment || '';
    }
    return report;
  }

  function syncFlatFromEffective(report) {
    if (report.sectionData) applySectionToFlat(report, effectiveSectionKey(report));
    return report;
  }

  function recomputeCombined(report, syncFlat = true) {
    if (!report.sectionData) report.sectionData = {};
    report.sectionData.combined = expectedCombinedSnapshot(report);
    report.autoCombine = true;
    if (syncFlat) syncFlatFromEffective(report);
    return report.sectionData.combined;
  }

  function ensureSectionModel(report) {
    if (!report.sectionData || typeof report.sectionData !== 'object') report.sectionData = {};
    for (const key of ['male', 'female', 'combined']) {
      report.sectionData[key] = normalizeSectionData(report, report.sectionData[key] || blankSectionFor(report));
    }
    if (report.sectionMode === 'all') recomputeCombined(report, false);
    syncFlatFromEffective(report);
    return report;
  }

  function sameNumber(a, b) {
    return Math.abs(numberOrZero(a) - numberOrZero(b)) < 0.0001;
  }

  function combinedIntegrityAudit(report) {
    if (report.sectionMode !== 'all') return { ok: true, errors: [] };
    const expected = expectedCombinedSnapshot(report);
    const actual = normalizeSectionData(report, report.sectionData?.combined || blankSectionFor(report));
    const errors = [];

    if (!sameNumber(actual.studentsStart, expected.studentsStart)) errors.push(`Students starting: expected ${expected.studentsStart}, found ${actual.studentsStart}`);
    if (!sameNumber(actual.studentsComplete, expected.studentsComplete)) errors.push(`Students completed: expected ${expected.studentsComplete}, found ${actual.studentsComplete}`);
    for (const label of ALL_GRADE_LABELS) {
      if (!sameNumber(actual.grades[label], expected.grades[label])) errors.push(`${label}: expected ${numberOrZero(expected.grades[label])}, found ${numberOrZero(actual.grades[label])}`);
    }
    for (const field of ['gradeComment', 'gradeRecommendation', 'cloRecommendation']) {
      if (String(actual[field] || '') !== String(expected[field] || '')) errors.push(`${field}: derived text is stale`);
    }
    for (const clo of report.clos || []) {
      const a = actual.cloResults[clo.code] || {};
      const e = expected.cloResults[clo.code] || {};
      const numericEqual = !isBlank(a.actual) && !isBlank(e.actual) && Number.isFinite(numeric(a.actual)) && Number.isFinite(numeric(e.actual)) && sameNumber(a.actual, e.actual);
      if (String(a.actual ?? '') !== String(e.actual ?? '') && !numericEqual) {
        errors.push(`${clo.code} actual: expected ${e.actual === '' ? 'blank until both sections are entered' : e.actual}, found ${a.actual ?? ''}`);
      }
      if (String(a.comment || '') !== String(e.comment || '')) errors.push(`${clo.code} comment: derived text is stale`);
    }
    return { ok: errors.length === 0, errors, expected };
  }

  function enforceCombinedIntegrity(report, syncFlat = true) {
    if (report.sectionMode !== 'all') {
      if (syncFlat) syncFlatFromEffective(report);
      return { ok: true, errors: [] };
    }
    recomputeCombined(report, syncFlat);
    const audit = combinedIntegrityAudit(report);
    if (!audit.ok) throw new Error(`Combined integrity check failed: ${audit.errors.join('; ')}`);
    return audit;
  }

  function reportVariant(report, key) {
    const variant = clone(report);
    if (variant.sectionMode === 'all') enforceCombinedIntegrity(variant, false);
    variant.sectionMode = key;
    ensureSectionModel(variant);
    applySectionToFlat(variant, key);
    return variant;
  }

  function gradeCount(report, label) {
    return numberOrZero(report.grades?.[label]);
  }

  function gradeTotal(report) {
    return Object.values(report.grades || {}).reduce((sum, value) => sum + numberOrZero(value), 0);
  }

  function letterGradeTotalFromSection(section) {
    return LETTER_GRADE_LABELS.reduce((sum, label) => sum + numberOrZero(section?.grades?.[label]), 0);
  }

  function completedStudentCountFromSection(section) {
    return COMPLETION_GRADE_LABELS.reduce((sum, label) => sum + numberOrZero(section?.grades?.[label]), 0);
  }

  function gradeInflationForSection(section) {
    const denominator = letterGradeTotalFromSection(section);
    const aPlus = numberOrZero(section?.grades?.['A+']);
    const a = numberOrZero(section?.grades?.A);
    const aPlusPct = denominator ? (aPlus / denominator) * 100 : 0;
    const aOrAbovePct = denominator ? ((aPlus + a) / denominator) * 100 : 0;
    const reasons = [];
    if (denominator && aPlusPct >= 20) reasons.push(`A+ ${formatPercent(aPlusPct)} ≥ 20%`);
    if (denominator && aOrAbovePct > 60) reasons.push(`A and above ${formatPercent(aOrAbovePct)} > 60%`);
    return { inflated: reasons.length > 0, denominator, aPlus, a, aPlusPct, aOrAbovePct, reasons };
  }

  function gradeInflationSections(report, sourceOnly = false) {
    const keys = report.sectionMode === 'all'
      ? (sourceOnly ? ['male', 'female'] : ['male', 'female', 'combined'])
      : [effectiveSectionKey(report)];
    return keys
      .map((key) => ({ key, label: sectionLabel(key), ...gradeInflationForSection(sectionSnapshot(report, key)) }))
      .filter((item) => item.denominator > 0);
  }

  function reportGradeInflation(report) {
    const sections = gradeInflationSections(report, false);
    const flagged = sections.filter((item) => item.inflated);
    return {
      inflated: flagged.length > 0,
      sections,
      flagged,
      reasons: flagged.flatMap((item) => item.reasons.map((reason) => `${item.label}: ${reason}`))
    };
  }

  function reportCloGaps(report) {
    const keys = report.sectionMode === 'all' ? ['male', 'female', 'combined'] : [effectiveSectionKey(report)];
    const gaps = [];
    for (const key of keys) {
      const section = sectionSnapshot(report, key);
      for (const clo of report.clos || []) {
        const actual = section.cloResults[clo.code]?.actual;
        if (isBlank(actual)) continue;
        const actualNumber = numeric(actual);
        const target = numeric(clo.target);
        if (Number.isFinite(actualNumber) && Number.isFinite(target) && actualNumber < target) {
          gaps.push({ section: key, sectionLabel: sectionLabel(key), code: clo.code, actual: actualNumber, target, plo: clo.plo || '' });
        }
      }
    }
    return gaps;
  }

  function reportQualityFlags(report) {
    const inflation = reportGradeInflation(report);
    const cloGaps = reportCloGaps(report);
    return { inflation, cloGaps, hasIssue: inflation.inflated || cloGaps.length > 0 };
  }

  function pooledGradeDistribution(reports) {
    const totals = Object.fromEntries(LETTER_GRADE_LABELS.map((label) => [label, 0]));
    let denominator = 0;
    let courseCount = 0;
    for (const report of reports || []) {
      const section = sectionSnapshot(report, effectiveSectionKey(report));
      const graded = letterGradeTotalFromSection(section);
      if (!graded) continue;
      courseCount += 1;
      denominator += graded;
      for (const label of LETTER_GRADE_LABELS) totals[label] += numberOrZero(section.grades[label]);
    }
    const percentages = Object.fromEntries(LETTER_GRADE_LABELS.map((label) => [label, denominator ? (totals[label] / denominator) * 100 : 0]));
    return { totals, percentages, denominator, courseCount };
  }

  function reportAverageAttainment(report) {
    const section = sectionSnapshot(report, effectiveSectionKey(report));
    const values = (report.clos || [])
      .map((clo) => section.cloResults[clo.code]?.actual)
      .filter((value) => !isBlank(value) && Number.isFinite(numeric(value)))
      .map(numeric);
    return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  }

  function reportCompleteness(report) {
    let total = 0;
    let done = 0;
    const base = [report.courseCode, report.courseName, report.academicYear, report.semester, report.instructor, report.reportDate];
    total += base.length;
    done += base.filter((value) => String(value ?? '').trim() !== '').length;
    const keys = report.sectionMode === 'all' ? ['male', 'female'] : [effectiveSectionKey(report)];
    for (const key of keys) {
      const section = sectionSnapshot(report, key);
      total += 5;
      if (numberOrZero(section.studentsStart) > 0) done += 1;
      if (numberOrZero(section.studentsComplete) > 0) done += 1;
      done += [section.gradeComment, section.gradeRecommendation, section.cloRecommendation]
        .filter((value) => String(value || '').trim()).length;
      for (const clo of report.clos || []) {
        total += 2;
        const result = section.cloResults[clo.code] || {};
        if (!isBlank(result.actual)) done += 1;
        if (String(result.comment || '').trim()) done += 1;
      }
    }
    total += 1;
    if ((report.improvements || []).length) done += 1;
    return Math.round((done / Math.max(total, 1)) * 100);
  }

  function calculatePloRollups(reports, plos, year, term = 'Annual') {
    const approved = (reports || []).filter((report) => report.status === 'Approved'
      && (!year || report.academicYear === year)
      && (term === 'Annual' || !term || report.semester === term));

    return (plos || []).map((plo) => {
      const rows = [];
      for (const report of approved) {
        const section = sectionSnapshot(report, effectiveSectionKey(report));
        const weight = numberOrZero(section.studentsComplete);
        if (weight <= 0) continue;
        for (const clo of report.clos || []) {
          if (clo.plo !== plo.code) continue;
          const actual = section.cloResults[clo.code]?.actual;
          if (isBlank(actual) || !Number.isFinite(numeric(actual))) continue;
          rows.push({ report, clo: { ...clo, actual: numeric(actual), comment: section.cloResults[clo.code]?.comment || '' }, actual: numeric(actual), weight });
        }
      }
      const totalWeight = rows.reduce((sum, row) => sum + row.weight, 0);
      const actual = totalWeight ? rows.reduce((sum, row) => sum + row.actual * row.weight, 0) / totalWeight : null;
      return { ...plo, actual, rows, totalWeight, met: actual !== null && actual >= numberOrZero(plo.target) };
    });
  }

  // Keep identical PLO codes in different programs separate during supervision.
  function supervisorScope(snapshot, filters) {
    const programs=(snapshot.programs||[]).filter(p=>(!filters.department||p.department===filters.department)&&(!filters.program||p.id===filters.program));
    const ids=new Set(programs.map(p=>p.id));
    const periodReports=(snapshot.reports||[]).filter(r=>ids.has(r.programId)&&(!filters.year||r.academicYear===filters.year)&&(filters.term==='Annual'||r.semester===filters.term));
    const reports=periodReports.filter(r=>!filters.status||r.status===filters.status);
    const rollups=programs.flatMap(p=>calculatePloRollups(periodReports.filter(r=>r.programId===p.id),(snapshot.plos||[]).filter(x=>x.programId===p.id),filters.year,filters.term).map(x=>({...x,programId:p.id})));
    return {programs,periodReports,reports,rollups};
  }

  function validateSection(report, key, requireInflationNarrative) {
    const section = sectionSnapshot(report, key);
    const label = sectionLabel(key);
    const errors = [];

    if (!Number.isInteger(numeric(section.studentsStart)) || numeric(section.studentsStart) <= 0) errors.push(`${label} students starting must be a positive whole number`);
    if (!Number.isInteger(numeric(section.studentsComplete)) || numeric(section.studentsComplete) <= 0) errors.push(`${label} students completed must be a positive whole number`);
    if (numeric(section.studentsComplete) > numeric(section.studentsStart)) errors.push(`${label} completed students cannot exceed starting students`);

    let entered = 0;
    for (const grade of ALL_GRADE_LABELS) {
      const value = numeric(section.grades[grade]);
      if (!Number.isInteger(value) || value < 0) errors.push(`${label} ${grade} count must be a non-negative whole number`);
      else entered += value;
    }
    if (entered !== numeric(section.studentsStart)) errors.push(`${label} grade/status total (${entered}) must equal students starting (${section.studentsStart})`);

    const completedFromGrades = completedStudentCountFromSection(section);
    if (completedFromGrades !== numeric(section.studentsComplete)) {
      errors.push(`${label} completed-grade total (${completedFromGrades}) must equal students completed (${section.studentsComplete})`);
    }

    if (requireInflationNarrative && gradeInflationForSection(section).inflated) {
      if (!String(section.gradeComment || '').trim()) errors.push(`${label} Comment on Student Grades is required because grade inflation was detected`);
      if (!String(section.gradeRecommendation || '').trim()) errors.push(`${label} Recommendations on Grades is required because grade inflation was detected`);
    }

    for (const clo of report.clos || []) {
      const actual = section.cloResults[clo.code]?.actual;
      if (isBlank(actual) || !Number.isFinite(numeric(actual))) errors.push(`${label} ${clo.code} actual is required`);
      else if (numeric(actual) < 0 || numeric(actual) > 100) errors.push(`${label} ${clo.code} actual must be 0–100`);
    }
    return errors;
  }

  function validateReport(report, options = {}) {
    const errors = [];
    const ploCodes = new Set(options.ploCodes || []);

    if (!report.academicYear) errors.push('academic year');
    if (!TERMS.includes(report.semester)) errors.push('semester');
    if (!String(report.courseCode || '').trim() || !String(report.courseName || '').trim()) errors.push('course identity');
    if (!String(report.instructor || '').trim()) errors.push('instructor');
    if (!String(report.reportDate || '').trim()) errors.push('report date');

    const codes = new Set();
    for (const clo of report.clos || []) {
      const code = String(clo.code || '').trim();
      if (!code) errors.push('CLO code is required');
      else if (codes.has(code.toLowerCase())) errors.push(`Duplicate CLO code: ${code}`);
      else codes.add(code.toLowerCase());
      if (!String(clo.text || '').trim()) errors.push(`${code || 'CLO'} description is required`);
      if (!String(clo.method || '').trim()) errors.push(`${code || 'CLO'} assessment method is required`);
      if (!String(clo.plo || '').trim()) errors.push(`${code || 'CLO'} PLO mapping is required`);
      else if (ploCodes.size && !ploCodes.has(clo.plo)) errors.push(`${code || 'CLO'} maps to an unknown PLO (${clo.plo})`);
      if (isBlank(clo.target) || !Number.isFinite(numeric(clo.target)) || numeric(clo.target) < 0 || numeric(clo.target) > 100) errors.push(`${code || 'CLO'} target must be 0–100`);
    }
    if (!(report.clos || []).length) errors.push('at least one CLO is required');

    const sourceKeys = report.sectionMode === 'all' ? ['male', 'female'] : [effectiveSectionKey(report)];
    for (const key of sourceKeys) errors.push(...validateSection(report, key, true));

    if (report.sectionMode === 'all') {
      const combinedInflation = gradeInflationForSection(expectedCombinedSnapshot(report));
      if (combinedInflation.inflated) {
        // Combined is derived and read-only. Require both source narratives so the generated Combined report has an explanation.
        for (const key of ['male', 'female']) {
          const section = sectionSnapshot(report, key);
          if (!String(section.gradeComment || '').trim()) errors.push(`${sectionLabel(key)} Comment on Student Grades is required because Combined grade inflation was detected`);
          if (!String(section.gradeRecommendation || '').trim()) errors.push(`${sectionLabel(key)} Recommendations on Grades is required because Combined grade inflation was detected`);
        }
      }
      try {
        enforceCombinedIntegrity(report, true);
        const audit = combinedIntegrityAudit(report);
        if (!audit.ok) errors.push(...audit.errors.map((error) => `Combined check: ${error}`));
      } catch (error) {
        errors.push(error.message || 'Combined integrity check failed');
      }
    }

    return [...new Set(errors)];
  }

  // Academic years are keyed by their starting year, independent of dash style.
  function kpiYearStart(label){
    const match=String(label||'').trim().match(/^(\d{4})(?:\s*[-–—/]\s*\d{4})?$/);
    return match?Number(match[1]):null;
  }
  function kpiYearLabel(start, reference){return /^\d{4}$/.test(String(reference))?String(start):`${start}–${start+1}`;}
  function kpiNumber(value){
    if(value==null||String(value).trim()==='')return null;
    const number=Number(value);
    if(!Number.isFinite(number)||number<0||number>1e12)throw new Error('Benchmarks must be numbers between 0 and 1,000,000,000,000.');
    return number;
  }
  function kpiInternal(records,kpiId,year,fallback=null){
    const previous=records.find(r=>r.kpi_id===kpiId&&Number(r.year_start)===Number(year)-1);
    return previous?.actual!=null?{value:kpiNumber(previous.actual),automatic:true}:{value:kpiNumber(fallback),automatic:false};
  }
  function kpiTrend(records,kpiId,year){
    return [Number(year)-2,Number(year)-1,Number(year)].map(y=>({year:y,actual:kpiNumber(records.find(r=>r.kpi_id===kpiId&&Number(r.year_start)===y)?.actual)}));
  }
  function kpiMeasurement(unit, outOf){
    if(!['%','ratio'].includes(unit))throw new Error('Select percentage or ratio.');
    const ratio=unit==='ratio'?kpiNumber(outOf):null;
    if(unit==='ratio'&&!(ratio>0))throw new Error('Enter a ratio “out of” value greater than zero.');
    return {unit,ratio_out_of:ratio};
  }
  function kpiBenchmark(value,kpi){
    const number=kpiNumber(value);
    if(kpi.unit==='%'&&number!=null&&number>100)throw new Error('Percentage benchmarks must be between 0 and 100.');
    return number;
  }
  function kpiDepartmentAccess(user,department){
    const own=String(user?.department||'').trim();
    return !!user&&user.active!==false&&!!own&&own===String(department||'').trim()&&['HOD','Head of Department','Coordinator','Instructor','APU','VDAA'].includes(user.role);
  }
  function canEditKpi(user){return !!user&&user.active!==false&&['HOD','Head of Department'].includes(user.role);}
  function canEditKpiAction(user,kpi){return !!user&&user.active!==false&&!!kpi?.owner_user_id&&['HOD','Head of Department','Coordinator','Instructor'].includes(user.role)&&user.id===kpi.owner_user_id;}

  return Object.freeze({
    supervisorScope,
    kpiMeasurement, kpiBenchmark, kpiDepartmentAccess, kpiYearStart, kpiYearLabel, kpiNumber, kpiInternal, kpiTrend, canEditKpi, canEditKpiAction,
    TERMS,
    LETTER_GRADE_LABELS,
    GRADE_DEFS,
    ALL_GRADE_LABELS,
    COMPLETION_GRADE_LABELS,
    sectionLabel,
    blankGrades,
    blankSectionFor,
    normalizeSectionData,
    effectiveSectionKey,
    activeSectionKeys,
    combineText,
    weightedActual,
    expectedCombinedSnapshot,
    sectionSnapshot,
    applySectionToFlat,
    syncFlatFromEffective,
    recomputeCombined,
    ensureSectionModel,
    combinedIntegrityAudit,
    enforceCombinedIntegrity,
    reportVariant,
    gradeCount,
    gradeTotal,
    letterGradeTotalFromSection,
    completedStudentCountFromSection,
    gradeInflationForSection,
    gradeInflationSections,
    reportGradeInflation,
    reportCloGaps,
    reportQualityFlags,
    pooledGradeDistribution,
    reportAverageAttainment,
    reportCompleteness,
    calculatePloRollups,
    validateReport
  });
});

