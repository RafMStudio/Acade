from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = root / 'src/app.js'
s = app.read_text()

old = """  const normalizeTitlePrefix = value => TITLE_PREFIXES.includes(String(value||'').trim()) ? String(value).trim() : '';
  const displayUserName = user => [normalizeTitlePrefix(user?.titlePrefix), user?.firstName, user?.lastName].filter(Boolean).join(' ').trim() || user?.email || 'User';
  const programInputLabel = program => program ? `${program.code} · ${program.name}` : '';
  const findProgramFromInput = value => {
    const key=String(value||'').trim().toLowerCase();
    if(!key) return null;
    return programDirectory.find(program=>[program.id,program.code,program.name,programInputLabel(program)].some(candidate=>String(candidate||'').trim().toLowerCase()===key))||null;
  };
"""
new = """  const PROGRAM_TYPES = ['Diploma','Bachelor'];
  const normalizeTitlePrefix = value => TITLE_PREFIXES.includes(String(value||'').trim()) ? String(value).trim() : '';
  const normalizeProgramType = value => PROGRAM_TYPES.includes(String(value||'').trim()) ? String(value).trim() : '';
  const displayUserName = user => [normalizeTitlePrefix(user?.titlePrefix), user?.firstName, user?.lastName].filter(Boolean).join(' ').trim() || user?.email || 'User';
  const programTypeLabel = program => normalizeProgramType(program?.program_type||program?.programType||program?.data?.programType) || 'Bachelor';
  const programDirectoryLabel = program => program ? `${program.name} (${program.code})` : '';
  const uniqueDepartments = programs => [...new Set((programs||[]).map(program=>String(program?.department||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
"""
if old not in s:
    raise SystemExit('helper block not found')
s = s.replace(old, new, 1)

start = s.index('  function renderUsers(){')
end = s.index('  function renderProgramsAdmin(){', start)
s = s[:start] + r'''  function renderUsers(){
    const isAdmin=state.role==='System Administrator';
    const rows=userDirectory.map(u=>`<tr><td><strong>${esc(displayUserName(u))}</strong><div class="tiny">${esc(u.email)}</div></td><td>${esc(u.programName||u.department||'System')}</td><td><span class="user-table-role">${esc(u.role)}</span></td><td><span class="user-table-role user-status-active">${u.active===false?'Inactive':'Active'}</span></td><td>${esc(u.createdAt?String(u.createdAt).slice(0,10):'—')}</td><td>${u.role==='System Administrator'?'—':`<button class="btn btn-ghost" data-user-status="${u.id}" data-user-active="${u.active===false?'1':'0'}" data-user-program="${esc(u.programId||'')}">${u.active===false?'Reactivate':'Deactivate'}</button>`}</td></tr>`).join('');
    const actions=backendEnabled?`<button class="btn btn-ghost" id="backupAllData">${isAdmin?'Backup Entire System':'Backup Program'} (.xlsx)</button>`:'';
    const openPrograms=programDirectory.filter(p=>p.status==='Open');
    const departmentOptions=uniqueDepartments(openPrograms).map(department=>`<option value="${esc(department)}">${esc(department)}</option>`).join('');
    const roleOptions=isAdmin?'<option>HOD</option><option>Coordinator</option><option>Instructor</option>':'<option>Instructor</option><option>Coordinator</option>';
    const activeProgram=programDirectory.find(p=>p.id===activeProgramId);
    const hodDepartment=activeProgram?.department||state.program.department||'';
    const hodProgramLabel=activeProgram?`${programDirectoryLabel(activeProgram)} · ${programTypeLabel(activeProgram)}`:state.program.name||'Current academic program';
    const assignmentFields=isAdmin?`<div class="field f12"><label>Department *</label><select id="auDepartment" ${openPrograms.length?'':'disabled'}><option value="">${openPrograms.length?'Select department':'Create an academic program first'}</option>${departmentOptions}</select></div><div class="field f12"><label>Academic program *</label><select id="auProgram" disabled><option value="">Select department first</option></select><span class="tiny">Programs and departments come from Academic Programs. Add or edit them there first.</span></div>`:`<div class="field f12"><label>Department *</label><select id="auDepartment" disabled><option value="${esc(hodDepartment)}">${esc(hodDepartment)}</option></select></div><div class="field f12"><label>Academic program *</label><select id="auProgram" disabled><option value="${esc(activeProgramId||'')}">${esc(hodProgramLabel)}</option></select></div>`;
    return roleHero()+pageHead('Access control','Users',isAdmin?'Manage authorized users across every academic program. Public registration is disabled.':'Manage users assigned to this academic program. Public registration is disabled.',actions)+`<div class="user-directory-note"><div class="automation-icon">↗</div><div><strong>Controlled access</strong><span>Users authenticate by email. Department and academic program assignments are selected from the Academic Programs master list.</span></div></div><div class="user-admin-grid"><div class="table-card"><table class="data-table"><thead><tr><th>User</th><th>Program / Department</th><th>Role</th><th>Status</th><th>Added</th><th>Action</th></tr></thead><tbody>${rows||'<tr><td colspan="6" class="empty">No authorized users have been added yet.</td></tr>'}</tbody></table></div><div class="card user-add-card"><h3>Add authorized user</h3><p>${isAdmin?'Select the department and academic program from the master Academic Programs list, then appoint an HOD, Coordinator, or Instructor.':'HOD can add Coordinators and Instructors to this program.'}</p><div class="form-grid"><div class="field f4"><label>Prefix *</label><select id="auPrefix"><option value="">Select prefix</option>${TITLE_PREFIXES.map(prefix=>`<option value="${esc(prefix)}">${esc(prefix)}</option>`).join('')}</select></div><div class="field f4"><label>First name *</label><input id="auFirst" autocomplete="off"></div><div class="field f4"><label>Last name *</label><input id="auLast" autocomplete="off"></div>${assignmentFields}<div class="field f12"><label>Role *</label><select id="auRole">${roleOptions}</select></div><div class="field f12"><label>Email *</label><input type="email" id="auEmail" placeholder="name@university.edu"></div><div class="field f12"><button class="btn btn-primary" id="addAuthorizedUser" style="width:100%">Add / assign user</button></div></div></div></div>`;
  }
''' + s[end:]

start = s.index('  function renderProgramsAdmin(){')
end = s.index('  function renderSetup(){', start)
s = s[:start] + r'''  function renderProgramsAdmin(){
    const departments=uniqueDepartments(programDirectory);
    const departmentSuggestions=departments.map(department=>`<option value="${esc(department)}"></option>`).join('');
    const programSuggestions=[...new Set(programDirectory.map(p=>String(p.name||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b)).map(name=>`<option value="${esc(name)}"></option>`).join('');
    const rows=programDirectory.map(p=>`<tr><td><strong>${esc(p.code)}</strong><div class="tiny">${esc(p.name)}</div></td><td><span class="tag blue">${esc(programTypeLabel(p))}</span></td><td>${esc(p.department||'—')}</td><td>${esc(p.institution||'—')}</td><td>${esc(p.college||'—')}</td><td>${esc(p.current_academic_year)}</td><td>${statusPill(p.status)}</td><td><button class="btn btn-ghost" data-program-toggle="${p.id}" data-program-status="${p.status}">${p.status==='Open'?'Close':'Open'}</button></td></tr>`).join('');
    return roleHero()+pageHead('System administration','Academic Programs','This is the master list for departments and academic programs. Saved values automatically become available in the Add User dropdowns.')+`<div class="user-admin-grid"><div class="table-card"><table class="data-table"><thead><tr><th>Academic program</th><th>Type</th><th>Department</th><th>Institution</th><th>College</th><th>Year</th><th>Status</th><th></th></tr></thead><tbody>${rows||'<tr><td colspan="8" class="empty">No academic programs yet. Add the first program to populate the user assignment dropdowns.</td></tr>'}</tbody></table></div><div class="card user-add-card"><h3>Add academic program</h3><p>Enter the department and program once here. Existing departments and program names appear as suggestions, and saved records become dropdown options when adding users.</p><div class="form-grid"><div class="field f12"><label>Department *</label><input id="apDepartment" list="apDepartmentList" placeholder="e.g. Health Information Management" autocomplete="off"><datalist id="apDepartmentList">${departmentSuggestions}</datalist><span class="tiny">Type a new department or reuse one already saved.</span></div><div class="field f8"><label>Academic program *</label><input id="apName" list="apProgramNameList" placeholder="e.g. Health Information and Technology Management" autocomplete="off"><datalist id="apProgramNameList">${programSuggestions}</datalist></div><div class="field f4"><label>Program type *</label><select id="apProgramType"><option value="">Select type</option>${PROGRAM_TYPES.map(type=>`<option value="${esc(type)}">${esc(type)}</option>`).join('')}</select></div><div class="field f4"><label>Program code *</label><input id="apCode" placeholder="BHIM" autocomplete="off"></div><div class="field f8"><label>Current academic year *</label><input id="apYear" value="2026–2027" autocomplete="off"></div><div class="field f12"><label>Institution</label><input id="apInstitution" autocomplete="off"></div><div class="field f12"><label>College</label><input id="apCollege" autocomplete="off"></div><div class="field f12"><button class="btn btn-primary" id="createAcademicProgram" style="width:100%">Add academic program</button></div></div></div></div>`;
  }
''' + s[end:]

start = s.index('  async function addAuthorizedUser(){')
end = s.index('  async function setUserStatus(', start)
s = s[:start] + r'''  async function addAuthorizedUser(){
    const isAdmin=state.role==='System Administrator';
    const titlePrefix=normalizeTitlePrefix($('auPrefix')?.value),first=$('auFirst')?.value.trim(),last=$('auLast')?.value.trim(),role=$('auRole')?.value,email=$('auEmail')?.value.trim().toLowerCase();
    const selectedDepartment=isAdmin?$('auDepartment')?.value.trim():(state.program.department||'').trim();
    const programId=isAdmin?$('auProgram')?.value:activeProgramId;
    const matchedProgram=programDirectory.find(p=>p.id===programId);
    const department=(matchedProgram?.department||selectedDepartment||'').trim();
    if(!titlePrefix||!first||!last||!department||!email||(backendEnabled&&!programId)){toast('Prefix, first name, last name, department, role, email, and academic program are required.');return;}
    if(isAdmin&&backendEnabled&&(!matchedProgram||matchedProgram.status!=='Open')){toast('Select an open academic program from the Academic Programs list.');return;}
    if(isAdmin&&matchedProgram&&selectedDepartment!==matchedProgram.department){toast('The selected academic program does not belong to that department.');return;}
    if(!$('auEmail')?.checkValidity()){toast('Enter a valid email address.');return;}
    const allowed=isAdmin?['HOD','Coordinator','Instructor']:['Instructor','Coordinator'];if(!allowed.includes(role)){toast('That role is not permitted here.');return;}
    const btn=$('addAuthorizedUser');if(btn){btn.disabled=true;btn.textContent='Adding…'}
    try{
      if(!backendEnabled){const users=loadLocalUsers();if(users.some(u=>String(u.email||'').toLowerCase()===email))throw new Error('This email is already authorized.');users.push({id:uid(),titlePrefix,firstName:first,lastName:last,department,role,email,active:true,createdAt:nowDate()});saveLocalUsers(users);userDirectory=users;}
      else{await Backend.invoke('admin-create-user',{title_prefix:titlePrefix,first_name:first,last_name:last,department,role,email,program_id:programId});await loadUsers();}
      render();toast('User added and assigned. They can sign in from their authorized email.');
    }catch(e){toast(e?.message||'Could not add user.');}
    finally{if(btn){btn.disabled=false;btn.textContent='Add / assign user'}}
  }
''' + s[end:]

start = s.index('  async function createAcademicProgram(){')
end = s.index('  async function toggleAcademicProgram(', start)
s = s[:start] + r'''  async function createAcademicProgram(){
    const code=$('apCode')?.value.trim().toUpperCase(),name=$('apName')?.value.trim(),programType=normalizeProgramType($('apProgramType')?.value),institution=$('apInstitution')?.value.trim()||'',college=$('apCollege')?.value.trim()||'',department=$('apDepartment')?.value.trim(),year=$('apYear')?.value.trim();
    if(!code||!name||!programType||!department||!year){toast('Department, academic program, program type, program code, and academic year are required.');return;}
    if(programDirectory.some(p=>String(p.code||'').trim().toLowerCase()===code.toLowerCase())){toast('That program code already exists.');return;}
    if(programDirectory.some(p=>String(p.name||'').trim().toLowerCase()===name.toLowerCase()&&String(p.department||'').trim().toLowerCase()===department.toLowerCase())){toast('That academic program already exists in this department.');return;}
    const btn=$('createAcademicProgram');btn.disabled=true;btn.textContent='Adding…';
    try{await Backend.insert('academic_programs',{code,name,program_type:programType,institution,college,department,status:'Open',current_academic_year:year,data:{academicYears:[year],programType},created_by:currentUser.id});await loadPrograms();render();toast('Academic program added. Its department and program are now available in the Users dropdowns.');}catch(e){toast(e?.message||'Could not create academic program.');}finally{if($('createAcademicProgram')){$('createAcademicProgram').disabled=false;$('createAcademicProgram').textContent='Add academic program';}}
  }
''' + s[end:]

old = """    if($('auProgram')){
      const syncDepartmentFromProgram=()=>{const program=findProgramFromInput($('auProgram').value);if(program&&$('auDepartment')&&!$('auDepartment').value.trim())$('auDepartment').value=program.department||'';};
      $('auProgram').addEventListener('change',syncDepartmentFromProgram);
      $('auProgram').addEventListener('blur',syncDepartmentFromProgram);
    }
"""
new = """    if(state.role==='System Administrator'&&$('auDepartment')&&$('auProgram')){
      const refreshProgramOptions=()=>{
        const department=$('auDepartment').value;
        const programs=programDirectory.filter(p=>p.status==='Open'&&p.department===department);
        $('auProgram').innerHTML=`<option value=\"\">${department?(programs.length?'Select academic program':'No open programs in this department'):'Select department first'}</option>${programs.map(p=>`<option value=\"${esc(p.id)}\">${esc(programDirectoryLabel(p))} · ${esc(programTypeLabel(p))}</option>`).join('')}`;
        $('auProgram').disabled=!department||programs.length===0;
      };
      $('auDepartment').addEventListener('change',refreshProgramOptions);
      refreshProgramOptions();
    }
"""
if old not in s:
    raise SystemExit('user dropdown binding not found')
s = s.replace(old, new, 1)
s = s.replace("const pg=programRows?.[0];if(pg){base.program={...base.program,name:pg.name,department:pg.department,college:pg.college,institution:pg.institution,academicYear:pg.current_academic_year};", "const pg=programRows?.[0];if(pg){base.program={...base.program,name:pg.name,programType:programTypeLabel(pg),department:pg.department,college:pg.college,institution:pg.institution,academicYear:pg.current_academic_year};", 1)
app.write_text(s)

seed = root / 'src/seed.js'
x = seed.read_text().replace("name:'Bachelor of Health Information Management',academicYear", "name:'Bachelor of Health Information Management',programType:'Bachelor',academicYear", 1)
seed.write_text(x)

fn = root / 'supabase/functions/admin-create-user/index.ts'
f = fn.read_text().replace('const department=String(body.department||"").trim();', 'const requestedDepartment=String(body.department||"").trim();', 1)
f = f.replace('select("id,status,department")', 'select("id,status,department,program_type")', 1)
f = f.replace('if(!program) return reply(404,{error:"Academic program not found"});', 'if(!program) return reply(404,{error:"Academic program not found"});\n  if(program.status!=="Open") return reply(400,{error:"Academic program is closed"});\n  const department=String(program.department||"").trim();\n  if(requestedDepartment&&requestedDepartment!==department) return reply(400,{error:"Department does not match the selected academic program"});', 1)
fn.write_text(f)

(root / 'supabase/migrations/20260910_academic_program_type.sql').write_text("""alter table public.academic_programs
  add column if not exists program_type text not null default 'Bachelor';

alter table public.academic_programs
  drop constraint if exists academic_programs_program_type_check;

alter table public.academic_programs
  add constraint academic_programs_program_type_check
  check (program_type in ('Diploma', 'Bachelor'));
""")

pkg = root / 'package.json'
pkg.write_text(pkg.read_text().replace('"version": "1.2.3"', '"version": "1.2.4"', 1))

chg = root / 'CHANGELOG.md'
c = chg.read_text()
entry = """\n### 1.2.4 — Academic Programs master list
- Academic Programs is now the master source for Department and Academic Program assignments.
- Added required Program Type with Diploma and Bachelor options.
- Saved departments and programs immediately populate the Add User dropdowns.
- Add User now uses strict Department and Academic Program dropdowns instead of free-text entry.
- Academic Program choices are filtered by the selected Department and include the program type.
\n"""
if '### 1.2.4' not in c:
    pos = c.find('\n') + 1
    c = c[:pos] + entry + c[pos:]
chg.write_text(c)

chk = root / 'scripts/check-project.js'
c = chk.read_text()
c = c.replace("assert.ok(app.includes('id=\"auProgram\" list=\"auProgramList\"'), 'SystemAdmin academic program entry must be writable');\nassert.ok(app.includes('id=\"auDepartment\"'), 'Authorized-user department entry is missing');", "assert.ok(app.includes('<select id=\"auDepartment\"') && app.includes('<select id=\"auProgram\"'), 'Department and academic program must be dropdowns');\nassert.ok(app.includes(\"const PROGRAM_TYPES = ['Diploma','Bachelor']\"), 'Academic program type options are missing');\nassert.ok(app.includes('id=\"apProgramType\"'), 'Program type selector is missing');\nassert.ok(app.includes('program_type:programType'), 'Program type is not persisted');", 1)
chk.write_text(c)

smoke = root / 'scripts/browser-smoke.js'
b = smoke.read_text().replace("  await expect('SystemAdmin program field is writable', \"document.getElementById('auProgram').tagName\", 'INPUT');\n  await expect('SystemAdmin department field is writable', \"document.getElementById('auDepartment').disabled||document.getElementById('auDepartment').readOnly\", false);", "  await expect('SystemAdmin department is a dropdown', \"document.getElementById('auDepartment').tagName\", 'SELECT');\n  await expect('SystemAdmin academic program is a dropdown', \"document.getElementById('auProgram').tagName\", 'SELECT');", 1)
smoke.write_text(b)
