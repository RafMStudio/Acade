from pathlib import Path
import re

root=Path('.')
app=root/'src/app.js'
s=app.read_text()

def block(text,start,end,replacement):
    a=text.index(start)
    b=text.index(end,a)
    return text[:a]+replacement+text[b:]

# Multi-program session state.
s=s.replace("  let programDirectory = [];\n  let membershipDirectory = [];\n", "  let programDirectory = [];\n  let membershipDirectory = [];\n  let accessibleProgramIds = [];\n")

# Academic year is HOD-owned settings data, not part of the permanent program master.
s=s.replace("    s.academicYears = Array.isArray(s.academicYears) && s.academicYears.length ? s.academicYears : [s.program.academicYear];\n    if(!s.academicYears.includes(s.program.academicYear)) s.academicYears.unshift(s.program.academicYear);", "    s.program.academicYear = String(s.program.academicYear||'').trim();\n    s.academicYears = Array.isArray(s.academicYears) ? [...new Set(s.academicYears.map(x=>String(x||'').trim()).filter(Boolean))] : [];\n    if(s.program.academicYear&&!s.academicYears.includes(s.program.academicYear)) s.academicYears.unshift(s.program.academicYear);")

# User directory: department default + optional program restriction.
render_users=r'''  function renderUsers(){
    const isAdmin=state.role==='System Administrator';
    const openPrograms=programDirectory.filter(p=>p.status==='Open');
    const departments=isAdmin?uniqueDepartments(openPrograms):[currentUser?.department||state.program.department].filter(Boolean);
    const departmentOptions=departments.map(department=>`<option value="${esc(department)}">${esc(department)}</option>`).join('');
    const roleOptions=isAdmin?'<option>HOD</option><option>Coordinator</option><option>Instructor</option>':'<option>Instructor</option><option>Coordinator</option>';
    const rows=userDirectory.map(u=>{
      const programs=(u.programIds||[]).map(id=>programDirectory.find(p=>p.id===id)).filter(Boolean);
      const access=u.role==='System Administrator'?'Global':u.limitProgramAccess?`${programs.length} selected program${programs.length===1?'':'s'}`:`All ${u.department||''} programs`;
      const detail=u.limitProgramAccess&&programs.length?programs.map(programDirectoryLabel).join(', '):u.department||'System';
      return `<tr><td><strong>${esc(displayUserName(u))}</strong><div class="tiny">${esc(u.email)}</div></td><td><strong>${esc(access)}</strong><div class="tiny">${esc(detail)}</div></td><td><span class="user-table-role">${esc(u.role)}</span></td><td><span class="user-table-role user-status-active">${u.active===false?'Inactive':'Active'}</span></td><td>${esc(u.createdAt?String(u.createdAt).slice(0,10):'—')}</td><td>${u.role==='System Administrator'?'—':`<button class="btn btn-ghost" data-user-status="${u.id}" data-user-active="${u.active===false?'1':'0'}" data-user-program="${esc(u.programIds?.[0]||u.programId||'')}">${u.active===false?'Reactivate':'Deactivate'}</button>`}</td></tr>`;
    }).join('');
    const actions=backendEnabled?`<button class="btn btn-ghost" id="backupAllData">${isAdmin?'Backup Entire System':'Backup Program'} (.xlsx)</button>`:'';
    const fixedDepartment=currentUser?.department||state.program.department||'';
    const departmentField=isAdmin?`<div class="field f12"><label>Department *</label><select id="auDepartment" ${departments.length?'':'disabled'}><option value="">${departments.length?'Select department':'Create an academic program first'}</option>${departmentOptions}</select></div>`:`<div class="field f12"><label>Department *</label><select id="auDepartment" disabled><option value="${esc(fixedDepartment)}">${esc(fixedDepartment)}</option></select></div>`;
    return roleHero()+pageHead('Access control','Users',isAdmin?'Assign users by department. Program access is department-wide unless you explicitly limit it.':'Manage users in your department. Program access is department-wide unless you explicitly limit it.',actions)+`
      <div class="user-directory-note"><div class="automation-icon">↗</div><div><strong>Department-based access</strong><span>A user normally receives every open academic program in the selected department, including programs added later. Tick Limit program access only when a user should see a smaller set.</span></div></div>
      <div class="user-admin-grid"><div class="table-card"><table class="data-table"><thead><tr><th>User</th><th>Department / Access</th><th>Role</th><th>Status</th><th>Added</th><th>Action</th></tr></thead><tbody>${rows||'<tr><td colspan="6" class="empty">No authorized users have been added yet.</td></tr>'}</tbody></table></div>
      <div class="card user-add-card"><h3>Add authorized user</h3><p>${isAdmin?'Choose a department. The user gets all programs in it by default.':'The user gets all programs in your department by default.'}</p><div class="form-grid"><div class="field f4"><label>Prefix *</label><select id="auPrefix"><option value="">Select prefix</option>${TITLE_PREFIXES.map(prefix=>`<option value="${esc(prefix)}">${esc(prefix)}</option>`).join('')}</select></div><div class="field f4"><label>First name *</label><input id="auFirst" autocomplete="off"></div><div class="field f4"><label>Last name *</label><input id="auLast" autocomplete="off"></div>${departmentField}<div class="field f12"><label class="access-limit-toggle"><input type="checkbox" id="auLimitPrograms"> <strong>Limit program access</strong></label><span class="tiny">Leave unchecked for access to every current and future open program in this department.</span></div><div class="field f12 hidden" id="auProgramLimitWrap"><label>Allowed academic programs *</label><div id="auProgramLimitList" class="program-access-list"></div></div><div class="field f12"><label>Role *</label><select id="auRole">${roleOptions}</select></div><div class="field f12"><label>Email *</label><input type="email" id="auEmail" placeholder="name@university.edu"></div><div class="field f12"><button class="btn btn-primary" id="addAuthorizedUser" style="width:100%">Add / assign user</button></div></div></div></div>`;
  }
'''
s=block(s,'  function renderUsers(){','  function renderProgramsAdmin(){',render_users)

render_programs=r'''  function renderProgramsAdmin(){
    const departments=uniqueDepartments(programDirectory);
    const departmentSuggestions=departments.map(department=>`<option value="${esc(department)}"></option>`).join('');
    const programSuggestions=[...new Set(programDirectory.map(p=>String(p.name||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b)).map(name=>`<option value="${esc(name)}"></option>`).join('');
    const rows=programDirectory.map(p=>`<tr><td><strong>${esc(p.code)}</strong><div class="tiny">${esc(p.name)}</div></td><td><span class="tag blue">${esc(programTypeLabel(p))}</span></td><td>${esc(p.department||'—')}</td><td>${esc(p.institution||'—')}</td><td>${esc(p.college||'—')}</td><td>${statusPill(p.status)}</td><td><button class="btn btn-ghost" data-program-toggle="${p.id}" data-program-status="${p.status}">${p.status==='Open'?'Close':'Open'}</button></td></tr>`).join('');
    return roleHero()+pageHead('System administration','Academic Programs','Create each academic program once. Academic years are configured later by the HOD in Program Settings, so a program is never duplicated for a new year.')+`
      <div class="user-admin-grid"><div class="table-card"><table class="data-table"><thead><tr><th>Academic program</th><th>Type</th><th>Department</th><th>Institution</th><th>College</th><th>Status</th><th></th></tr></thead><tbody>${rows||'<tr><td colspan="7" class="empty">No academic programs yet.</td></tr>'}</tbody></table></div>
      <div class="card user-add-card"><h3>Add academic program</h3><p>Programs are permanent master records. Do not enter an academic year here.</p><div class="form-grid"><div class="field f12"><label>Department *</label><input id="apDepartment" list="apDepartmentList" placeholder="e.g. Health Information Management" autocomplete="off"><datalist id="apDepartmentList">${departmentSuggestions}</datalist></div><div class="field f8"><label>Academic program *</label><input id="apName" list="apProgramNameList" placeholder="e.g. Health Information Management" autocomplete="off"><datalist id="apProgramNameList">${programSuggestions}</datalist></div><div class="field f4"><label>Program type *</label><select id="apProgramType"><option value="">Select type</option>${PROGRAM_TYPES.map(type=>`<option value="${esc(type)}">${esc(type)}</option>`).join('')}</select></div><div class="field f4"><label>Program code *</label><input id="apCode" placeholder="BHIM" autocomplete="off"></div><div class="field f12"><label>Institution</label><input id="apInstitution" autocomplete="off"></div><div class="field f12"><label>College</label><input id="apCollege" autocomplete="off"></div><div class="field f12"><button class="btn btn-primary" id="createAcademicProgram" style="width:100%">Add academic program</button></div></div></div></div>`;
  }
'''
s=block(s,'  function renderProgramsAdmin(){','  function renderSetup(){',render_programs)

render_setup=r'''  function renderSetup(){
    if(state.role==='System Administrator') return renderProgramsAdmin();
    const managed=programDirectory.filter(p=>accessibleProgramIds.includes(p.id));
    const identity=`<div class="card"><h3 style="margin-top:0">Program identity</h3><div class="form-grid"><div class="field f12"><label>Academic program</label><input value="${esc(state.program.name)}" disabled></div><div class="field f6"><label>Program type</label><input value="${esc(state.program.programType||'—')}" disabled></div><div class="field f6"><label>Department</label><input value="${esc(state.program.department)}" disabled></div><div class="field f6"><label>Institution</label><input value="${esc(state.program.institution||'—')}" disabled></div><div class="field f6"><label>College</label><input value="${esc(state.program.college||'—')}" disabled></div></div><p class="tiny">Program identity is controlled by the System Administrator. ${managed.length>1?'Use the Program selector in the top bar to configure another program.':''}</p></div>`;
    const settings=`<div class="card"><h3 style="margin-top:0">Academic year settings</h3><p class="tiny">Academic years belong to this program's settings and do not create another Academic Program record.</p><div class="form-grid"><div class="field f6"><label>Current academic year *</label><input id="spYear" value="${esc(state.program.academicYear)}" placeholder="2026–2027"></div><div class="field f6"><label>Available academic years *</label><input id="spYears" value="${esc(state.academicYears.join(', '))}" placeholder="2026–2027, 2027–2028"></div><div class="field f12"><button class="btn btn-primary" id="saveSetup">Save Program Settings</button></div></div></div>`;
    return roleHero()+pageHead('Administration','Program Settings','The HOD configures academic years separately for each assigned academic program. Program identity stays permanent.')+`<div class="grid grid-2">${identity}${settings}</div><div class="card" style="margin-top:14px"><h3 style="margin-top:0">PLO targets</h3>${state.plos.map((p,i)=>`<div class="setup-plo-row"><strong>${esc(p.code)}</strong><span>${esc(p.name)}</span><input type="number" min="0" max="100" value="${p.target}" data-plo-target="${i}"></div>`).join('')}<button class="btn btn-ghost" id="savePloTargets" style="margin-top:12px">Save targets</button></div>`;
  }
'''
s=block(s,'  function renderSetup(){','\n\n  function openReport(',render_setup+'\n\n')

# User creation payload.
add_user=r'''  async function addAuthorizedUser(){
    const isAdmin=state.role==='System Administrator';
    const titlePrefix=normalizeTitlePrefix($('auPrefix')?.value),first=$('auFirst')?.value.trim(),last=$('auLast')?.value.trim(),role=$('auRole')?.value,email=$('auEmail')?.value.trim().toLowerCase();
    const department=isAdmin?$('auDepartment')?.value.trim():(currentUser?.department||state.program.department||'').trim();
    const limitProgramAccess=!!$('auLimitPrograms')?.checked;
    const programIds=limitProgramAccess?[...document.querySelectorAll('[data-au-program]:checked')].map(el=>el.value):[];
    const departmentPrograms=programDirectory.filter(p=>p.status==='Open'&&p.department===department);
    if(!titlePrefix||!first||!last||!department||!email){toast('Prefix, first name, last name, department, role, and email are required.');return;}
    if(backendEnabled&&!departmentPrograms.length){toast('This department has no open academic programs. Add a program first.');return;}
    if(limitProgramAccess&&!programIds.length){toast('Select at least one academic program or turn off Limit program access.');return;}
    if(!$('auEmail')?.checkValidity()){toast('Enter a valid email address.');return;}
    const allowed=isAdmin?['HOD','Coordinator','Instructor']:['Instructor','Coordinator'];if(!allowed.includes(role)){toast('That role is not permitted here.');return;}
    const btn=$('addAuthorizedUser');if(btn){btn.disabled=true;btn.textContent='Adding…'}
    try{
      if(!backendEnabled){const users=loadLocalUsers();if(users.some(u=>String(u.email||'').toLowerCase()===email))throw new Error('This email is already authorized.');users.push({id:uid(),titlePrefix,firstName:first,lastName:last,department,role,email,limitProgramAccess,programIds,active:true,createdAt:nowDate()});saveLocalUsers(users);userDirectory=users;}
      else{await Backend.invoke('admin-create-user',{title_prefix:titlePrefix,first_name:first,last_name:last,department,role,email,limit_program_access:limitProgramAccess,program_ids:programIds});await loadUsers();}
      render();toast(limitProgramAccess?'User added with limited program access.':'User added with access to all department programs.');
    }catch(e){toast(e?.message||'Could not add user.');}finally{if(btn){btn.disabled=false;btn.textContent='Add / assign user'}}
  }
'''
s=block(s,'  async function addAuthorizedUser(){','  async function setUserStatus(',add_user)

create_program=r'''  async function createAcademicProgram(){
    const code=$('apCode')?.value.trim().toUpperCase(),name=$('apName')?.value.trim(),programType=normalizeProgramType($('apProgramType')?.value),institution=$('apInstitution')?.value.trim()||'',college=$('apCollege')?.value.trim()||'',department=$('apDepartment')?.value.trim();
    if(!code||!name||!programType||!department){toast('Department, academic program, program type, and program code are required.');return;}
    if(programDirectory.some(p=>String(p.code||'').trim().toLowerCase()===code.toLowerCase())){toast('That program code already exists.');return;}
    if(programDirectory.some(p=>String(p.name||'').trim().toLowerCase()===name.toLowerCase()&&String(p.department||'').trim().toLowerCase()===department.toLowerCase())){toast('That academic program already exists in this department.');return;}
    const btn=$('createAcademicProgram');btn.disabled=true;btn.textContent='Adding…';
    try{await Backend.insert('academic_programs',{code,name,program_type:programType,institution,college,department,status:'Open',current_academic_year:null,data:{programType},created_by:currentUser.id});await loadPrograms();render();toast('Academic program added. The HOD can now configure its academic years in Program Settings.');}catch(e){toast(e?.message||'Could not create academic program.');}finally{if($('createAcademicProgram')){$('createAcademicProgram').disabled=false;$('createAcademicProgram').textContent='Add academic program';}}
  }
'''
s=block(s,'  async function createAcademicProgram(){','  async function toggleAcademicProgram(',create_program)

# Load users with all memberships and access scope.
load_users=r'''  async function loadUsers(){
    if(!['Head of Department','System Administrator'].includes(state.role)) return;
    if(!backendEnabled){userDirectory=loadLocalUsers().filter(u=>!u.testOnly);return;}
    try{
      const rows=await Backend.select('profiles','select=id,email,title_prefix,first_name,last_name,department,role,active,default_program_id,limit_program_access,created_at&order=created_at.asc')||[];
      const memberships=await Backend.select('program_memberships','select=program_id,user_id,role,active&active=eq.true')||[];
      membershipDirectory=memberships;
      userDirectory=rows.map(u=>{
        const mine=memberships.filter(m=>m.user_id===u.id&&m.active!==false);
        return {id:u.id,email:u.email,titlePrefix:normalizeTitlePrefix(u.title_prefix),firstName:u.first_name,lastName:u.last_name,department:u.department,role:dbRoleToUi(u.role),active:u.active,createdAt:u.created_at,programId:mine[0]?.program_id||u.default_program_id||null,programIds:mine.map(m=>m.program_id),limitProgramAccess:!!u.limit_program_access};
      });
      if(state.role==='Head of Department')userDirectory=userDirectory.filter(u=>u.department===currentUser?.department&&u.role!=='System Administrator');
    }catch(e){userDirectory=[];}
  }
'''
s=block(s,'  async function loadUsers(){','\n  async function addAuthorizedUser(){',load_users+'\n')

# Production hydration supports multiple program memberships; settings own years.
hydrate=r'''  async function hydrateSharedState(){
    if(!backendEnabled){state=normalizeState(loadState());state.role=currentUser.role;ploYear=state.program.academicYear;ploTerm='Annual';return;}
    await loadPrograms();
    if(currentUser.role==='System Administrator'){
      accessibleProgramIds=[];activeProgramId=null;backendProgramSettingsId=null;const base=clone(seed);base.reports=[];base.operational=[];base.audit=[];state=normalizeState(base);state.role=currentUser.role;ploYear=state.program.academicYear;ploTerm='Annual';return;
    }
    const memberships=await Backend.select('program_memberships',`user_id=eq.${encodeURIComponent(currentUser.id)}&active=eq.true&select=program_id,role`);
    membershipDirectory=memberships||[];
    accessibleProgramIds=[...new Set(membershipDirectory.map(m=>m.program_id).filter(Boolean))];
    if(!accessibleProgramIds.length) throw new Error('Your account is not assigned to an academic program. Contact the System Administrator or HOD.');
    if(!activeProgramId||!accessibleProgramIds.includes(activeProgramId))activeProgramId=accessibleProgramIds.includes(currentUser.defaultProgramId)?currentUser.defaultProgramId:accessibleProgramIds[0];
    const base=clone(seed);base.reports=[];base.operational=[];base.audit=[];base.academicYears=[];base.program={...base.program,academicYear:''};backendProgramSettingsId=null;
    const pid=encodeURIComponent(activeProgramId);
    const [programRows,settingsRows,ploRows,operationalRows,reportRows]=await Promise.all([
      Backend.select('academic_programs',`id=eq.${pid}&select=*`),
      Backend.select('program_settings',`program_id=eq.${pid}&is_active=eq.true&select=*&order=updated_at.desc&limit=1`),
      Backend.select('plos',`program_id=eq.${pid}&active=eq.true&select=*&order=code.asc`),
      Backend.select('operational_plans',`program_id=eq.${pid}&select=*&order=updated_at.desc&limit=1`),
      Backend.select('course_reports',`program_id=eq.${pid}&select=*&order=updated_at.desc`)
    ]);
    const pg=programRows?.[0];if(pg){base.program={...base.program,name:pg.name,programType:programTypeLabel(pg),department:pg.department,college:pg.college,institution:pg.institution,academicYear:''};base.academicYears=[];}
    if(settingsRows?.[0]){const row=settingsRows[0];backendProgramSettingsId=row.id;base.program={...base.program,academicYear:String(row.academic_year||row.data?.academicYear||'').trim()};base.academicYears=Array.isArray(row.data?.academicYears)?row.data.academicYears.filter(Boolean):(base.program.academicYear?[base.program.academicYear]:[]);}
    if(ploRows?.length)base.plos=ploRows.map(p=>({code:p.code,name:p.name,target:Number(p.target)}));
    if(operationalRows?.[0]?.data?.items)base.operational=operationalRows[0].data.items;
    base.reports=(reportRows||[]).map(reportFromDb);
    if(currentUser.role==='Head of Department'){try{const auditRows=await Backend.select('audit_log',`details->>program_id=eq.${pid}&select=*&order=created_at.desc&limit=50`);base.audit=(auditRows||[]).map(a=>({icon:'•',title:a.action,detail:`${a.entity_type}${a.entity_id?` · ${a.entity_id}`:''}`,time:String(a.created_at||'').slice(0,16).replace('T',' ')}));}catch{}}
    state=normalizeState(base);state.role=currentUser.role;ploYear=state.program.academicYear;ploTerm='Annual';
  }

  async function switchActiveProgram(programId){
    if(!backendEnabled||!accessibleProgramIds.includes(programId)||programId===activeProgramId)return;
    activeProgramId=programId;currentReportId=null;currentPortfolioId=null;activePlo=null;
    try{await hydrateSharedState();render();toast(`Switched to ${state.program.name}.`);}catch(e){toast(e?.message||'Could not switch academic program.');}
  }

'''
s=block(s,'  async function hydrateSharedState(){','  async function onAuthenticated(user){',hydrate+'  async function onAuthenticated(user){')
# Above replacement duplicates function marker body opening; fix accidental duplicate signature if present.
s=s.replace('  async function onAuthenticated(user){  async function onAuthenticated(user){','  async function onAuthenticated(user){')

# Program switcher + dynamic nav wording.
old="""    if($('roleContext')) $('roleContext').innerHTML=`<span>Workspace</span><b>${esc(cfg.label)}</b>`;
    if($('avatarLabel')){$('avatarLabel').textContent=currentUserInitials();$('avatarLabel').title=currentUserName();}
"""
new="""    if($('roleContext')) $('roleContext').innerHTML=`<span>Workspace</span><b>${esc(cfg.label)}</b>`;
    const setupButton=document.querySelector('[data-view=setup]');if(setupButton)setupButton.childNodes[setupButton.childNodes.length-1].textContent=state.role==='System Administrator'?' Academic Programs':' Program Settings';
    const programWrap=$('workspaceProgramWrap'),programSelect=$('workspaceProgramSelect');
    if(programWrap&&programSelect){const programs=programDirectory.filter(p=>accessibleProgramIds.includes(p.id)&&p.status==='Open');programWrap.classList.toggle('hidden',state.role==='System Administrator'||programs.length<2);programSelect.innerHTML=programs.map(p=>`<option value=\"${esc(p.id)}\" ${p.id===activeProgramId?'selected':''}>${esc(programDirectoryLabel(p))}</option>`).join('');}
    if($('avatarLabel')){$('avatarLabel').textContent=currentUserInitials();$('avatarLabel').title=currentUserName();}
"""
if old not in s: raise SystemExit('syncRoleUI marker missing')
s=s.replace(old,new)
s=s.replace("if($('sideAcademicYear'))$('sideAcademicYear').textContent=state.program.academicYear;", "if($('sideAcademicYear'))$('sideAcademicYear').textContent=state.program.academicYear||'Not set';")

# New report cannot precede HOD year setup.
s=s.replace("  function openNewReport(){\n    if(!canCreateReport()){toast('Only the Instructor workspace creates Course Reports.');return;}\n    const years=[...new Set([state.program.academicYear,...state.academicYears])];", "  function openNewReport(){\n    if(!canCreateReport()){toast('Only the Instructor workspace creates Course Reports.');return;}\n    const years=[...new Set([state.program.academicYear,...state.academicYears].filter(Boolean))];\n    if(!years.length){toast('Academic year is not configured for this program. Ask the HOD to set it in Program Settings.');return;}")

# HOD settings save only years; permanent program identity remains Admin-owned.
old_save=re.search(r"    if\(\$\('saveSetup'\)\)\$\('saveSetup'\)\.addEventListener\('click',async\(\)=>\{.*?\}\);\n    if\(\$\('savePloTargets'\)\)",s,re.S)
if not old_save: raise SystemExit('saveSetup handler missing')
replacement="""    if($('saveSetup'))$('saveSetup').addEventListener('click',async()=>{const current=$('spYear').value.trim();const years=[...new Set($('spYears').value.split(',').map(x=>x.trim()).filter(Boolean))];if(!current){toast('Current academic year is required.');return;}if(!years.includes(current))years.unshift(current);state.program.academicYear=current;state.academicYears=years;ploYear=current;try{await persistProgramSetup();saveState();render();toast('Program Settings saved.');}catch(e){toast(e?.message||'Could not save Program Settings.');}});
    if($('savePloTargets'))"""
s=s[:old_save.start()]+replacement+s[old_save.end():]

# Add-user access controls replace the old dependent program dropdown binding.
start="    if(state.role==='System Administrator'&&$('auDepartment')&&$('auProgram')){"
if start in s:
    a=s.index(start);b=s.index("    if($('addAuthorizedUser'))",a)
    bind=r'''    if($('auLimitPrograms')&&$('auDepartment')&&$('auProgramLimitWrap')&&$('auProgramLimitList')){
      const refreshProgramLimitList=()=>{const department=$('auDepartment').value;const programs=programDirectory.filter(p=>p.status==='Open'&&p.department===department);$('auProgramLimitList').innerHTML=programs.map(p=>`<label class="program-access-option"><input type="checkbox" data-au-program value="${esc(p.id)}"><span><strong>${esc(programDirectoryLabel(p))}</strong><small>${esc(programTypeLabel(p))}</small></span></label>`).join('')||'<span class="tiny">No open academic programs in this department.</span>';};
      const syncProgramLimitVisibility=()=>{$('auProgramLimitWrap').classList.toggle('hidden',!$('auLimitPrograms').checked);if($('auLimitPrograms').checked)refreshProgramLimitList();};
      $('auLimitPrograms').addEventListener('change',syncProgramLimitVisibility);$('auDepartment').addEventListener('change',refreshProgramLimitList);refreshProgramLimitList();syncProgramLimitVisibility();
    }
'''
    s=s[:a]+bind+s[b:]

# Switcher event.
s=s.replace("    $('signOutBtn')?.addEventListener('click',signOut);", "    $('signOutBtn')?.addEventListener('click',signOut);\n    $('workspaceProgramSelect')?.addEventListener('change',e=>switchActiveProgram(e.target.value));")

# Production auth maps new access flag.
s=s.replace("defaultProgramId:p.default_program_id||null});", "defaultProgramId:p.default_program_id||null,limitProgramAccess:!!p.limit_program_access});")

app.write_text(s)

# Backend profile includes restriction flag.
backend=root/'src/backend.js'
b=backend.read_text().replace('default_program_id,created_at','default_program_id,limit_program_access,created_at')
backend.write_text(b)

# Topbar program switcher; Admin/HOD nav label starts generic and is changed by role.
idx=root/'index.source.html'
i=idx.read_text()
i=i.replace('<button class="nav-item" data-view="setup" type="button"><span class="nav-icon">⚙</span>Program Setup</button>','<button class="nav-item" data-view="setup" type="button"><span class="nav-icon">⚙</span> Program Settings</button>')
i=i.replace('<span class="role-context" id="roleContext"><span>Workspace</span><b>Loading</b></span>','<span class="role-context" id="roleContext"><span>Workspace</span><b>Loading</b></span>\n<div class="role-switch hidden" id="workspaceProgramWrap"><span>Program</span><select id="workspaceProgramSelect" aria-label="Academic program"></select></div>')
idx.write_text(i)

# Small UI for restricted-program checkboxes.
styles=root/'src/styles.css'
css=styles.read_text()+'''\n.program-access-list{display:grid;gap:7px;margin-top:7px}.program-access-option{display:flex;align-items:center;gap:9px;border:1px solid var(--line);border-radius:9px;padding:9px 10px;background:#fafafa;cursor:pointer}.program-access-option input{width:16px;height:16px}.program-access-option span{display:flex;flex-direction:column;gap:2px}.program-access-option strong{font-size:11px}.program-access-option small{font-size:9px;color:var(--muted)}.access-limit-toggle{display:flex!important;align-items:center;gap:8px}.access-limit-toggle input{width:16px;height:16px}\n'''
styles.write_text(css)

# Repository Edge Function mirrors production v6.
edge=root/'supabase/functions/admin-create-user/index.ts'
edge.write_text(r'''import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";
const cors={"Access-Control-Allow-Origin":"https://acadeloop.com","Access-Control-Allow-Headers":"authorization, x-client-info, apikey, content-type","Access-Control-Allow-Methods":"POST, OPTIONS"};
const reply=(status:number,body:unknown)=>new Response(JSON.stringify(body),{status,headers:{...cors,"Content-Type":"application/json","Cache-Control":"no-store"}});
const allowedPrefixes=['Mr.','Ms.','Dr.'];
Deno.serve(async(req:Request)=>{
 if(req.method==='OPTIONS')return new Response('ok',{headers:cors});if(req.method!=='POST')return reply(405,{error:'Method not allowed'});
 const token=(req.headers.get('Authorization')||'').replace(/^Bearer\s+/i,'').trim();if(!token)return reply(401,{error:'Authentication required'});
 const supabase=createClient(Deno.env.get('SUPABASE_URL')!,Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,{auth:{persistSession:false}});const {data:authData}=await supabase.auth.getUser(token);if(!authData.user)return reply(401,{error:'Invalid session'});
 const {data:caller}=await supabase.from('profiles').select('id,role,active,department').eq('id',authData.user.id).single();if(!caller?.active||!['SystemAdmin','HOD'].includes(caller.role))return reply(403,{error:'You cannot add users'});
 let body:any;try{body=await req.json()}catch{return reply(400,{error:'Invalid request'})};const email=String(body.email||'').trim().toLowerCase(),titlePrefix=String(body.title_prefix||body.titlePrefix||'').trim(),firstName=String(body.first_name||body.firstName||'').trim(),lastName=String(body.last_name||body.lastName||'').trim(),department=String(body.department||'').trim(),role=String(body.role||'').trim(),limitProgramAccess=Boolean(body.limit_program_access??body.limitProgramAccess??false),requestedProgramIds=Array.isArray(body.program_ids||body.programIds)?[...new Set((body.program_ids||body.programIds).map((x:any)=>String(x||'').trim()).filter(Boolean))]:[];
 if(!email||!/^\S+@\S+\.\S+$/.test(email))return reply(400,{error:'A valid email is required'});if(!allowedPrefixes.includes(titlePrefix))return reply(400,{error:'Prefix must be Mr., Ms., or Dr.'});if(!firstName||!lastName||!department)return reply(400,{error:'First name, last name, and department are required'});if(!['HOD','Coordinator','Instructor'].includes(role))return reply(400,{error:'Role must be HOD, Coordinator, or Instructor'});if(caller.role==='HOD'&&role==='HOD')return reply(403,{error:'Only System Administrator can appoint an HOD'});if(caller.role==='HOD'&&caller.department!==department)return reply(403,{error:'You may only add users to your department'});
 const {data:departmentPrograms,error:programError}=await supabase.from('academic_programs').select('id,department,status').eq('department',department).eq('status','Open');if(programError)return reply(500,{error:programError.message});if(!departmentPrograms?.length)return reply(400,{error:'This department has no open academic programs'});if(caller.role==='HOD'){const ids=departmentPrograms.map((p:any)=>p.id);const {data:mine}=await supabase.from('program_memberships').select('program_id').eq('user_id',caller.id).eq('role','HOD').eq('active',true).in('program_id',ids);if(!mine?.length)return reply(403,{error:'You are not assigned as HOD for this department'});}
 const validIds=new Set(departmentPrograms.map((p:any)=>p.id));if(limitProgramAccess&&requestedProgramIds.length===0)return reply(400,{error:'Select at least one academic program when program access is limited'});if(requestedProgramIds.some((id:string)=>!validIds.has(id)))return reply(400,{error:'One or more selected programs do not belong to this department'});const accessibleProgramIds=limitProgramAccess?requestedProgramIds:departmentPrograms.map((p:any)=>p.id),defaultProgramId=accessibleProgramIds[0]||null;
 const {data:existingProfile}=await supabase.from('profiles').select('id,email,role').eq('email',email).maybeSingle();let userId=existingProfile?.id||null;if(existingProfile?.role==='SystemAdmin')return reply(403,{error:'System Administrator accounts cannot be reassigned here'});
 if(!userId){const {data:created,error:createError}=await supabase.auth.admin.createUser({email,email_confirm:true,user_metadata:{title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department},app_metadata:{role}});if(createError||!created.user)return reply(400,{error:createError?.message||'Could not create user'});userId=created.user.id;const {error:profileError}=await supabase.from('profiles').insert({id:userId,email,title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department,role,active:true,default_program_id:defaultProgramId,limit_program_access:limitProgramAccess,created_by:caller.id});if(profileError){await supabase.auth.admin.deleteUser(userId);return reply(500,{error:profileError.message});}}else{const {error:updateError}=await supabase.from('profiles').update({title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department,role,active:true,default_program_id:defaultProgramId,limit_program_access:limitProgramAccess}).eq('id',userId);if(updateError)return reply(500,{error:updateError.message});await supabase.auth.admin.updateUserById(userId,{user_metadata:{title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department},app_metadata:{role}});}
 const {error:deleteError}=await supabase.from('program_memberships').delete().eq('user_id',userId);if(deleteError)return reply(500,{error:deleteError.message});if(accessibleProgramIds.length){const memberships=accessibleProgramIds.map((programId:string)=>({program_id:programId,user_id:userId,role,active:true,created_by:caller.id}));const {error:membershipError}=await supabase.from('program_memberships').insert(memberships);if(membershipError)return reply(500,{error:membershipError.message});}await supabase.from('audit_log').insert({actor_id:caller.id,action:'create_or_assign_user',entity_type:'profile',entity_id:userId,details:{email,title_prefix:titlePrefix,role,department,limit_program_access:limitProgramAccess,program_ids:accessibleProgramIds}});return reply(200,{user:{id:userId,email,title_prefix:titlePrefix,first_name:firstName,last_name:lastName,department,role,limit_program_access:limitProgramAccess,program_ids:accessibleProgramIds,active:true}});
});
''')

migration=root/'supabase/migrations/20260911_department_wide_program_access.sql'
migration.write_text('''alter table public.profiles\n  add column if not exists limit_program_access boolean not null default false;\n\nalter table public.academic_programs\n  alter column current_academic_year drop default,\n  alter column current_academic_year drop not null;\n\nupdate public.academic_programs set current_academic_year = null;\n\ninsert into public.program_memberships (program_id, user_id, role, active, created_by)\nselect ap.id, p.id, p.role, p.active, p.created_by\nfrom public.profiles p join public.academic_programs ap on ap.department = p.department\nwhere p.role in ('HOD','Coordinator','Instructor') and p.limit_program_access = false\non conflict (program_id, user_id) do update set role=excluded.role, active=excluded.active;\n\ncreate or replace function public.sync_department_memberships_for_new_program() returns trigger language plpgsql set search_path=public as $$\nbegin\n insert into public.program_memberships(program_id,user_id,role,active,created_by)\n select new.id,p.id,p.role,p.active,p.created_by from public.profiles p\n where p.department=new.department and p.role in ('HOD','Coordinator','Instructor') and p.limit_program_access=false\n on conflict(program_id,user_id) do update set role=excluded.role,active=excluded.active;\n return new;\nend;$$;\ndrop trigger if exists academic_programs_sync_department_memberships on public.academic_programs;\ncreate trigger academic_programs_sync_department_memberships after insert on public.academic_programs for each row execute function public.sync_department_memberships_for_new_program();\n''')

# Test contracts.
check=root/'scripts/check-project.js'
c=check.read_text()
c=c.replace("assert.ok(app.includes('<select id=\"auDepartment\"') && app.includes('<select id=\"auProgram\"'), 'Department and academic program must be dropdowns');", "assert.ok(app.includes('<select id=\"auDepartment\"'), 'Department must be selected from the Academic Programs master list');\nassert.ok(app.includes('id=\"auLimitPrograms\"') && app.includes('data-au-program'), 'Optional limited program access controls are missing');\nassert.ok(!app.includes('id=\"apYear\"'), 'Academic Programs must not own academic years');\nassert.ok(app.includes('id=\"spYear\"') && app.includes('id=\"spYears\"'), 'HOD Program Settings must own academic years');")
check.write_text(c)

browser=root/'scripts/browser-smoke.js'
br=browser.read_text()
br=br.replace("  await expect('SystemAdmin academic program is a dropdown', \"document.getElementById('auProgram').tagName\", 'SELECT');", "  await expect('SystemAdmin no longer assigns a program by default', \"document.getElementById('auProgram')===null\", true);\n  await expect('SystemAdmin can limit program access', \"!!document.getElementById('auLimitPrograms')\", true);")
browser.write_text(br)

pkg=root/'package.json'
p=pkg.read_text().replace('"version": "1.2.4"','"version": "1.2.5"')
pkg.write_text(p)

ch=root/'CHANGELOG.md'
ct=ch.read_text()
ct=ct.replace('# Changelog\n','# Changelog\n\n### 1.2.5 — Permanent programs and department-wide access\n- Academic Programs are permanent master records and no longer contain an academic year.\n- HOD sets current and available academic years separately in Program Settings for each accessible program.\n- New users are assigned by Department and receive all open programs in that department by default.\n- Added optional Limit program access control for Admin/HOD to restrict a user to selected programs.\n- Unrestricted users automatically receive access when a new program is later added to their department.\n- Added a top-bar program switcher for users who can access more than one program.\n\n')
ch.write_text(ct)

print('Applied Acadeloop v1.2.5 source changes')
