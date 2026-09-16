const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const app=fs.readFileSync('src/app.js','utf8');
test('APU and VDAA roles exist',()=>{assert.match(app,/if\(value==='APU'\) return 'APU'/);assert.match(app,/if\(value==='VDAA'\) return 'VDAA'/);assert.match(app,/isSupervisorRole/);});
test('supervision dashboard has program, year and semester filters',()=>{assert.match(app,/supervisorProgram/);assert.match(app,/supervisorYear/);assert.match(app,/supervisorTerm/);});
test('supervisor role navigation is read-only',()=>{const a=app.indexOf("'APU': {");const c=app.indexOf("};",app.indexOf("'VDAA': {"));const block=app.slice(a,c);assert.doesNotMatch(block,/users|setup|automations|course-portfolios/);});
