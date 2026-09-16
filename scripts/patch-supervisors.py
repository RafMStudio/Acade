from pathlib import Path
import re

p=Path('src/app.js')
s=p.read_text()

if "'APU': {" not in s:
    pat=r"(\s+'Head of Department': \{\s*views:\['dashboard','course-reports','course-portfolios','plo','apr','operational','users','setup'\], label:'Executive oversight', avatar:'HD',\s*dashboard:'Department Quality Overview', description:'View approved quality results and control who is allowed to access Acadeloop\.'\s*\})(\s*\};)"
    m=re.search(pat,s,re.S)
    if not m: raise SystemExit('Missing HOD role block')
    addition="""\1,
    'APU': {
      views:['dashboard','course-reports','plo','apr','operational'], label:'Institution supervision', avatar:'AP',
      dashboard:'APU Supervision Dashboard', description:'Read-only oversight across all academic programs, academic years, and semesters.'
    },
    'VDAA': {
      views:['dashboard','course-reports','plo','apr','operational'], label:'Institution supervision', avatar:'VD',
      dashboard:'VDAA Supervision Dashboard', description:'Read-only oversight across all academic programs, academic years, and semesters.'
    }\2"""
    s=re.sub(pat,addition,s,count=1,flags=re.S)

if "if(value==='APU') return 'APU';" not in s:
    needle="    if(value==='Instructor') return 'Instructor';\n    return '';"
    repl="    if(value==='Instructor') return 'Instructor';\n    if(value==='APU') return 'APU';\n    if(value==='VDAA') return 'VDAA';\n    return '';"
    if needle not in s: raise SystemExit('Missing canonical role block')
    s=s.replace(needle,repl,1)
if 'const isSupervisorRole' not in s:
    needle='  const dbRoleToUi = role => canonicalUiRole(role);'
    if needle not in s: raise SystemExit('Missing dbRoleToUi')
    s=s.replace(needle,"  const isSupervisorRole = role => ['APU','VDAA'].includes(canonicalUiRole(role));\n"+needle,1)

if 'function renderSupervisorDashboard()' not in s:
    marker="  function renderDashboard(){\n    if(state.role==='System Administrator') return renderSystemAdminDashboard();"
    if marker not in s: raise SystemExit('Missing dashboard marker')
    supervisor="""  function renderSupervisorDashboard(){
    const year=ploYear||state.program.academicYear||state.academicYears[0]||'';
    const term=ploTerm||'Annual';
    const periodReports=state.reports.filter(r=>(!year||r.academicYear===year)&&(term==='Annual'||r.semester===term));
    const approved=periodReports.filter(r=>r.status==='Approved');
    const waiting=periodReports.filter(r=>r.status==='Awaiting Quality Approval');
    const returned=periodReports.filter(r=>r.status==='Returned for Revision');
    const roll=year?ploRollups(year,term):[];
    const program=programDirectory.find(p=>p.id===activeProgramId);
    const programOptions=programDirectory.map(p=>`<option value="${esc(p.id)}" ${p.id===activeProgramId?'selected':''}>${esc(programDirectoryLabel(p))}${p.status==='Closed'?' · Closed':''}</option>`).join('');
    const yearOptions=state.academicYears.map(y=>`<option value="${esc(y)}" ${y===year?'selected':''}>${esc(y)}</option>`).join('');
    const termOptions=['Annual',...TERMS].map(t=>`<option value="${esc(t)}" ${t===term?'selected':''}>${esc(t)}</option>`).join('');
    return roleHero()+pageHead('Institution-wide supervision',`${state.role} Supervision Dashboard`,'Read-only oversight across every Acadeloop academic program. Filter by program, academic year, and semester; no data can be edited or deleted from this role.')+`
      <div class="period-filter"><label><span>Academic program</span><select id="supervisorProgram">${programOptions}</select></label><label><span>Academic year</span><select id="supervisorYear">${yearOptions}</select></label><label><span>Semester</span><select id="supervisorTerm">${termOptions}</select></label></div>
      <div class="user-directory-note"><div class="automation-icon">◉</div><div><strong>Read-only supervision</strong><span>${esc(program?.name||'Academic program')} · ${esc(year||'No academic year')} · ${esc(term)}. APU/VDAA can inspect all available quality data but cannot create, edit, approve, return, delete, or change settings.</span></div></div>
      <div class="grid grid-4"><div class="card metric"><div class="label">Reports</div><div class="value">${periodReports.length}</div><div class="sub">All statuses in selected period</div></div><div class="card metric"><div class="label">Quality approved</div><div class="value">${approved.length}</div><div class="sub">Official program data</div></div><div class="card metric"><div class="label">In workflow</div><div class="value">${waiting.length+returned.length}</div><div class="sub">${waiting.length} awaiting · ${returned.length} returned</div></div><div class="card metric"><div class="label">PLOs meeting target</div><div class="value">${roll.filter(x=>x.met).length}/${roll.length}</div><div class="sub">Approved CLO evidence only</div></div></div>
      ${dashboardQualitySection(periodReports,year,term)}
      ${reportBoard(periodReports,'Program reporting oversight')}`;
  }

"""
    replacement=supervisor+marker.replace("\n    if(state.role==='System Administrator') return renderSystemAdminDashboard();","\n    if(state.role==='System Administrator') return renderSystemAdminDashboard();\n    if(isSupervisorRole(state.role)) return renderSupervisorDashboard();")
    s=s.replace(marker,replacement,1)

old="const roleOptions=isAdmin?'<option>HOD</option><option>Coordinator</option><option>Instructor</option>':'<option>Instructor</option><option>Coordinator</option>';"
new="const roleOptions=isAdmin?'<option>APU</option><option>VDAA</option><option>HOD</option><option>Coordinator</option><option>Instructor</option>':'<option>Instructor</option><option>Coordinator</option>';"
if new not in s:
    if old not in s: raise SystemExit('Missing role options')
    s=s.replace(old,new,1)

old="""      const access=u.role==='System Administrator'?'Global':u.limitProgramAccess?`${programs.length} selected program${programs.length===1?'':'s'}`:`All ${u.department||''} programs`;
      const detail=u.limitProgramAccess&&programs.length?programs.map(programDirectoryLabel).join(', '):u.department||'System';"""
new="""      const supervisor=isSupervisorRole(u.role);
      const access=u.role==='System Administrator'?'Global':supervisor?'All programs · Read only':u.limitProgramAccess?`${programs.length} selected program${programs.length===1?'':'s'}`:`All ${u.department||''} programs`;
      const detail=supervisor?'System-wide supervision':u.limitProgramAccess&&programs.length?programs.map(programDirectoryLabel).join(', '):u.department||'System';"""
if new not in s:
    if old not in s: raise SystemExit('Missing user access display')
    s=s.replace(old,new,1)

if "const globalSupervisor=isAdmin&&['APU','VDAA'].includes(role);" not in s:
    fn=s.index('async function addAuthorizedUser')
    start=s.index("    const department=isAdmin?$('auDepartment')?.value.trim()",fn)
    end=s.index("    const btn=$('addAuthorizedUser')",start)
    replacement="""    const globalSupervisor=isAdmin&&['APU','VDAA'].includes(role);
    const department=globalSupervisor?'System Supervision':isAdmin?$('auDepartment')?.value.trim():(currentUser?.department||state.program.department||'').trim();
    const limitProgramAccess=globalSupervisor?false:!!$('auLimitPrograms')?.checked;
    const programIds=globalSupervisor?[]:(limitProgramAccess?[...document.querySelectorAll('[data-au-program]:checked')].map(el=>el.value):[]);
    const departmentPrograms=globalSupervisor?[]:programDirectory.filter(p=>p.status==='Open'&&p.department===department);
    if(!titlePrefix||!first||!last||(!globalSupervisor&&!department)||!email){toast('Prefix, first name, last name, role, and email are required. Department is required for program roles.');return;}
    if(backendEnabled&&!globalSupervisor&&!departmentPrograms.length){toast('This department has no open academic programs. Add a program first.');return;}
    if(!globalSupervisor&&limitProgramAccess&&!programIds.length){toast('Select at least one academic program or turn off Limit program access.');return;}
    if(!$('auEmail')?.checkValidity()){toast('Enter a valid email address.');return;}
    const allowed=isAdmin?['APU','VDAA','HOD','Coordinator','Instructor']:['Instructor','Coordinator'];if(!allowed.includes(role)){toast('That role is not permitted here.');return;}
"""
    s=s[:start]+replacement+s[end:]

old="render();toast(limitProgramAccess?'User added with limited program access.':'User added with access to all department programs.');"
new="render();toast(globalSupervisor?'Read-only supervisor added with access to all academic programs.':limitProgramAccess?'User added with limited program access.':'User added with access to all department programs.');"
if new not in s:
    if old not in s: raise SystemExit('Missing add-user toast')
    s=s.replace(old,new,1)

if "$('supervisorProgram')" not in s:
    needle="    if($('periodTerm'))$('periodTerm').addEventListener('change',()=>{ploTerm=$('periodTerm').value;activePlo=null;render();});"
    if needle not in s: raise SystemExit('Missing periodTerm handler')
    addition=needle+"\n    if($('supervisorProgram'))$('supervisorProgram').addEventListener('change',e=>switchActiveProgram(e.target.value));\n    if($('supervisorYear'))$('supervisorYear').addEventListener('change',()=>{ploYear=$('supervisorYear').value;activePlo=null;render();});\n    if($('supervisorTerm'))$('supervisorTerm').addEventListener('change',()=>{ploTerm=$('supervisorTerm').value;activePlo=null;render();});"
    s=s.replace(needle,addition,1)

if "if(isSupervisorRole(currentUser.role)){" not in s:
    fn=s.index('async function hydrateSharedState')
    start=s.index("    const memberships=await Backend.select('program_memberships'",fn)
    end=s.index('    const base=clone(seed);',start)
    replacement="""    if(isSupervisorRole(currentUser.role)){
      membershipDirectory=[];
      accessibleProgramIds=programDirectory.map(p=>p.id).filter(Boolean);
      if(!accessibleProgramIds.length) throw new Error('No academic programs are available for supervision.');
      if(!activeProgramId||!accessibleProgramIds.includes(activeProgramId))activeProgramId=programDirectory.find(p=>p.status==='Open')?.id||accessibleProgramIds[0];
    }else{
      const memberships=await Backend.select('program_memberships',`user_id=eq.${encodeURIComponent(currentUser.id)}&active=eq.true&select=program_id,role`);
      membershipDirectory=memberships||[];
      accessibleProgramIds=[...new Set(membershipDirectory.map(m=>m.program_id).filter(Boolean))];
      if(!accessibleProgramIds.length) throw new Error('Your account is not assigned to an academic program. Contact the System Administrator or HOD.');
      if(!activeProgramId||!accessibleProgramIds.includes(activeProgramId))activeProgramId=accessibleProgramIds.includes(currentUser.defaultProgramId)?currentUser.defaultProgramId:accessibleProgramIds[0];
    }
"""
    s=s[:start]+replacement+s[end:]

p.write_text(s)

Path('tests/supervisor.test.js').write_text("""const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const app=fs.readFileSync('src/app.js','utf8');
test('APU and VDAA roles exist',()=>{assert.match(app,/if\\(value==='APU'\\) return 'APU'/);assert.match(app,/if\\(value==='VDAA'\\) return 'VDAA'/);assert.match(app,/isSupervisorRole/);});
test('supervision dashboard has program, year and semester filters',()=>{assert.match(app,/supervisorProgram/);assert.match(app,/supervisorYear/);assert.match(app,/supervisorTerm/);});
test('supervisor role navigation is read-only',()=>{const a=app.indexOf("'APU': {");const c=app.indexOf("};",app.indexOf("'VDAA': {"));const block=app.slice(a,c);assert.doesNotMatch(block,/users|setup|automations|course-portfolios/);});
""")
