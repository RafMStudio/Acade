'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');

const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const sourceFiles = [
  'src/core.js', 'src/seed.js', 'src/backend.js', 'src/app.js',
  'scripts/build.js', 'scripts/check-project.js', 'scripts/browser-smoke.js',
  'tests/core.test.js'
];

for (const file of sourceFiles) {
  const result = spawnSync(process.execPath, ['--check', path.join(root, file)], { encoding: 'utf8' });
  assert.equal(result.status, 0, `${file} failed syntax check:\n${result.stderr}`);
}

const index = read('index.html');
const sourceIndex = read('index.source.html');
const app = read('src/app.js');
const core = read('src/core.js');
const seedSource = read('src/seed.js');

const ids = [...sourceIndex.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
const duplicates = ids.filter((id, i) => ids.indexOf(id) !== i);
assert.deepEqual([...new Set(duplicates)], [], 'Static HTML contains duplicate ids');
for (const button of sourceIndex.matchAll(/<button\b[^>]*>/g)) {
  assert.match(button[0], /\btype="button"/, `Static button missing type="button": ${button[0]}`);
}

for (const marker of ['src/styles.css', 'src/vendor/jszip.min.js', 'src/core.js', 'src/seed.js', 'src/backend.js', 'src/app.js']) {
  assert.ok(sourceIndex.includes(marker), `index.source.html is missing ${marker}`);
}
assert.ok(index.includes('id="acadeloop-styles"'), 'Deployment index must inline Acadeloop CSS');
for (const file of ['src/core.js', 'src/seed.js', 'src/backend.js', 'src/app.js']) {
  assert.ok(index.includes(`data-source="${file}"`), `Deployment index must inline ${file}`);
  assert.ok(!index.includes(`<script src="${file}"></script>`), `Deployment index must not depend on ${file} at runtime`);
}
assert.ok(!index.includes('<link href="src/styles.css"'), 'Deployment index must not depend on external Acadeloop CSS');
assert.ok(index.includes('<script src="vendor/jszip.min.js"></script>'), 'Deployment index must keep JSZip as a separate vendor file');
assert.ok(!index.includes('template-data.js'), 'index.html must not load an embedded template-data blob');
assert.ok(!fs.existsSync(path.join(root, 'src/template-data.js')), 'Embedded template-data.js must not exist');
assert.ok(fs.existsSync(path.join(root, 'templates/Course_Report_Placeholder.docx')), 'External Course Report template is missing');

for (const dead of ['Academic Coordinator', 'Required Course Portfolio structure']) {
  assert.ok(!app.includes(dead) && !index.includes(dead), `Dead/stale feature remains: ${dead}`);
}
for (const coreFunction of ['expectedCombinedSnapshot', 'combinedIntegrityAudit', 'gradeInflationForSection', 'calculatePloRollups', 'validateReport']) {
  assert.ok(core.includes(`function ${coreFunction}`), `Core is missing ${coreFunction}`);
  assert.ok(!app.includes(`function ${coreFunction}`), `${coreFunction} is duplicated in app.js`);
}

assert.ok(app.includes("fetch(COURSE_REPORT_TEMPLATE_URL"), 'Course Report template must be fetched as an external binary asset');
assert.ok(app.includes("templates/Course_Report_Placeholder.docx"), 'Template URL is missing from app.js');
assert.ok(!app.includes('COURSE_REPORT_TEMPLATE_BASE64'), 'Base64 Word template must not be embedded in app.js');
assert.ok(!app.includes('eval('), 'app.js must not use eval()');
assert.ok(app.includes('acadeloop_program_quality_v100'), 'Acadeloop storage key is missing');
assert.ok(!app.includes('qualiflow_'), 'Old QualiFlow storage keys remain');
assert.ok(app.includes('safePathComponent'), 'Path component sanitizer is missing');
assert.ok(index.includes('Acadeloop') && !index.includes('QualiFlow'), 'Branding is not fully updated in index.html');
assert.ok(core.includes('AcadeloopCore') && !core.includes('QualiFlowCore'), 'Core namespace is not fully rebranded');
assert.ok(seedSource.includes('ACADELOOP_SEED') && !seedSource.includes('QUALIFLOW_SEED'), 'Seed namespace is not fully rebranded');

// Source readability guard: binary/base64 payloads belong in binary files, never JS/HTML source.
for (const file of ['index.html', 'index.source.html', 'src/app.js', 'src/core.js', 'src/seed.js', 'src/backend.js']) {
  const text = read(file);
  assert.ok(!/data:(?:application|image)\/[a-z0-9.+-]+;base64,[A-Za-z0-9+/]{500,}/i.test(text), `${file} contains a large Base64 data URI`);
  assert.ok(!/[A-Za-z0-9+/]{50000,}={0,2}/.test(text), `${file} appears to contain an embedded binary/Base64 blob`);
}

assert.ok(read('src/backend.js').includes('sb_publishable_'), 'Supabase publishable key is missing');
assert.ok(read('src/backend.js').includes('/auth/v1/otp'), 'Email OTP request flow is missing');
assert.ok(app.includes("value==='SystemAdmin'||value==='System Administrator'"), 'SystemAdmin role canonicalization is missing');
assert.ok(app.includes("state.role=role;"), 'Authenticated role must overwrite stale workspace state');
assert.ok(app.includes("'System Administrator':"), 'System Administrator workspace configuration is missing');
assert.ok(app.includes("admin-create-user"), 'HOD Supabase user creation integration is missing');
assert.ok(app.includes("const TITLE_PREFIXES = ['Mr.','Ms.','Dr.']"), 'Authorized-user title prefixes are missing');
assert.ok(app.includes('<select id="auDepartment"'), 'Department must be selected from the Academic Programs master list');
assert.ok(app.includes('id="auLimitPrograms"') && app.includes('data-au-program'), 'Optional limited program access controls are missing');
assert.ok(!app.includes('id="apYear"'), 'Academic Programs must not own academic years');
assert.ok(app.includes('id="spYear"') && app.includes('id="spYears"'), 'HOD Program Settings must own academic years');
assert.ok(app.includes("const PROGRAM_TYPES = ['Diploma','Bachelor']"), 'Academic program type options are missing');
assert.ok(app.includes('id="apProgramType"'), 'Program type selector is missing');
assert.ok(app.includes('program_type:programType'), 'Program type is not persisted');
assert.ok(app.includes('id="auPrefix"'), 'Authorized-user prefix selector is missing');
assert.ok(app.includes('title_prefix:titlePrefix'), 'Authorized-user prefix is not sent to Supabase');
assert.ok(read('src/backend.js').includes('title_prefix'), 'Profile title prefix is not loaded from Supabase');
assert.ok(app.includes("export-backup-xlsx"), 'Excel backup integration is missing');
assert.ok(app.includes("project_keepalive"), 'System Administrator keepalive status integration is missing');
assert.ok(app.includes("Supabase project heartbeat"), 'Keepalive dashboard panel is missing');
assert.ok(app.includes('persistCourseReport'), 'Supabase Course Report data persistence is missing');
assert.ok(!app.includes('COURSE_REPORT_TEMPLATE_BASE64'), 'Generated DOCX must not be stored as Base64');

const seedContext = { window: {} };
vm.runInNewContext(seedSource, seedContext, { filename: 'src/seed.js' });
const seed = seedContext.window.ACADELOOP_SEED;
assert.ok(seed && Array.isArray(seed.reports), 'Seed data did not load');
assert.equal(new Set(seed.reports.map((r) => r.id)).size, seed.reports.length, 'Seed report IDs must be unique');
assert.equal(new Set(seed.plos.map((p) => p.code)).size, seed.plos.length, 'PLO codes must be unique');
for (const report of seed.reports) {
  assert.ok(['S1', 'S2', 'Summer'].includes(report.semester), `${report.id} has invalid semester`);
  assert.ok(['male', 'female', 'combined', 'all'].includes(report.sectionMode), `${report.id} has invalid section mode`);
  assert.ok(['Draft', 'Awaiting Quality Approval', 'Returned for Revision', 'Approved'].includes(report.status), `${report.id} has invalid status`);
}
for (const plo of seed.plos) {
  assert.ok(Number.isFinite(Number(plo.target)) && Number(plo.target) >= 0 && Number(plo.target) <= 100, `${plo.code} target must be 0-100`);
}

for (const file of [
  'dist/index.html', 'dist/vendor/jszip.min.js', 'dist/templates/Course_Report_Placeholder.docx'
]) {
  assert.ok(fs.existsSync(path.join(root, file)), `Build output missing ${file}`);
}

console.log('Static, branding, readability, build, and seed integrity checks passed.');
