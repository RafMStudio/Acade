
(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const esc = (v='') => String(v).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const uid = () => globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2,8) + Date.now().toString(36).slice(-5);
  const nowDate = () => { const d=new Date(), pad=n=>String(n).padStart(2,'0'); return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`; };
  const clamp = (n,min=0,max=100) => Math.max(min,Math.min(max,Number(n)||0));
  const Core = window.AcadeloopCore;
  const Backend = window.AcadeloopBackend;
  if(!Core) throw new Error('Itqan core failed to load.');
  const {
    TERMS, LETTER_GRADE_LABELS, GRADE_DEFS: gradeDefs,
    sectionLabel, blankSectionFor, ensureSectionModel, effectiveSectionKey, activeSectionKeys,
    syncFlatFromEffective, expectedCombinedSnapshot, enforceCombinedIntegrity, reportVariant,
    gradeCount, gradeTotal, gradeInflationForSection, reportQualityFlags, pooledGradeDistribution,
    reportAverageAttainment, reportCompleteness, calculatePloRollups,
    validateReport
  } = Core;
  const STORAGE_KEY = 'acadeloop_program_quality_v100';
  const TITLE_PREFIXES = ['Mr.','Ms.','Dr.'];
  const PROGRAM_TYPES = ['Diploma','Bachelor'];
  const normalizeTitlePrefix = value => TITLE_PREFIXES.includes(String(value||'').trim()) ? String(value).trim() : '';
  const normalizeProgramType = value => PROGRAM_TYPES.includes(String(value||'').trim()) ? String(value).trim() : '';
  const displayUserName = user => [normalizeTitlePrefix(user?.titlePrefix), user?.firstName, user?.lastName].filter(Boolean).join(' ').trim() || user?.email || 'User';
  const programTypeLabel = program => normalizeProgramType(program?.program_type||program?.programType||program?.data?.programType) || 'Bachelor';
  const programDirectoryLabel = program => program ? `${program.name} (${program.code})` : '';
  const uniqueDepartments = programs => [...new Set((programs||[]).map(program=>String(program?.department||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
  let dashboardInflationOnly = false;
  let supervisorData = null;
  let supervisorError = '';
  let supervisorFilters = {department:'',program:'',year:'',term:'Annual',status:'',view:'all'};



  const ROLE_CONFIG = {
    'System Administrator': {
      views:['dashboard','users','setup'], label:'System administration', avatar:'SA',
      dashboard:'Itqan Administration', description:'Manage academic programs, appoint HODs, control users, and back up the complete Itqan system.'
    },
    'Instructor': {
      views:['dashboard','course-reports','course-portfolios','kpis'], label:'Instructor workspace', avatar:'IN',
      dashboard:'My Course Quality', description:'Create course reports by reporting period and section, then submit them for coordinator approval.'
    },
    'Coordinator': {
      views:['dashboard','course-reports','course-portfolios','plo','apr','kpis','operational','automations'], label:'Quality coordination', avatar:'CO',
      dashboard:'Quality Approval Center', description:'Review submitted reports exactly as entered, return them for revision, or approve them into official program calculations.'
    },
    'Head of Department': {
      views:['dashboard','course-reports','course-portfolios','plo','apr','kpis','operational','users','setup'], label:'Executive oversight', avatar:'HD',
      dashboard:'Department Quality Overview', description:'View approved quality results and control who is allowed to access Itqan.'
    },
    'APU': {
      views:['dashboard','course-reports','plo','apr','kpis','operational'], label:'Institution supervision', avatar:'AP',
      dashboard:'APU Supervision Dashboard', description:'Read-only oversight across all academic programs, academic years, and semesters.'
    },
    'VDAA': {
      views:['dashboard','course-reports','plo','apr','kpis','operational'], label:'Institution supervision', avatar:'VD',
      dashboard:'VDAA Supervision Dashboard', description:'Read-only oversight across all academic programs, academic years, and semesters.'
    }
  };

  const seed = window.ACADELOOP_SEED;

  const backendEnabled = !!Backend?.enabled;
  const normalizeLoginEmail = value => String(value||'').trim().toLowerCase();
  const validLoginEmail = value => { const email=normalizeLoginEmail(value); return email.length<=254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/u.test(email); };
  function canonicalUiRole(role){
    const value=String(role||'').trim();
    if(value==='SystemAdmin'||value==='System Administrator') return 'System Administrator';
    if(value==='HOD'||value==='Head of Department') return 'Head of Department';
    if(value==='Coordinator') return 'Coordinator';
    if(value==='Instructor') return 'Instructor';
    if(value==='APU') return 'APU';
    if(value==='VDAA') return 'VDAA';
    return '';
  }
  const isSupervisorRole = role => ['APU','VDAA'].includes(canonicalUiRole(role));
  const dbRoleToUi = role => canonicalUiRole(role);
  const uiRoleToDb = role => canonicalUiRole(role)==='Head of Department' ? 'HOD' : canonicalUiRole(role)==='System Administrator' ? 'SystemAdmin' : canonicalUiRole(role);
  const clone = value => JSON.parse(JSON.stringify(value));
  let backendProgramSettingsId = null;
  let activeProgramId = null;
  let programDirectory = [];
  let membershipDirectory = [];
  let accessibleProgramIds = [];

  let currentUser = null;
  let userDirectory = [];
  let keepaliveStatus = null;
  const SESSION_KEY = 'acadeloop_session_v100';
  const USERS_KEY = 'acadeloop_authorized_users_v100';
  const memoryStorage = new Map();
  function storageGet(key){try{const value=localStorage.getItem(key);if(value!==null)return value}catch{}return memoryStorage.has(key)?memoryStorage.get(key):null}
  function storageSet(key,value){const text=String(value);memoryStorage.set(key,text);try{localStorage.setItem(key,text)}catch{}}
  function storageRemove(key){memoryStorage.delete(key);try{localStorage.removeItem(key)}catch{}}

  function currentUserName(){
    if(!currentUser) return 'User';
    return [currentUser.firstName,currentUser.lastName].filter(Boolean).join(' ').trim() || currentUser.email || 'User';
  }
  function currentUserInitials(){
    const n=currentUserName().split(/\s+/).filter(Boolean);
    return (n.length>1?(n[0][0]+n[n.length-1][0]):(n[0]||'Q').slice(0,2)).toUpperCase();
  }
  function authToken(){return storageGet(SESSION_KEY)||''}
  function setAuthToken(v){if(v)storageSet(SESSION_KEY,v);else storageRemove(SESSION_KEY)}
  function defaultTestUsers(){
    const department=state?.program?.department||seed.program.department;
    return [
      // Preset identities are used only with the isolated test backend.
      {id:'test-hod',username:'TestHOD',firstName:'Test',lastName:'HOD',department,role:'Head of Department',email:'testhod@acadeloop.test',active:true,createdAt:nowDate(),preset:true},
      {id:'test-i',username:'TestI',firstName:'Test',lastName:'Instructor',department,role:'Instructor',email:'testi@acadeloop.test',active:true,createdAt:nowDate(),preset:true},
      {id:'test-q',username:'TestQ',firstName:'Test',lastName:'Quality',department,role:'Coordinator',email:'testq@acadeloop.test',active:true,createdAt:nowDate(),preset:true},
      {id:'test-i2',username:'TestI2',firstName:'Test',lastName:'Instructor 2',department,role:'Instructor',email:'testi2@acadeloop.test',active:true,createdAt:nowDate(),preset:true},
      {id:'test-apu',username:'TestAPU',firstName:'Test',lastName:'APU',department,role:'APU',email:'apu@acadeloop.test',active:true,createdAt:nowDate(),preset:true,testOnly:true},
      {id:'test-vdaa',username:'TestVDAA',firstName:'Test',lastName:'VDAA',department,role:'VDAA',email:'vdaa@acadeloop.test',active:true,createdAt:nowDate(),preset:true,testOnly:true}
    ];
  }
  function loadLocalUsers(){
    let users=[];
    try{const raw=storageGet(USERS_KEY);if(raw)users=JSON.parse(raw)}catch(e){}
    if(!Array.isArray(users))users=[];
    for(const preset of defaultTestUsers()){
      const i=users.findIndex(u=>String(u.username||'').toLowerCase()===preset.username.toLowerCase()||String(u.email||'').toLowerCase()===preset.email.toLowerCase());
      if(i<0)users.push(preset); else users[i]={...users[i],...preset,active:true};
    }
    users.sort((a,b)=>(a.preset===b.preset?String(a.username||a.email).localeCompare(String(b.username||b.email)):(a.preset?-1:1)));
    storageSet(USERS_KEY,JSON.stringify(users))
    return users;
  }
  function saveLocalUsers(users){
    storageSet(USERS_KEY,JSON.stringify(users))
  }
  function localUserByLogin(login){
    const key=String(login||'').trim().toLowerCase();
    return loadLocalUsers().find(u=>canonicalUiRole(u.role)!=='System Administrator'&&u.active!==false&&(String(u.username||'').toLowerCase()===key||String(u.email||'').toLowerCase()===key))||null;
  }

  let state = normalizeState(loadState());
  let currentView = 'dashboard';
  let currentReportId = null;
  let currentPortfolioId = null;
  // Course Portfolio uploads are intentionally session-only. File objects are kept in memory and are never written to localStorage.
  const portfolioUploadFiles = new Map();
  const portfolioActiveTerms = new Map();
  let activePlo = null;
  let ploYear = state.program.academicYear;
  let ploTerm = 'Annual';

  function loadState(){
    if(backendEnabled) return clone(seed);
    try{const raw=storageGet(STORAGE_KEY); if(raw) return JSON.parse(raw);}catch(e){}
    return clone(seed);
  }
  function saveState(){
    // Production data is persisted explicitly to Supabase. Browser storage is test-only.
    if(!backendEnabled) storageSet(STORAGE_KEY,JSON.stringify(state));
    syncChrome();
  }

  function reportDbRow(r){
    ensureSectionModel(r);
    if(r.sectionMode==='all') enforceCombinedIntegrity(r);
    syncFlatFromEffective(r);
    const data=clone(r);
    // The database stores report DATA only. Generated DOCX/ZIP files and temporary portfolio files are never persisted.
    return {
      id:r.id, legacy_id:r.legacyId||null, program_id:activeProgramId, course_code:r.courseCode, course_title:r.courseName,
      academic_year:r.academicYear, semester:r.semester, section_mode:r.sectionMode,
      instructor_id:r.instructorId||currentUser?.id, status:r.status, data
    };
  }
  function reportFromDb(row){
    const r={...(row.data||{})};
    r.id=row.id;r.legacyId=row.legacy_id||r.legacyId||'';r.programId=row.program_id||r.programId||null;r.courseCode=row.course_code;r.courseName=row.course_title;
    r.academicYear=row.academic_year;r.semester=row.semester;r.sectionMode=row.section_mode;r.instructorId=row.instructor_id;
    r.status=row.status;r.submittedAt=row.submitted_at?String(row.submitted_at).slice(0,10):(r.submittedAt||'');
    r.approvedAt=row.approved_at?String(row.approved_at).slice(0,10):(r.approvedAt||'');
    r.revisionNote=row.return_reason||'';
    ensureSectionModel(r);if(r.sectionMode==='all')enforceCombinedIntegrity(r);syncFlatFromEffective(r);
    return r;
  }
  async function persistCourseReport(r){
    if(!backendEnabled)return r;
    const rows=await Backend.insert('course_reports',reportDbRow(r),{onConflict:'id',upsert:true});
    if(rows?.[0])Object.assign(r,reportFromDb(rows[0]));
    return r;
  }
  async function persistProgramSetup(){
    if(!backendEnabled)return;
    const row={
      id:backendProgramSettingsId||uid(), program_id:activeProgramId, program_name:state.program.name||'Academic Program', department:state.program.department||'',
      academic_year:state.program.academicYear||'', data:{...clone(state.program),academicYears:clone(state.academicYears)}, is_active:true
    };
    const rows=await Backend.insert('program_settings',row,{onConflict:'id',upsert:true});
    if(rows?.[0])backendProgramSettingsId=rows[0].id;
  }
  async function persistPlos(){
    if(!backendEnabled)return;
    for(const p of state.plos){await Backend.insert('plos',{program_id:activeProgramId,code:p.code,name:p.name,target:Number(p.target),active:true,data:{}},{onConflict:'program_id,code',upsert:true});}
  }
  function normalizeState(s){
    s = s && typeof s === 'object' ? s : JSON.parse(JSON.stringify(seed));
    s.program = s.program || JSON.parse(JSON.stringify(seed.program));
    s.program.academicYear = String(s.program.academicYear||'').trim();
    s.academicYears = Array.isArray(s.academicYears) ? [...new Set(s.academicYears.map(x=>String(x||'').trim()).filter(Boolean))] : [];
    if(s.program.academicYear&&!s.academicYears.includes(s.program.academicYear)) s.academicYears.unshift(s.program.academicYear);
    s.reports = Array.isArray(s.reports) ? s.reports : [];
    s.plos = Array.isArray(s.plos) ? s.plos : [];
    for(const key of ['kpiDefinitions','kpiYears','kpiPriorities','kpiActions'])s[key]=Array.isArray(s[key])?s[key]:[];
    s.operational = Array.isArray(s.operational) ? s.operational : [];
    s.automations = Array.isArray(s.automations) ? s.automations : [];
    s.audit = Array.isArray(s.audit) ? s.audit : [];
    s.role = canonicalUiRole(s.role) || canonicalUiRole(seed?.role) || 'Instructor';
    s.reports.forEach(r=>{
      r.academicYear = r.academicYear || s.program.academicYear;
      if(r.semester==='First') r.semester='S1';
      if(r.semester==='Second') r.semester='S2';
      if(!TERMS.includes(r.semester)) r.semester='S1';
      if(r.status==='In Review') r.status='Awaiting Quality Approval';
      if(r.status==='Needs Revision') r.status='Returned for Revision';
      r.revisionNote = r.revisionNote || '';
      r.sectionMode = ['male','female','combined','all'].includes(r.sectionMode) ? r.sectionMode : 'combined';
      // Combined is never manually maintained when the instructor enters Male + Female.
      // It is a deterministic derived record, so stale/manual Combined values cannot survive reload.
      r.autoCombine = r.sectionMode === 'all' ? true : r.autoCombine !== false;
      r.clos = Array.isArray(r.clos) ? r.clos : [];
      r.improvements = Array.isArray(r.improvements) ? r.improvements : [];
      ensureSectionModel(r);
    });
    return s;
  }

  const UNKNOWN_ROLE_CONFIG = {views:['dashboard'],label:'Account access',avatar:'?',dashboard:'Account access unavailable',description:'This account does not have a supported Itqan role.'};
  function roleConfig(){return ROLE_CONFIG[canonicalUiRole(state.role)] || UNKNOWN_ROLE_CONFIG}
  function roleCanView(view){return roleConfig().views.includes(view)}
  function canCreateReport(){return state.role==='Instructor'}
  function isInstructorOwner(r){
    if(state.role!=='Instructor') return false;
    if(r.instructorEmail&&currentUser?.email) return r.instructorEmail.toLowerCase()===currentUser.email.toLowerCase();
    return r.instructor===currentUserName();
  }
  function canEditReport(r){return state.role==='Instructor' && isInstructorOwner(r) && (r.status==='Draft'||r.status==='Returned for Revision')}
  function reportsForRole(){
    const all=state.reports||[];
    if(state.role==='Instructor') return all.filter(isInstructorOwner);
    if(state.role==='Head of Department') return all.filter(r=>r.status==='Approved');
    if(state.role==='System Administrator') return [];
    return all;
  }
  function approvedReports(year=null,term='Annual'){
    return state.reports.filter(r=>r.status==='Approved' && (!year || r.academicYear===year) && (term==='Annual'||!term||r.semester===term));
  }

  function sectionPill(k){return `<span class="section-scope-pill ${esc(k||'combined')}">${esc(sectionLabel(k||'combined'))}</span>`}
  function periodLabel(r){return `${r.semester} ${r.academicYear}`}
  function periodPill(r){return `<span class="period-pill"><b>${esc(r.semester)}</b><span>${esc(r.academicYear)}</span></span>`}

  function formatPct(v){if(v===''||v==null)return '—';const n=Number(v);return Number.isFinite(n)?`${Math.round(n*10)/10}%`:'—'}
  function statusClass(s){return `status-${String(s).replace(/[^A-Za-z0-9_-]/g,'')}`}
  function statusPill(s){return `<span class="status-pill ${statusClass(s)}">${esc(s)}</span>`}
  function progressHtml(n){return `<div class="progress-wrap"><div class="progress-track"><div class="progress-fill" style="width:${clamp(n)}%"></div></div><span>${clamp(n)}%</span></div>`}
  function semesterFolderName(term){return term==='S1'?'Semester 1':term==='S2'?'Semester 2':'Summer'}
  function portfolioGroupKey(r){return `${r.courseCode}|||${r.academicYear}`}
  function portfolioGroupsForRole(){
    const groups=new Map();
    reportsForRole().forEach(r=>{
      const key=portfolioGroupKey(r);
      if(!groups.has(key))groups.set(key,{key,courseCode:r.courseCode,courseName:r.courseName,academicYear:r.academicYear,reports:[]});
      groups.get(key).reports.push(r);
    });
    return Array.from(groups.values()).sort((a,b)=>a.courseCode.localeCompare(b.courseCode)||b.academicYear.localeCompare(a.academicYear));
  }
  function portfolioPeriodReports(g,term){return g.reports.filter(r=>r.semester===term)}
  function portfolioApprovedReports(g,term=null){return g.reports.filter(r=>r.status==='Approved'&&(!term||r.semester===term))}
  function portfolioOfficialPercent(g){return g.reports.length?Math.round(portfolioApprovedReports(g).length/g.reports.length*100):0}
  function portfolioStatusText(g){
    const a=portfolioApprovedReports(g).length,t=g.reports.length;
    if(!t)return 'No reports';
    if(a===t)return 'Official';
    if(a>0)return 'Partially approved';
    return 'Waiting for approval';
  }
  function periodStatusHtml(g,term){
    const rs=portfolioPeriodReports(g,term);if(!rs.length)return '<span class="tiny">No report</span>';
    const approved=rs.filter(r=>r.status==='Approved').length;
    if(approved===rs.length)return '<span class="portfolio-ready">Approved</span>';
    if(approved>0)return '<span class="portfolio-attention">Partial</span>';
    const first=rs[0];return statusPill(first.status);
  }

  function ploRollups(year=state.program.academicYear,term='Annual'){
    return calculatePloRollups(state.reports,state.plos,year,term);
  }
  function overallPlo(year=state.program.academicYear,term='Annual'){const vals=ploRollups(year,term).map(x=>x.actual).filter(x=>x!==null);return vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:null}
  function reportingReadiness(year=state.program.academicYear,term='Annual'){
    const rs=state.reports.filter(r=>r.academicYear===year&&(term==='Annual'||r.semester===term));
    return rs.length?Math.round(rs.filter(r=>r.status==='Approved').length/rs.length*100):0;
  }
  function aprReadiness(year=state.program.academicYear){return reportingReadiness(year,'Annual')}

  function syncRoleUI(){
    const cfg=roleConfig();
    document.querySelectorAll('.nav-item[data-view]').forEach(b=>b.classList.toggle('role-hidden',!cfg.views.includes(b.dataset.view)));
    if($('roleContext')) $('roleContext').innerHTML=`<span>Workspace</span><b>${esc(cfg.label)}</b>`;
    const setupButton=document.querySelector('[data-view=setup]');if(setupButton)setupButton.childNodes[setupButton.childNodes.length-1].textContent=state.role==='System Administrator'?' Academic Programs':' Program Settings';
    const programWrap=$('workspaceProgramWrap'),programSelect=$('workspaceProgramSelect');
    if(programWrap&&programSelect){const programs=programDirectory.filter(p=>accessibleProgramIds.includes(p.id)&&p.status==='Open');programWrap.classList.toggle('hidden',state.role==='System Administrator'||programs.length<2);programSelect.innerHTML=programs.map(p=>`<option value="${esc(p.id)}" ${p.id===activeProgramId?'selected':''}>${esc(programDirectoryLabel(p))}</option>`).join('');}
    if($('avatarLabel')){$('avatarLabel').textContent=currentUserInitials();$('avatarLabel').title=currentUserName();}
    if($('currentUserName'))$('currentUserName').textContent=currentUserName();
    if($('currentUserRole'))$('currentUserRole').textContent=state.role;
    document.body.dataset.role=state.role||''; // lets the visual layer pick role-specific imagery
    if($('quickAdd')){$('quickAdd').style.display=canCreateReport()?'inline-flex':'none';$('quickAdd').textContent='+ New report';}
  }
  function syncChrome(){
    if($('sideAcademicYear'))$('sideAcademicYear').textContent=state.program.academicYear||'Not set'; if($('sideProgram'))$('sideProgram').textContent=state.program.name;
    if($('navCourseCount'))$('navCourseCount').textContent=reportsForRole().length; if($('navPortfolioCount'))$('navPortfolioCount').textContent=portfolioGroupsForRole().length;
    syncRoleUI();
  }
  function toast(msg){const t=$('toast');t.textContent=msg;t.classList.add('show');clearTimeout(toast._t);toast._t=setTimeout(()=>t.classList.remove('show'),2600)}
  function pageHead(kicker,title,desc,actions=''){return `<div class="page-head"><div><span class="eyebrow">${esc(kicker)}</span><h1>${esc(title)}</h1><p>${esc(desc)}</p></div><div class="page-actions">${actions}</div></div>`}
  // The role banner repeated the dashboard title on every page; the sidebar, top bar and page heading already carry that context.
  function roleHero(){return ''}
  function periodFilter(yearId='periodYear',termId='periodTerm',includeAnnual=true){return `<div class="period-filter"><label><span>Academic year</span><select id="${yearId}">${state.academicYears.map(y=>`<option ${y===ploYear?'selected':''}>${esc(y)}</option>`).join('')}</select></label><label><span>Period</span><select id="${termId}">${includeAnnual?'<option>Annual</option>':''}${TERMS.map(t=>`<option ${t===ploTerm?'selected':''}>${t}</option>`).join('')}</select></label></div>`}

  function render(){
    if(!roleCanView(currentView)) currentView='dashboard';
    const titles={dashboard:[roleConfig().label,roleConfig().dashboard],'course-reports':[state.role==='Instructor'?'My reporting':'Quality cycle',state.role==='Instructor'?'My Course Reports':state.role==='Coordinator'?'Course Report Approval':'Course Reports'],'course-portfolios':['Portfolio builder','Course Portfolios'],plo:['Outcome analytics','PLO Attainment'],apr:['Program reporting','Annual Program Report'],kpis:['Performance management','Key Performance Indicators'],operational:['Execution','Operational Plan'],automations:['Workflow engine','Automations'],users:['Access control','Users'],setup:['Administration','Program Setup']};
    if(currentView==='course-portfolios'&&currentPortfolioId){const g=portfolioGroupsForRole().find(x=>x.key===currentPortfolioId);if(g)titles['course-portfolios']=['Course portfolio',g.courseCode];}
    $('pageKicker').textContent=titles[currentView][0];$('pageTitle').textContent=titles[currentView][1];
    document.querySelectorAll('.nav-item[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===currentView));
    const map={dashboard:renderDashboard,'course-reports':renderCourseReports,'course-portfolios':renderCoursePortfolios,plo:renderPlo,apr:renderApr,kpis:renderKpis,operational:renderOperational,automations:renderAutomations,users:renderUsers,setup:renderSetup};
    $('content').classList.toggle('dashboard-page',currentView==='dashboard');
    $('content').innerHTML=map[currentView](); syncRoleUI(); bindViewEvents();
  }

  function dashboardQualitySection(reports,year=ploYear,term=ploTerm,supervision=false){
    const rs=(reports||[]).filter(r=>r.academicYear===year&&(term==='Annual'||r.semester===term));
    const flagged=rs.map(r=>({r,flags:reportQualityFlags(r)}));
    const inflationCount=flagged.filter(x=>x.flags.inflation.inflated).length;
    const cloCount=flagged.filter(x=>x.flags.cloGaps.length).length;
    const dist=pooledGradeDistribution(rs);
    const gradeItems=LETTER_GRADE_LABELS.map(g=>`<div class="grade-average-item"><b>${esc(g)}</b><strong>${formatPct(dist.percentages[g])}</strong><div class="mini-grade-track"><div class="mini-grade-fill" style="width:${Math.min(100,Math.max(0,dist.percentages[g]))}%"></div></div></div>`).join('');
    const rows=flagged.slice().sort((a,b)=>Number(b.flags.hasIssue)-Number(a.flags.hasIssue)||a.r.courseCode.localeCompare(b.r.courseCode)).map(({r,flags})=>{
      const inflation=flags.inflation.inflated?`<div class="signal-stack">${flags.inflation.flagged.map(x=>`<span class="signal-chip alert">${esc(x.label)} · ${esc(x.reasons.join(' / '))}</span>`).join('')}</div>`:'<span class="signal-chip ok">No inflation</span>';
      const gaps=flags.cloGaps.length?`<div class="signal-stack">${flags.cloGaps.slice(0,4).map(g=>`<span class="signal-chip bad">${esc(g.sectionLabel)} ${esc(g.code)} · ${formatPct(g.actual)} &lt; ${formatPct(g.target)}</span>`).join('')}${flags.cloGaps.length>4?`<span class="signal-chip bad">+${flags.cloGaps.length-4} more</span>`:''}</div>`:'<span class="signal-chip ok">Targets met</span>';
      return `<tr data-dashboard-course data-inflation="${flags.inflation.inflated?'1':'0'}"><td><strong>${esc(r.courseCode)}</strong><div class="tiny">${esc(r.courseName)}</div>${supervision?`<div class="tiny">${esc(supervisorData.programs.find(p=>p.id===r.programId)?.name||'')}</div>`:''}</td><td>${periodPill(r)}</td><td>${inflation}</td><td>${gaps}</td><td>${statusPill(r.status)}</td><td><button class="btn btn-ghost" ${supervision?`data-supervisor-report="${esc(r.id)}" data-program="${esc(r.programId)}"`:`data-edit-report="${r.id}"`}>View</button></td></tr>`;
    }).join('');
    return `<div class="section"><div class="section-title"><div><h2>Academic performance signals</h2><p>Grade inflation is detected when A+ is at least 20% of letter-graded students, or A and above is more than 60%. CLO alerts appear whenever an actual result is below its target.</p></div></div>
      <div class="quality-signal-grid"><div class="quality-signal-card"><div class="label">Courses with grade inflation</div><strong>${inflationCount}</strong><small>${rs.length} course report${rs.length===1?'':'s'} included</small></div><div class="quality-signal-card"><div class="label">Courses with CLO below target</div><strong>${cloCount}</strong><small>Any section/CLO actual below its target is flagged</small></div></div>
      <div class="grade-average-card"><div class="grade-average-head"><div><h3>Average grade distribution across courses</h3><p>Enrollment-weighted across letter grades A+ through F for ${esc(term==='Annual'?year:`${term} ${year}`)}. Status categories such as Withdrawn or Incomplete are excluded.</p></div><span class="tag">${dist.courseCount} courses · ${dist.denominator} graded students</span></div><div class="grade-average-grid">${gradeItems}</div></div>
      <div class="quality-monitor-tools"><div><strong style="font-size:11px">Course quality monitor</strong><div class="tiny">Use the checkbox to isolate courses with grade inflation.</div></div><label><input type="checkbox" id="inflationOnlyCheck" ${dashboardInflationOnly?'checked':''}> Show courses only with grade inflation</label></div>
      <div class="table-card"><table class="data-table"><thead><tr><th>Course</th><th>Period</th><th>Grade inflation</th><th>CLO below target</th><th>Status</th><th></th></tr></thead><tbody>${rows||'<tr><td colspan="6" class="empty">No course reports are available for this academic year.</td></tr>'}</tbody></table></div>
    </div>`;
  }

  function dashboardHead(kicker,title,description,actions=''){
    const admin=state.role==='System Administrator';
    return `<header class="dashboard-hero"><div class="dashboard-context"><span class="dashboard-role">${esc(state.role)}</span><span>${esc(admin?'Academic quality administration':state.program.department)}</span></div><div class="dashboard-hero-main"><div><span class="eyebrow">${esc(kicker)}</span><h1>${esc(title)}</h1><p>${esc(description)}</p></div><div class="page-actions">${actions}</div></div>${admin?'':`<div class="dashboard-program"><span>${esc(state.program.name)}</span><span>Academic year <strong>${esc(ploYear||state.program.academicYear||'Not set')}</strong></span></div>`}</header>`;
  }
  function dashboardKpis(yearLabel=ploYear){
    if(!kpiInDepartment())return '';
    const year=Core.kpiYearStart(yearLabel),items=state.kpiDefinitions,annual=state.kpiYears.filter(r=>Number(r.year_start)===year);
    const recorded=items.filter(k=>annual.some(r=>r.kpi_id===k.id&&r.actual!=null)).length;
    const priorities=state.kpiPriorities.filter(p=>Number(p.year_start)===year);
    const pending=priorities.filter(p=>{const a=state.kpiActions.find(a=>a.priority_id===p.id);return !a||!a.actions?.trim()||!a.responsible?.trim()||!a.start_date||!a.end_date||a.target==null;}).length;
    const rows=items.slice().sort((a,b)=>a.code.localeCompare(b.code)).slice(0,4).map(k=>{
      const r=annual.find(r=>r.kpi_id===k.id)||{},points=Core.kpiTrend(state.kpiYears,k.id,year),max=Math.max(1,...points.map(p=>p.actual??0));
      return `<button type="button" class="dashboard-kpi-row" data-dashboard-kpi="${esc(k.id)}"><span class="dashboard-kpi-title"><span class="eyebrow">${esc(k.code)}</span><strong>${esc(k.name)}</strong><small>${esc(k.owner_category)}${k.owner_user_id?'':' · User not linked'}</small></span><span class="dashboard-kpi-number"><small>Actual</small><strong>${kpiValue(r.actual,k)}</strong><small>Target ${kpiValue(r.target,k)}</small></span><span class="dashboard-kpi-spark" role="img" aria-label="${esc(points.map(p=>`${Core.kpiYearLabel(p.year,yearLabel)}: ${p.actual==null?'No data':p.actual+' '+kpiUnit(k)}`).join('; '))}">${points.map(p=>`<span title="${esc(Core.kpiYearLabel(p.year,yearLabel))}: ${p.actual??'No data'}" style="height:${p.actual==null?0:Math.max(p.actual===0?2:0,p.actual/max*100)}%" class="${p.year===year?'current':''}"></span>`).join('')}</span><span class="dashboard-kpi-arrow" aria-hidden="true">↗</span></button>`;
    }).join('');
    return `<section class="dashboard-kpis" aria-labelledby="dashboardKpiTitle"><div class="section-title"><div><span class="eyebrow">Department performance · Annual ${esc(yearLabel)}</span><h2 id="dashboardKpiTitle">Key Performance Indicators</h2><p>Benchmarks, ownership and improvement actions in one place.</p></div><button class="btn btn-ghost" data-go="kpis">View all KPIs →</button></div><div class="dashboard-kpi-layout"><div class="dashboard-kpi-summary"><div class="dashboard-kpi-total"><span>Department KPIs</span><strong>${items.length}</strong><small>${recorded} with an actual result this year</small></div><dl><div><dt>Awaiting actual results</dt><dd>${items.length-recorded}</dd></div><div><dt>Action plans to complete</dt><dd>${pending}</dd></div><div><dt>Owners awaiting user links</dt><dd>${items.filter(k=>!k.owner_user_id).length}</dd></div></dl></div><div class="dashboard-kpi-list">${rows||`<div class="dashboard-kpi-empty"><span class="dashboard-empty-icon" aria-hidden="true">▥</span><h3>Your department’s performance starts here</h3><p>${canManageKpi()?'Add a KPI, choose its measurement and assign an owner category.':'Your HOD can add department KPIs and assign owner categories.'}</p>${canManageKpi()?'<button class="btn btn-primary" id="dashboardNewKpi">＋ Create first KPI</button>':''}</div>`}${rows?'<div class="dashboard-kpi-foot">Actual trends: selected year and previous two years. Select a KPI to open its record.</div>':''}</div></div></section>`;
  }

  async function loadSupervisorData(){
    supervisorData=null;supervisorError='';
    if(!isSupervisorRole(currentUser?.role))return;
    if(!backendEnabled){
      const id='sample-program';
      supervisorData={programs:[{...state.program,id,code:'Sample',status:'Open'}],reports:state.reports.map(r=>({...r,programId:id})),plos:state.plos.map(p=>({...p,programId:id})),years:state.academicYears};
      return;
    }
    // Use the signed-in reader and existing RLS. Paginate so institution totals are not capped.
    const readAll=async(table,query)=>{
      const rows=[];let offset=0;
      while(true){const page=await Backend.select(table,`${query}&order=id.asc&limit=500&offset=${offset}`);rows.push(...(page||[]));if(!page?.length)break;offset+=page.length;}
      return rows;
    };
    try{
      const [reports,plos,settings]=await Promise.all([
        readAll('course_reports','select=*'),readAll('plos','select=*&active=eq.true'),readAll('program_settings','select=*&is_active=eq.true')
      ]);
      if(!isSupervisorRole(currentUser?.role))return;
      supervisorData={programs:programDirectory.filter(p=>accessibleProgramIds.includes(p.id)),reports:reports.map(reportFromDb),plos:plos.map(p=>({...p,programId:p.program_id,target:Number(p.target)})),years:[...new Set(settings.flatMap(p=>[p.academic_year,...(p.data?.academicYears||[])]).concat(reports.map(r=>r.academic_year)).filter(Boolean))].sort().reverse()};
    }catch(e){supervisorError='Could not load institution data. Retry to avoid viewing incomplete totals.';}
  }
  function renderSupervisorDashboard(){
    const f=supervisorFilters;
    const head=`<header class="dashboard-hero"><span class="eyebrow">Institution-wide supervision</span><h1>${esc(state.role)} Supervision Dashboard</h1><p>Choose departments, programs and reporting periods. All supervision is read-only.</p></header>`;
    if(!supervisorData)return head+`<div class="card"><p role="alert">${esc(supervisorError||'Loading institution data…')}</p><button class="btn btn-primary" id="supervisorRefresh">Retry</button></div>`;
    const data=supervisorData;
    const options=(values,value,all)=>`${all?`<option value="">${esc(all)}</option>`:''}${values.map(x=>{const v=typeof x==='string'?x:x.id;return `<option value="${esc(v)}" ${v===value?'selected':''}>${esc(typeof x==='string'?x:programDirectoryLabel(x))}</option>`;}).join('')}`;
    const availablePrograms=data.programs.filter(p=>!f.department||p.department===f.department);
    const years=[...new Set([...data.years,...data.reports.map(r=>r.academicYear)].filter(Boolean))].sort().reverse();
    if(!years.includes(f.year))f.year=years.includes(ploYear)?ploYear:years[0]||'';
    const scope=Core.supervisorScope(data,f), rs=scope.reports;
    const approved=rs.filter(r=>r.status==='Approved'),waiting=rs.filter(r=>r.status==='Awaiting Quality Approval'),returned=rs.filter(r=>r.status==='Returned for Revision');
    const show=part=>f.view==='all'||f.view===part;
    const summary=`<div class="grid grid-4"><div class="card metric"><div class="label">Reports</div><div class="value">${rs.length}</div><div class="sub">${scope.programs.length} academic programs</div></div><div class="card metric"><div class="label">Quality approved</div><div class="value">${approved.length}</div><div class="sub">Official program data</div></div><div class="card metric"><div class="label">In workflow</div><div class="value">${waiting.length+returned.length}</div><div class="sub">${waiting.length} awaiting · ${returned.length} returned</div></div><div class="card metric"><div class="label">PLOs meeting target</div><div class="value">${scope.rollups.filter(x=>x.met).length}/${scope.rollups.length}</div><div class="sub">Approved evidence; independent of status filter</div></div></div>`;
    const programRows=scope.programs.map(p=>{const reports=rs.filter(r=>r.programId===p.id),roll=scope.rollups.filter(r=>r.programId===p.id);return `<tr><td>${esc(p.department)}</td><td>${esc(programDirectoryLabel(p))}</td><td>${reports.length}</td><td>${reports.filter(r=>r.status==='Approved').length}</td><td>${roll.filter(x=>x.met).length}/${roll.length}</td></tr>`;}).join('');
    const reportRows=rs.map(r=>{const p=scope.programs.find(p=>p.id===r.programId);return `<tr><td>${esc(p.department)}<div class="tiny">${esc(programDirectoryLabel(p))}</div></td><td><strong>${esc(r.courseCode)}</strong><div class="tiny">${esc(r.courseName)}</div></td><td>${periodPill(r)}</td><td>${statusPill(r.status)}</td><td><button class="btn btn-ghost" data-supervisor-report="${esc(r.id)}" data-program="${esc(r.programId)}">View</button></td></tr>`;}).join('');
    const kpis=f.program&&(f.program===activeProgramId||!backendEnabled)?(dashboardKpis(f.year)||'<div class="card"><p>KPI access remains restricted to your department.</p></div>'):`<div class="card"><h2>Key Performance Indicators</h2><p>Select a program to view its permitted department KPIs. KPI access remains restricted to your department.</p>${f.program?`<button class="btn btn-ghost" data-supervisor-workspace="${esc(f.program)}">Open selected program KPIs</button>`:''}</div>`;
    return head+`<div class="period-filter supervisor-filters" aria-label="Dashboard filters">
      <label><span>Department</span><select id="supervisorDepartment">${options(uniqueDepartments(data.programs),f.department,'All departments')}</select></label>
      <label><span>Academic program</span><select id="supervisorProgram">${options(availablePrograms,f.program,'All programs')}</select></label>
      <label><span>Academic year</span><select id="supervisorYear">${options(years,f.year,years.length?'':'No academic years')}</select></label>
      <label><span>Semester</span><select id="supervisorTerm">${options(['Annual',...TERMS],f.term)}</select></label>
      <label><span>Report status</span><select id="supervisorStatus">${options(['Draft','Awaiting Quality Approval','Returned for Revision','Approved'],f.status,'All statuses')}</select></label>
      <label><span>Show sections</span><select id="supervisorView">${[['all','All sections'],['overview','Program overview'],['performance','Academic performance signals'],['reports','Course reports'],['kpis','Key Performance Indicators']].map(([v,t])=>`<option value="${v}" ${v===f.view?'selected':''}>${esc(t)}</option>`).join('')}</select></label>
      <button class="btn btn-ghost" id="supervisorReset">Reset filters</button><button class="btn btn-ghost" id="supervisorRefresh">Refresh data</button></div>
      <p class="tiny" role="status">${esc(f.department||'All departments')} · ${esc(f.year||'No academic years')} · ${esc(f.term)} · ${rs.length} reports${backendEnabled?'':' · Sample workspace only'}</p>
      ${summary}
      ${show('overview')?`<section class="section"><h2>Program overview</h2><div class="table-card"><table class="data-table"><thead><tr><th>Department</th><th>Academic program</th><th>Reports</th><th>Quality approved</th><th>PLOs meeting target</th></tr></thead><tbody>${programRows||'<tr><td colspan="5" class="empty">No programs match these filters.</td></tr>'}</tbody></table></div></section>`:''}
      ${show('performance')?dashboardQualitySection(rs,f.year,f.term,true):''}
      ${show('reports')?`<section class="section"><h2>Course reports</h2><div class="table-card"><table class="data-table"><thead><tr><th>Department / program</th><th>Course</th><th>Period</th><th>Status</th><th></th></tr></thead><tbody>${reportRows||'<tr><td colspan="5" class="empty">No reports match these filters.</td></tr>'}</tbody></table></div></section>`:''}
      ${show('kpis')?kpis:''}`;
  }

  function renderDashboard(){
    if(state.role==='System Administrator') return renderSystemAdminDashboard();
    if(isSupervisorRole(state.role)) return renderSupervisorDashboard();
    const rs=reportsForRole();
    if(state.role==='Instructor'){
      const open=rs.filter(r=>r.status==='Draft'||r.status==='Returned for Revision').length;
      return dashboardHead('Instructor quality cycle','My Course Quality','Each Course Report is tied to an academic year and semester. Choose Male, Female, Combined, or All; All lets you enter Male and Female together.',`<button class="btn btn-primary" data-new="report">＋ New course report</button>`)+`
      <div class="grid grid-4"><div class="card metric"><div class="label">My reports</div><div class="value">${rs.length}</div><div class="sub">${open} open for editing</div></div><div class="card metric"><div class="label">Awaiting quality approval</div><div class="value">${rs.filter(r=>r.status==='Awaiting Quality Approval').length}</div><div class="sub">Locked after submission</div></div><div class="card metric"><div class="label">Approved</div><div class="value">${rs.filter(r=>r.status==='Approved').length}</div><div class="sub">Released to official program calculations</div></div><div class="card metric"><div class="label">Generated portfolios</div><div class="value">${rs.filter(r=>r.status==='Approved').length}</div><div class="sub">Generated on demand; no portfolio files stored</div></div></div>
      ${dashboardKpis()}
      ${reportBoard(rs,'My reporting board')}`;
    }
    if(state.role==='Coordinator'){
      const yr=ploYear,term=ploTerm;
      const periodReports=state.reports.filter(r=>r.academicYear===yr&&(term==='Annual'||r.semester===term));
      const waiting=periodReports.filter(r=>r.status==='Awaiting Quality Approval');
      const returned=periodReports.filter(r=>r.status==='Returned for Revision').length;
      return dashboardHead('Mandatory approval gate','Quality Approval Center','Submitted reports appear here exactly as the instructor entered them. Only your approval releases CLO data to PLO calculations and the HOD dashboard.',`<button class="btn btn-primary" data-go="course-reports">Open approval queue</button>`)+periodFilter()+`
      <div class="grid grid-4"><div class="card metric"><div class="label">Awaiting approval</div><div class="value">${waiting.length}</div><div class="sub">Official gate before PLO/APR/HOD</div></div><div class="card metric"><div class="label">Returned</div><div class="value">${returned}</div><div class="sub">Instructor revision required</div></div><div class="card metric"><div class="label">Approved</div><div class="value">${approvedReports(yr,term).length}</div><div class="sub">${esc(term==='Annual'?yr:`${term} ${yr}`)}</div></div><div class="card metric"><div class="label">Reporting readiness</div><div class="value">${reportingReadiness(yr,term)}%</div><div class="sub">Approved reporting coverage</div></div></div>
      ${dashboardKpis()}
      <div class="section"><div class="section-title"><div><h2>Approval queue</h2><p>Semester and academic year remain visible throughout review.</p></div></div><div class="table-card"><table class="data-table"><thead><tr><th>Course</th><th>Reporting period</th><th>Instructor</th><th>Scope</th><th>Submitted</th><th>Status</th><th></th></tr></thead><tbody>${waiting.length?waiting.map(r=>`<tr><td><strong>${esc(r.courseCode)}</strong><div class="tiny">${esc(r.courseName)}</div></td><td>${periodPill(r)}</td><td>${esc(r.instructor)}</td><td>${sectionPill(r.sectionMode)}</td><td>${esc(r.submittedAt||r.reportDate||'—')}</td><td>${statusPill(r.status)}</td><td><button class="btn btn-primary" data-edit-report="${r.id}">Review</button></td></tr>`).join(''):'<tr><td colspan="7" class="empty">No reports are waiting for approval in this period.</td></tr>'}</tbody></table></div></div>
      ${dashboardQualitySection(state.reports.filter(r=>r.status!=='Draft'),yr,term)}`;
    }
    if(state.role==='Head of Department'){
      const yr=ploYear,term=ploTerm,approved=approvedReports(yr,term),roll=ploRollups(yr,term),met=roll.filter(x=>x.met).length;
      return dashboardHead('Official approved data only','Department Quality Overview','Reports appear here only after coordinator approval. Drafts, returned reports, and reports awaiting approval are excluded.',`<button class="btn btn-ghost" data-go="users">Manage users</button><button class="btn btn-ghost" data-go="plo">PLO attainment</button><button class="btn btn-primary" data-go="apr">Open APR</button>`)+periodFilter()+`
      <div class="grid grid-4"><div class="card metric"><div class="label">Approved reports</div><div class="value">${approved.length}</div><div class="sub">${esc(term==='Annual'?yr:`${term} ${yr}`)} official reports</div></div><div class="card metric"><div class="label">PLOs meeting target</div><div class="value">${met}/${roll.length}</div><div class="sub">Weighted approved CLO evidence</div></div><div class="card metric"><div class="label">Reporting readiness</div><div class="value">${reportingReadiness(yr,term)}%</div><div class="sub">Based on approved reports</div></div><div class="card metric"><div class="label">Authorized users</div><div class="value">${userDirectory.length||'—'}</div><div class="sub">HOD-controlled access</div></div></div>
      ${dashboardKpis()}
      ${dashboardQualitySection(approved,yr,term)}
      ${reportBoard(approved,'Recently approved course reports',true)}`;
    }
    const yr=state.program.academicYear,roll=ploRollups(yr,'Annual'),approved=approvedReports(yr,'Annual');
    return dashboardHead('Program quality','Quality Overview','Monitor reporting coverage and approved outcomes.',`<button class="btn btn-ghost" data-go="course-reports">Course reports</button><button class="btn btn-primary" data-go="apr">Annual Program Report</button>`)+`
    <div class="grid grid-4"><div class="card metric"><div class="label">All reports</div><div class="value">${state.reports.filter(r=>r.academicYear===yr).length}</div><div class="sub">${esc(yr)}</div></div><div class="card metric"><div class="label">Quality approved</div><div class="value">${approved.length}</div><div class="sub">Official program data</div></div><div class="card metric"><div class="label">Awaiting approval</div><div class="value">${state.reports.filter(r=>r.academicYear===yr&&r.status==='Awaiting Quality Approval').length}</div><div class="sub">Coordinator queue</div></div><div class="card metric"><div class="label">PLOs meeting target</div><div class="value">${roll.filter(x=>x.met).length}/${roll.length}</div><div class="sub">Annual approved roll-up</div></div></div>
    ${reportBoard(state.reports.filter(r=>r.academicYear===yr),'Reporting coverage')}`;
  }

  function reportBoard(rs,title,approvedOnly=false){
    return `<div class="section"><div class="section-title"><div><h2>${esc(title)}</h2><p>${approvedOnly?'Quality-approved reports only.':'Course, reporting period, section scope, and approval status are separated.'}</p></div></div><div class="table-card"><table class="data-table"><thead><tr><th>Course</th><th>Period</th><th>Scope</th><th>Status</th><th>CLO</th><th></th></tr></thead><tbody>${rs.length?rs.map(r=>`<tr><td><div class="course-cell"><div class="course-code">${esc(r.courseCode.slice(-3))}</div><div class="course-meta"><strong>${esc(r.courseCode)}</strong><span>${esc(r.courseName)}</span></div></div></td><td>${periodPill(r)}</td><td>${sectionPill(r.sectionMode)}</td><td>${statusPill(r.status)}</td><td><strong>${reportAverageAttainment(r)!==null?formatPct(reportAverageAttainment(r)):'—'}</strong></td><td><button class="btn btn-ghost" data-edit-report="${r.id}">${state.role==='Coordinator'&&r.status==='Awaiting Quality Approval'?'Review':'View'}</button></td></tr>`).join(''):'<tr><td colspan="6" class="empty">No reports in this workspace.</td></tr>'}</tbody></table></div></div>`;
  }

  function renderCourseReports(){
    const rs=reportsForRole();
    const title=state.role==='Instructor'?'My Course Reports':state.role==='Coordinator'?'Course Report Approval':'Course Reports';
    const desc=state.role==='Instructor'?'Create one report per Course + Academic Year + Semester. Submit to the Coordinator when complete.':state.role==='Coordinator'?'Review the exact instructor-entered report. Approve or return it; do not edit instructor data.':state.role==='Head of Department'?'Only Coordinator-approved reports are visible here.':'Monitor all reports and their Quality approval status.';
    return roleHero()+pageHead('Reporting cycle',title,desc,`${canCreateReport()?'<button class="btn btn-primary" data-new="report">＋ New report</button>':''}`)+`
      <div class="table-card"><div class="board-tools"><div class="left"><input class="search" id="reportSearch" placeholder="Search course or instructor…"><select class="filter-select" id="yearFilter"><option value="">All academic years</option>${state.academicYears.map(y=>`<option>${esc(y)}</option>`).join('')}</select><select class="filter-select" id="semesterFilter"><option value="">All semesters</option>${TERMS.map(t=>`<option>${t}</option>`).join('')}</select><select class="filter-select" id="statusFilter"><option value="">All statuses</option><option>Draft</option><option>Awaiting Quality Approval</option><option>Returned for Revision</option><option>Approved</option></select></div><div class="right"><span class="tiny">${rs.length} report${rs.length===1?'':'s'}</span></div></div>
      <table class="data-table" id="reportsTable"><thead><tr><th>Course</th><th>Reporting period</th><th>Instructor</th><th>Scope</th><th>Status</th><th>Completion</th><th>Official CLO</th><th></th></tr></thead><tbody>${rs.length?rs.map(r=>reportRow(r)).join(''):'<tr><td colspan="8" class="empty">No course reports in this workspace.</td></tr>'}</tbody></table></div>`;
  }
  function reportRow(r){return `<tr data-report-row data-search="${esc((r.courseCode+' '+r.courseName+' '+r.instructor).toLowerCase())}" data-year="${esc(r.academicYear)}" data-semester="${esc(r.semester)}" data-status="${esc(r.status)}"><td><div class="course-cell"><div class="course-code">${esc(r.courseCode.slice(-3))}</div><div class="course-meta"><strong>${esc(r.courseCode)}</strong><span>${esc(r.courseName)}</span></div></div></td><td>${periodPill(r)}</td><td>${esc(r.instructor)}</td><td>${sectionPill(r.sectionMode)}</td><td>${statusPill(r.status)}</td><td>${progressHtml(reportCompleteness(r))}</td><td><strong>${r.status==='Approved'&&reportAverageAttainment(r)!==null?formatPct(reportAverageAttainment(r)):'—'}</strong></td><td><button class="btn ${state.role==='Coordinator'&&r.status==='Awaiting Quality Approval'?'btn-primary':'btn-ghost'}" data-edit-report="${r.id}">${state.role==='Coordinator'&&r.status==='Awaiting Quality Approval'?'Review':'Open'}</button></td></tr>`}

  function portfolioUploadStore(g){
    if(!portfolioUploadFiles.has(g.key)) portfolioUploadFiles.set(g.key,new Map());
    return portfolioUploadFiles.get(g.key);
  }
  function portfolioFilesAt(g,path){return portfolioUploadStore(g).get(path)||[]}
  function portfolioSelectedCount(g,prefix=''){
    let n=0; for(const [path,files] of portfolioUploadStore(g).entries()) if(!prefix||path.startsWith(prefix)) n+=files.length; return n;
  }
  function addPortfolioFiles(g,path,newFiles){
    const store=portfolioUploadStore(g),current=store.get(path)||[],merged=[...current];
    for(const f of newFiles){const key=`${f.name}|${f.size}|${f.lastModified}`;if(!merged.some(x=>`${x.name}|${x.size}|${x.lastModified}`===key))merged.push(f)}
    store.set(path,merged);
  }
  function clearPortfolioFiles(g,path){portfolioUploadStore(g).delete(path)}
  function portfolioFileSummary(files){
    if(!files.length)return '<span class="portfolio-upload-empty">No files selected</span>';
    const names=files.slice(0,2).map(f=>esc(f.name)).join(', '),more=files.length>2?` +${files.length-2} more`:'';
    return `<span class="portfolio-upload-selected"><b>${files.length}</b> file${files.length===1?'':'s'} · ${names}${more}</span>`;
  }
  function portfolioUploadButton(g,path,label='Choose files'){
    const files=portfolioFilesAt(g,path);
    return `<div class="portfolio-upload-control"><label class="portfolio-file-button">${files.length?'Add files':label}<input type="file" multiple data-portfolio-upload="${esc(path)}"></label>${files.length?`<button class="portfolio-clear-button" type="button" data-portfolio-clear="${esc(path)}" title="Remove selected files">Clear</button>`:''}<div class="portfolio-file-summary">${portfolioFileSummary(files)}</div></div>`;
  }
  function portfolioUploadRow(g,label,path,description=''){
    return `<div class="portfolio-upload-row"><div class="portfolio-upload-label"><strong>${esc(label)}</strong>${description?`<span>${esc(description)}</span>`:''}</div>${portfolioUploadButton(g,path)}</div>`;
  }
  function portfolioAssessmentCell(g,path){
    const files=portfolioFilesAt(g,path);
    return `<div class="portfolio-matrix-cell"><label class="portfolio-matrix-button">${files.length?`${files.length} file${files.length===1?'':'s'}`:'Add files'}<input type="file" multiple data-portfolio-upload="${esc(path)}"></label>${files.length?`<button type="button" class="portfolio-mini-clear" data-portfolio-clear="${esc(path)}" title="Clear">×</button>`:''}</div>`;
  }
  function portfolioAssessmentRow(g,base,label){
    const sample=`${base}/Sample of students answer`;
    return `<div class="portfolio-matrix-row"><div class="portfolio-matrix-name"><strong>${esc(label)}</strong></div>${portfolioAssessmentCell(g,`${base}/Questions with answer key`)}${portfolioAssessmentCell(g,`${sample}/Excellent`)}${portfolioAssessmentCell(g,`${sample}/Average`)}${portfolioAssessmentCell(g,`${sample}/Poor`)}</div>`;
  }
  function portfolioCourseDocumentsHtml(g){
    const instructors=[...new Set(g.reports.map(r=>r.instructor).filter(Boolean))];
    return `<section class="portfolio-panel"><div class="portfolio-panel-head"><div><h2>Course documents</h2><p>Add the course-level documents that will be placed into the generated portfolio.</p></div><span class="portfolio-session-chip">Session only</span></div><div class="portfolio-upload-section">${portfolioUploadRow(g,'Course Specification (CS)','Course Specification (CS)','Course specification document(s)')}${portfolioUploadRow(g,'Teaching Materials (TM)','Teaching Materials (TM)','Lecture materials, learning resources, or related teaching documents')}${instructors.map(name=>`<div class="portfolio-instructor-group"><div class="portfolio-instructor-title"><span>Instructor</span><strong>${esc(name)}</strong></div>${portfolioUploadRow(g,'Curriculum Vitae (CV)',`Instructors/${safeFolderName(name)}/Curriculum Vitae (CV)`)}${portfolioUploadRow(g,'Teaching Philosophy (TP)',`Instructors/${safeFolderName(name)}/Teaching Philosophy (TP)`)}</div>`).join('')||'<div class="portfolio-empty-inline">Instructor information will appear after a Course Report is created.</div>'}</div></section>`;
  }
  function portfolioSemesterUploadsHtml(g,term){
    const base=`Year ${safeFolderName(g.academicYear)}/${semesterFolderName(term)}`,assessment=`${base}/Assessments`;
    const approved=portfolioApprovedReports(g,term);
    const rows=[
      portfolioAssessmentRow(g,`${assessment}/Assignment`,'Assignment'),
      portfolioAssessmentRow(g,`${assessment}/Midterm Exam/Theory`,'Midterm · Theory'),
      portfolioAssessmentRow(g,`${assessment}/Midterm Exam/Practical`,'Midterm · Practical'),
      portfolioAssessmentRow(g,`${assessment}/Midterm Exam/Clinical`,'Midterm · Clinical'),
      portfolioAssessmentRow(g,`${assessment}/Final Exam/Theory`,'Final · Theory'),
      portfolioAssessmentRow(g,`${assessment}/Final Exam/Practical`,'Final · Practical'),
      portfolioAssessmentRow(g,`${assessment}/Final Exam/Clinical`,'Final · Clinical')
    ].join('');
    return `<section class="portfolio-panel"><div class="portfolio-panel-head"><div><h2>${semesterFolderName(term)} uploads</h2><p>Upload assessment evidence and survey files for this semester. Itqan puts each file in its correct portfolio folder when you download.</p></div><span class="portfolio-file-count">${portfolioSelectedCount(g,base)} selected</span></div>
      <div class="portfolio-assessment-wrap"><div class="portfolio-subhead"><strong>Assessments</strong><span>Questions/answer keys and student samples</span></div><div class="portfolio-matrix"><div class="portfolio-matrix-header"><span>Assessment</span><span>Questions + key</span><span>Excellent</span><span>Average</span><span>Poor</span></div>${rows}</div>${portfolioUploadRow(g,'Other assessment files',`${assessment}/Others`,'Any assessment material that does not fit the categories above')}</div>
      <div class="portfolio-survey-wrap"><div class="portfolio-subhead"><strong>Reports and surveys</strong><span>Semester-specific supporting documents</span></div><div class="portfolio-two-col">${portfolioUploadRow(g,'Course Evaluation Survey',`${base}/Reports and Surveys/Course Evaluation Survey`)}${portfolioUploadRow(g,'Informal feedback',`${base}/Reports and Surveys/Informal feedback`)}</div></div>
      <div class="portfolio-generated-strip"><div><span class="portfolio-generated-icon">DOCX</span><p><strong>Course Report</strong><small>${approved.length?'Automatically generated from Coordinator-approved report data.':'Waiting for Coordinator approval; the folder will still be created.'}</small></p><b class="${approved.length?'ready':'waiting'}">${approved.length?'Generated':'Waiting'}</b></div><div><span class="portfolio-generated-icon">CSV</span><p><strong>CLOs Assessment Report</strong><small>${approved.length?'Automatically generated from approved CLO results.':'Waiting for Coordinator approval; the folder will still be created.'}</small></p><b class="${approved.length?'ready':'waiting'}">${approved.length?'Generated':'Waiting'}</b></div></div>
    </section>`;
  }
  function renderCoursePortfolios(){
    const groups=portfolioGroupsForRole();
    if(currentPortfolioId){const g=groups.find(x=>x.key===currentPortfolioId);if(g)return renderCoursePortfolioDetail(g);currentPortfolioId=null;}
    const approvedGroups=groups.filter(g=>portfolioApprovedReports(g).length>0).length;
    return roleHero()+pageHead('Generate on demand','Course Portfolios','Open a course, add the portfolio documents into the sections provided, then download the generated portfolio ZIP. Files selected here are temporary and are never saved by Itqan.',``)+`
      <div class="portfolio-summary-strip"><div><span>Course portfolios</span><strong>${groups.length}</strong><small>course + academic year</small></div><div><span>With approved reports</span><strong>${approvedGroups}</strong><small>Course Report and CLO files auto-generate</small></div><div><span>Reporting periods</span><strong>S1 · S2 · Summer</strong><small>upload sections kept separate</small></div><div><span>Uploaded files</span><strong>Temporary</strong><small>used only for the current download session</small></div></div>
      <div class="table-card section portfolio-board"><table class="data-table"><thead><tr><th>Course</th><th>Academic year</th><th>S1</th><th>S2</th><th>Summer</th><th>Approval</th><th></th></tr></thead><tbody>${groups.map(g=>`<tr><td><strong>${esc(g.courseCode)}</strong><div class="tiny">${esc(g.courseName)}</div></td><td><strong>${esc(g.academicYear)}</strong></td><td>${periodStatusHtml(g,'S1')}</td><td>${periodStatusHtml(g,'S2')}</td><td>${periodStatusHtml(g,'Summer')}</td><td>${progressHtml(portfolioOfficialPercent(g))}<div class="tiny" style="margin-top:4px">${esc(portfolioStatusText(g))}</div></td><td><button class="btn btn-ghost" data-open-portfolio="${esc(g.key)}">Build portfolio →</button></td></tr>`).join('')}</tbody></table></div>`;
  }
  function renderCoursePortfolioDetail(g){
    const approved=portfolioApprovedReports(g),instructors=[...new Set(g.reports.map(r=>r.instructor).filter(Boolean))];
    const term=portfolioActiveTerms.get(g.key)||g.reports.find(r=>r.semester)?.semester||'S1';portfolioActiveTerms.set(g.key,term);
    const selected=portfolioSelectedCount(g);
    return `<button class="btn btn-ghost" id="portfolioBack">← Course Portfolios</button>
      <div class="portfolio-detail-hero"><div class="portfolio-title-line"><div><span class="eyebrow">Course portfolio builder</span><h1>${esc(g.courseCode)} <span>— ${esc(g.courseName)}</span></h1><p>Add documents to the sections below, then download the portfolio. Itqan uses the files only to build the ZIP; it does not save or upload them anywhere.</p></div><div class="page-actions"><button class="btn btn-primary" id="downloadPortfolioZip">Download portfolio ZIP</button></div></div>
      <div class="portfolio-meta-row"><div><span>Academic year</span><strong>${esc(g.academicYear)}</strong></div><div><span>Instructors</span><strong>${esc(instructors.join(', ')||'—')}</strong></div><div><span>Files selected</span><strong>${selected}</strong></div><div><span>Approved reports</span><strong>${approved.length}</strong></div></div></div>
      <div class="portfolio-session-notice"><div><strong>Files are temporary</strong><span>Selected documents remain only in this open browser session. Refreshing or closing the page clears them.</span></div><span class="portfolio-session-pill">Not stored</span></div>
      ${portfolioCourseDocumentsHtml(g)}
      <div class="portfolio-term-tabs">${TERMS.map(t=>`<button type="button" class="portfolio-term-tab ${t===term?'active':''}" data-portfolio-term="${t}"><strong>${semesterFolderName(t)}</strong><span>${portfolioSelectedCount(g,`Year ${safeFolderName(g.academicYear)}/${semesterFolderName(t)}`)} files</span></button>`).join('')}</div>
      ${portfolioSemesterUploadsHtml(g,term)}
      <div class="portfolio-download-footer"><div><strong>Ready to generate</strong><span>${selected} selected file${selected===1?'':'s'} will be packaged with ${approved.length} approved Course Report record${approved.length===1?'':'s'} and generated CLO data.</span></div><button class="btn btn-primary" id="downloadPortfolioZipBottom">Download portfolio ZIP</button></div>`;
  }

  function renderPlo(){
    const roll=ploRollups(ploYear,ploTerm); const selected=activePlo?roll.find(x=>x.code===activePlo):null;
    return roleHero()+pageHead('Approved outcomes only','PLO Attainment','PLOs are calculated only from Coordinator-approved reports. Switch between S1, S2, Summer, or Annual for the selected academic year.',periodFilter())+`
      <div class="grid grid-4"><div class="card metric"><div class="label">Reporting period</div><div class="value period-value">${esc(ploTerm)}</div><div class="sub">${esc(ploYear)}</div></div><div class="card metric"><div class="label">Approved reports used</div><div class="value">${approvedReports(ploYear,ploTerm).length}</div><div class="sub">Pending/returned excluded</div></div><div class="card metric"><div class="label">Overall attainment</div><div class="value">${formatPct(overallPlo(ploYear,ploTerm))}</div><div class="sub">Weighted by completed students</div></div><div class="card metric"><div class="label">PLOs meeting target</div><div class="value">${roll.filter(x=>x.met).length}/${roll.length}</div><div class="sub">Official results</div></div></div>
      <div class="plo-grid section">${roll.map(p=>`<div class="plo-card ${activePlo===p.code?'active':''}" data-plo="${esc(p.code)}"><div class="plo-card-head"><span class="plo-code">${esc(p.code)}</span><span class="plo-score ${p.actual!==null&&!p.met?'text-warn':''}">${p.actual===null?'—':formatPct(p.actual)}</span></div><div class="plo-name">${esc(p.name)}</div><div class="mini-bar"><span style="width:${clamp(p.actual||0)}%"></span></div><div class="tiny" style="margin-top:8px">Target ${p.target}% · ${p.rows.length} approved CLO source${p.rows.length===1?'':'s'}</div></div>`).join('')}</div>
      ${selected?renderPloDetail(selected):''}`;
  }
  function renderPloDetail(p){return `<div class="section"><div class="section-title"><div><h2>${esc(p.code)} traceability</h2><p>Every contribution links back to an approved Course Report and reporting period.</p></div></div><div class="table-card"><table class="data-table rollup-table"><thead><tr><th>Course</th><th>Period</th><th>CLO</th><th>Actual</th><th>Completed students</th><th></th></tr></thead><tbody>${p.rows.length?p.rows.map(x=>`<tr><td>${esc(x.report.courseCode)}</td><td>${periodPill(x.report)}</td><td><strong>${esc(x.clo.code)}</strong><div class="tiny">${esc(x.clo.text)}</div></td><td>${formatPct(x.actual)}</td><td>${x.weight}</td><td><button class="btn btn-ghost" data-edit-report="${x.report.id}">View approved report</button></td></tr>`).join(''):'<tr><td colspan="6" class="empty">No approved CLO evidence for this PLO in the selected period.</td></tr>'}</tbody></table></div></div>`}

  function renderApr(){
    const year=ploYear,annual=ploRollups(year,'Annual'),terms=TERMS.map(t=>({t,roll:ploRollups(year,t)}));
    return roleHero()+pageHead('Annual aggregation','Annual Program Report',`APR ${year} combines only approved S1, S2, and Summer course-report results. Semester results remain traceable separately.`,`<label class="inline-select-label"><span>Academic year</span><select id="aprYear">${state.academicYears.map(y=>`<option ${y===year?'selected':''}>${esc(y)}</option>`).join('')}</select></label><button class="btn btn-ghost" id="exportAprCsv">Export APR data</button>`)+`
      <div class="apr-hero"><div><span class="eyebrow">APR ${esc(year)}</span><h2>${aprReadiness(year)}% reporting readiness</h2><p>${approvedReports(year,'Annual').length} Quality-approved report${approvedReports(year,'Annual').length===1?'':'s'} currently feed the annual program report.</p></div><div class="apr-score">${formatPct(overallPlo(year,'Annual'))}<span>overall PLO attainment</span></div></div>
      <div class="section"><div class="section-title"><div><h2>Semester separation</h2><p>Annual values do not overwrite semester results.</p></div></div><div class="grid grid-3">${terms.map(x=>`<div class="card"><span class="eyebrow">${x.t} ${esc(year)}</span><div class="big-inline">${formatPct(overallPlo(year,x.t))}</div><div class="tiny">${approvedReports(year,x.t).length} approved report${approvedReports(year,x.t).length===1?'':'s'} · ${x.roll.filter(p=>p.met).length}/${x.roll.length} PLOs meeting target</div></div>`).join('')}</div></div>
      <div class="section"><div class="section-title"><div><h2>Annual PLO table</h2><p>Weighted by completed students across all approved semesters.</p></div></div><div class="table-card"><table class="data-table"><thead><tr><th>PLO</th><th>Target</th><th>S1</th><th>S2</th><th>Summer</th><th>Annual</th><th>Status</th></tr></thead><tbody>${annual.map(p=>`<tr><td><strong>${esc(p.code)}</strong><div class="tiny">${esc(p.name)}</div></td><td>${p.target}%</td>${TERMS.map(t=>{const q=ploRollups(year,t).find(z=>z.code===p.code);return `<td>${q?.actual==null?'—':formatPct(q.actual)}</td>`}).join('')}<td><strong>${p.actual==null?'—':formatPct(p.actual)}</strong></td><td>${p.actual==null?'<span class="tag">No data</span>':p.met?'<span class="tag blue">Achieved</span>':'<span class="status-pill status-ReturnedforRevision">Below target</span>'}</td></tr>`).join('')}</tbody></table></div></div>`;
  }

  const KPI_OWNERS=['Academic','Research','Quality','Extracurricular','HOD'];
  const kpiUnit=k=>k.unit==='ratio'?`out of ${k.ratio_out_of}`:'%';
  const kpiValue=(v,k)=>v==null?'Not entered':k.unit==='ratio'?`${esc(v)} / ${esc(k.ratio_out_of)}`:`${esc(v)}%`;
  const kpiInDepartment=()=>Core.kpiDepartmentAccess(currentUser,state.program.department);
  const canManageKpi=()=>kpiInDepartment()&&Core.canEditKpi(currentUser);
  const canManageKpiAction=k=>kpiInDepartment()&&Core.canEditKpiAction(currentUser,k);
  const kpiHasResults=k=>state.kpiYears.some(r=>r.kpi_id===k.id&&['internal','target','external','actual','new_target'].some(key=>r[key]!=null))||state.kpiPriorities.some(p=>p.kpi_id===k.id&&state.kpiActions.some(a=>a.priority_id===p.id&&a.target!=null));
  function kpiCurrentYear(){return Core.kpiYearStart(ploYear);}
  function kpiYearRecord(k){return state.kpiYears.find(r=>r.kpi_id===k.id&&Number(r.year_start)===kpiCurrentYear())||{};}
  function kpiField(id,label,value='',type='text',extra=''){return `<div class="field f6"><label for="${id}">${esc(label)}</label><input id="${id}" type="${type}" value="${esc(value??'')}" ${extra}></div>`;}
  function kpiText(id,label,value=''){return `<div class="field f12"><label for="${id}">${esc(label)}</label><textarea id="${id}" rows="3" maxlength="10000">${esc(value||'')}</textarea></div>`;}
  function kpiChart(k,year){
    const points=Core.kpiTrend(state.kpiYears,k.id,year),max=Math.max(1,...points.map(p=>p.actual??0));
    return `<figure class="kpi-chart"><figcaption>Actual benchmark · three-year trend (${esc(kpiUnit(k))})</figcaption><div class="kpi-bars" role="img" aria-label="${esc(points.map(p=>`${Core.kpiYearLabel(p.year,ploYear)}: ${p.actual??'No data'}`).join('; '))}">${points.map(p=>`<div class="kpi-bar-column"><strong>${p.actual==null?'No data':esc(p.actual)}</strong><div class="kpi-bar-space"><div class="kpi-bar ${p.year===year?'current':''}" style="height:${p.actual==null?0:p.actual/max*100}%"></div></div><span>${esc(Core.kpiYearLabel(p.year,ploYear))}</span></div>`).join('')}</div><p class="tiny">Scale starts at 0. Missing values are not plotted.</p></figure>`;
  }
  function renderKpis(){
    if(!kpiInDepartment())return pageHead('Performance management','Key Performance Indicators','KPIs are available only within the department where they were created.')+'<div class="card">This program belongs to another department. Select a program in your department to view its KPIs.</div>';
    const editable=canManageKpi(),year=kpiCurrentYear();
    const years=[...new Set([...state.academicYears,...state.kpiYears.map(r=>Core.kpiYearLabel(r.year_start,ploYear)),... (year==null?[]:[-2,-1,0,1].map(n=>Core.kpiYearLabel(year+n,ploYear)))])].filter(y=>Core.kpiYearStart(y)!=null).sort((a,b)=>Core.kpiYearStart(b)-Core.kpiYearStart(a));
    const head=pageHead('Performance management','Key Performance Indicators','The HOD sets department KPIs, benchmarks, analysis and priorities. Owner categories can be assigned before users register.',`<label class="inline-select-label"><span>Academic year</span><select id="kpiYear" aria-label="KPI academic year">${years.map(y=>`<option ${Core.kpiYearStart(y)===year?'selected':''}>${esc(y)}</option>`).join('')}</select></label>${editable?'<button class="btn btn-primary" id="newKpi">＋ New KPI</button>':''}`);
    if(year==null)return head+'<div class="card">The HOD must configure an academic year such as 2026–2027 in Program Setup.</div>';
    const cards=state.kpiDefinitions.map(k=>{
      const r=kpiYearRecord(k),internal=Core.kpiInternal(state.kpiYears,k.id,year,r.internal),priorities=state.kpiPriorities.filter(p=>p.kpi_id===k.id&&Number(p.year_start)===year);
      return `<article class="card kpi-card" id="kpi-${esc(k.id)}"><div class="section-title"><div><span class="eyebrow">${esc(k.code)}</span><h2>${esc(k.name)}</h2><p>Owner: <strong>${esc(k.owner_category)}</strong> · ${esc(k.owner_name||'User not linked yet')}</p></div>${editable?`<button class="btn btn-ghost" data-kpi-definition="${esc(k.id)}">Edit KPI / owner</button><button class="btn btn-primary" data-kpi-year="${esc(k.id)}">Edit annual record</button>`:'<span class="tag">Read-only KPI</span>'}</div><dl class="kpi-benchmarks">${[['Internal Benchmark',internal.value],['Target Benchmark',r.target],['External Benchmark',r.external],['Actual Benchmark',r.actual],['New Target Benchmark',r.new_target]].map(([label,v])=>`<div><dt>${label}</dt><dd>${kpiValue(v,k)}</dd></div>`).join('')}</dl><p class="tiny">${internal.automatic?'Internal benchmark automatically uses the previous year’s actual.':'No previous-year actual is available. The HOD can enter an internal benchmark.'}</p><div class="kpi-detail-grid">${kpiChart(k,year)}<section><h3>Analysis</h3>${[['Strengths',r.strengths],['Weaknesses',r.weaknesses],['Comparisons',r.comparisons]].map(([label,v])=>`<h4>${label}</h4><p class="kpi-narrative">${esc(v||'Not entered')}</p>`).join('')}</section></div><section><div class="section-title"><h3>Priorities for Improvement</h3>${editable?`<button class="btn btn-ghost" data-kpi-priority-new="${esc(k.id)}">＋ Add priority</button>`:''}</div>${priorities.length?`<ul class="kpi-priorities">${priorities.map(p=>`<li><span>${esc(p.priority)}</span>${editable?`<button class="btn btn-ghost" data-kpi-priority="${esc(p.id)}">Edit priority</button>`:''}</li>`).join('')}</ul>`:'<p class="tiny">No priorities entered for this year.</p>'}</section></article>`;
    }).join('');
    const priorities=state.kpiPriorities.filter(p=>Number(p.year_start)===year);
    return head+(cards||'<div class="card"><h2>No KPIs yet</h2><p>The HOD can add the first KPI and assign its owner.</p></div>')+`<section class="section"><h2>Priorities for Improvement · Action Plan</h2><p>Priorities and KPI names are linked to the records above. Only the assigned KPI owner can edit the remaining fields.</p><div class="table-card kpi-table-wrap"><table class="data-table"><thead><tr>${['Priorities for improvement','Actions','Responsible','Start Date','End Date','KPI','Target Benchmark',''].map(t=>`<th>${t}</th>`).join('')}</tr></thead><tbody>${priorities.map(p=>{const k=state.kpiDefinitions.find(k=>k.id===p.kpi_id);if(!k)return '';const a=state.kpiActions.find(a=>a.priority_id===p.id)||{};return `<tr><td class="kpi-narrative">${esc(p.priority)}</td><td class="kpi-narrative">${esc(a.actions||'Awaiting owner')}</td><td>${esc(a.responsible||'—')}</td><td>${esc(a.start_date||'—')}</td><td>${esc(a.end_date||'—')}</td><td><strong>${esc(k.code)}</strong><div>${esc(k.name)}</div><div class="tiny">${esc(k.owner_category)} · ${esc(k.owner_name||'User not linked yet')}</div></td><td>${kpiValue(a.target,k)}</td><td>${canManageKpiAction(k)?`<button class="btn btn-ghost" data-kpi-action="${esc(p.id)}">Edit action plan</button>`:'Owner only'}</td></tr>`;}).join('')||'<tr><td colspan="8">No improvement priorities for this year.</td></tr>'}</tbody></table></div></section>`;
  }
  async function saveKpiRow(table,key,row,identity='id'){
    if(!kpiInDepartment())throw new Error('KPI access is restricted to your department.');
    const existing=state[key].find(r=>r[identity]===row[identity]);
    let saved=row;
    if(backendEnabled){
      let result;
      if(existing){const changes={...row};for(const field of [identity,'program_id','kpi_id','year_start'])delete changes[field];result=await Backend.patch(table,`${identity}=eq.${encodeURIComponent(row[identity])}`,changes);}
      else result=await Backend.insert(table,row);
      if(!result?.[0])throw new Error('Save was not permitted or the record changed. Refresh and try again.');
      saved=result[0];
    }
    if(existing)Object.assign(existing,saved);else state[key].push(saved);
    saveState();
  }
  function kpiSubmit(handler){
    $('kpiForm').addEventListener('submit',async e=>{e.preventDefault();const b=$('saveKpi');b.disabled=true;try{await handler();hideModal();render();toast('KPI changes saved.');}catch(error){$('kpiError').textContent=error.message||'Could not save. Please try again.';}finally{b.disabled=false;}});
  }
  function kpiModal(title,fields){$('modalTitle').textContent=title;$('modalBody').innerHTML=`<form id="kpiForm" class="form-grid">${fields}<p id="kpiError" class="f12" role="alert"></p><div class="field f12"><button id="saveKpi" class="btn btn-primary" type="submit">Save</button></div></form>`;showModal();}
  async function editKpiDefinition(id){
    if(!canManageKpi()||kpiCurrentYear()==null)return;
    await loadUsers();
    const k=state.kpiDefinitions.find(k=>k.id===id)||{};
    const owners=userDirectory.filter(u=>u.department===state.program.department&&u.active!==false&&['Head of Department','Instructor','Coordinator'].includes(canonicalUiRole(u.role))&&(!backendEnabled||(u.programIds||[]).includes(activeProgramId)));
    kpiModal(id?'Edit KPI and owner':'New Key Performance Indicator',kpiField('kCode','KPI code',k.code,'text','required maxlength="60"')+kpiField('kName','KPI name',k.name,'text','required maxlength="500"')+`<div class="field f6"><label for="kUnit">Measurement</label><select id="kUnit" ${kpiHasResults(k)?'disabled':''}><option value="%" ${k.unit!=='ratio'?'selected':''}>Percentage (%)</option><option value="ratio" ${k.unit==='ratio'?'selected':''}>Ratio</option></select></div><div class="field f6" id="kRatioField"><label for="kRatioOutOf">Ratio: out of</label><input id="kRatioOutOf" type="number" min="0.000000001" max="1000000000000" step="any" placeholder="e.g. 5, 10 or 1" value="${esc(k.ratio_out_of??'')}" ${kpiHasResults(k)?'disabled':''}></div>${kpiHasResults(k)?'<p class="f12 tiny">Measurement is fixed once benchmarks exist, so historical results stay comparable.</p>':''}`+`<div class="field f6"><label for="kCategory">Owner category</label><select id="kCategory">${KPI_OWNERS.map(c=>`<option ${c===k.owner_category?'selected':''}>${c}</option>`).join('')}</select></div><div class="field f12"><label for="kOwner">Link a registered user (optional)</label><select id="kOwner"><option value="">Not registered / link later</option>${owners.map(u=>`<option value="${esc(u.id)}" ${u.id===k.owner_user_id?'selected':''}>${esc(displayUserName(u))} (${esc(u.role)})</option>`).join('')}</select></div>`);
    const syncRatio=()=>{const ratio=$('kUnit').value==='ratio';$('kRatioField').classList.toggle('hidden',!ratio);$('kRatioOutOf').required=ratio;};$('kUnit').addEventListener('change',syncRatio);syncRatio();
    kpiSubmit(async()=>{if(!canManageKpi())throw new Error('HOD access required.');const owner=owners.find(u=>u.id===$('kOwner').value),code=$('kCode').value.trim(),name=$('kName').value.trim(),measurement=Core.kpiMeasurement($('kUnit').value,$('kRatioOutOf').value);if(!code||!name)throw new Error('Complete the KPI code and name.');if(owner&&$('kCategory').value==='HOD'&&canonicalUiRole(owner.role)!=='Head of Department')throw new Error('Select an HOD user for the HOD category.');if(state.kpiDefinitions.some(other=>other.id!==k.id&&other.code.toLowerCase()===code.toLowerCase()))throw new Error('This KPI code already exists.');await saveKpiRow('kpi_definitions','kpiDefinitions',{id:k.id||uid(),program_id:activeProgramId,code,name,...measurement,owner_category:$('kCategory').value,owner_user_id:owner?.id||null,owner_name:owner?displayUserName(owner):''});});
  }
  function editKpiYear(id){
    if(!canManageKpi())return;
    const k=state.kpiDefinitions.find(k=>k.id===id);if(!k)return;
    const r=kpiYearRecord(k),internal=Core.kpiInternal(state.kpiYears,id,kpiCurrentYear(),r.internal);
    kpiModal(`${k.code} · ${ploYear}`,`<p class="f12">Benchmarks use ${esc(kpiUnit(k))}. Leave unknown values blank.</p>`+[['internal','Internal Benchmark',internal.value],['target','Target Benchmark',r.target],['external','External Benchmark',r.external],['actual','Actual Benchmark',r.actual],['new_target','New Target Benchmark',r.new_target]].map(([key,label,value])=>kpiField('kb_'+key,label,value,'number',`min="0" max="${k.unit==='%'?100:1000000000000}" step="any" ${key==='internal'&&internal.automatic?'readonly aria-describedby="internalSource"':''}`)).join('')+`<p id="internalSource" class="f12 tiny">${internal.automatic?'Internal benchmark is linked to last year’s actual and cannot be overridden.':'No prior actual: enter an internal benchmark if available.'}</p>`+kpiText('kStrengths','Analysis: Strengths',r.strengths)+kpiText('kWeaknesses','Analysis: Weaknesses',r.weaknesses)+kpiText('kComparisons','Analysis: Comparisons',r.comparisons));
    kpiSubmit(async()=>{if(!canManageKpi())throw new Error('HOD access required.');const row={id:r.id||uid(),program_id:activeProgramId,kpi_id:id,year_start:kpiCurrentYear(),strengths:$('kStrengths').value.trim(),weaknesses:$('kWeaknesses').value.trim(),comparisons:$('kComparisons').value.trim()};for(const key of ['internal','target','external','actual','new_target'])row[key]=key==='internal'&&internal.automatic?(r.internal??null):Core.kpiBenchmark($('kb_'+key).value,k);await saveKpiRow('kpi_years','kpiYears',row);});
  }
  function editKpiPriority(kpiId,id){
    if(!canManageKpi())return;
    const p=state.kpiPriorities.find(p=>p.id===id)||{},k=state.kpiDefinitions.find(k=>k.id===(p.kpi_id||kpiId));if(!k)return;
    kpiModal('Priority for Improvement',`<p class="f12">${esc(k.code)} · ${esc(ploYear)}</p>`+kpiText('kPriority','Priority for improvement',p.priority));$('kPriority').required=true;
    kpiSubmit(async()=>{if(!canManageKpi())throw new Error('HOD access required.');const priority=$('kPriority').value.trim();if(!priority)throw new Error('Enter a priority.');await saveKpiRow('kpi_priorities','kpiPriorities',{id:p.id||uid(),program_id:activeProgramId,kpi_id:k.id,year_start:kpiCurrentYear(),priority});});
  }
  function editKpiAction(id){
    const p=state.kpiPriorities.find(p=>p.id===id),k=state.kpiDefinitions.find(k=>k.id===p?.kpi_id);if(!p||!canManageKpiAction(k))return;
    const a=state.kpiActions.find(a=>a.priority_id===id)||{},r=kpiYearRecord(k);
    kpiModal('KPI improvement action plan',`<p class="f12"><strong>${esc(k.code)} · ${esc(k.name)}</strong><br>${esc(p.priority)}</p>`+kpiText('kActions','Actions',a.actions)+kpiField('kResponsible','Responsible',a.responsible,'text','maxlength="500"')+kpiField('kStart','Start Date',a.start_date,'date')+kpiField('kEnd','End Date',a.end_date,'date')+kpiField('kActionTarget',`Target Benchmark (${kpiUnit(k)})`,a.target??r.new_target??r.target,'number',`min="0" max="${k.unit==='%'?100:1000000000000}" step="any"`)+'<p class="f12 tiny">The suggested target comes from the KPI’s new target (or target). The owner may change it for this action plan.</p>');
    kpiSubmit(async()=>{if(!canManageKpiAction(k))throw new Error('Only the assigned KPI owner can edit this action plan.');const start=$('kStart').value||null,end=$('kEnd').value||null;if(start&&end&&end<start)throw new Error('End Date must be on or after Start Date.');await saveKpiRow('kpi_actions','kpiActions',{priority_id:id,program_id:activeProgramId,actions:$('kActions').value.trim(),responsible:$('kResponsible').value.trim(),start_date:start,end_date:end,target:Core.kpiBenchmark($('kActionTarget').value,k)},'priority_id');});
  }
  function bindKpiEvents(){
    $('dashboardNewKpi')?.addEventListener('click',()=>{go('kpis');editKpiDefinition();});
    document.querySelectorAll('[data-dashboard-kpi]').forEach(b=>b.addEventListener('click',()=>{const id=b.dataset.dashboardKpi;if(isSupervisorRole(state.role))ploYear=supervisorFilters.year;go('kpis');document.getElementById('kpi-'+id)?.scrollIntoView({block:'start',behavior:'smooth'});}));
    $('newKpi')?.addEventListener('click',()=>editKpiDefinition());
    $('kpiYear')?.addEventListener('change',e=>{ploYear=e.target.value;render();});
    document.querySelectorAll('[data-kpi-definition]').forEach(b=>b.addEventListener('click',()=>editKpiDefinition(b.dataset.kpiDefinition)));
    document.querySelectorAll('[data-kpi-year]').forEach(b=>b.addEventListener('click',()=>editKpiYear(b.dataset.kpiYear)));
    document.querySelectorAll('[data-kpi-priority-new]').forEach(b=>b.addEventListener('click',()=>editKpiPriority(b.dataset.kpiPriorityNew)));
    document.querySelectorAll('[data-kpi-priority]').forEach(b=>b.addEventListener('click',()=>editKpiPriority(null,b.dataset.kpiPriority)));
    document.querySelectorAll('[data-kpi-action]').forEach(b=>b.addEventListener('click',()=>editKpiAction(b.dataset.kpiAction)));
  }

  function renderOperational(){
    return roleHero()+pageHead('Execution','Operational Plan','Existing operational records. Manage annual KPI benchmarks and owner improvement actions in Key Performance Indicators.','<button class="btn btn-primary" data-go="kpis">Open Key Performance Indicators</button>')+`
      <div class="table-card"><table class="data-table"><thead><tr><th>Objective</th><th>KPI</th><th>Target</th><th>Actual</th><th>Owner</th><th>Due</th><th>Status</th></tr></thead><tbody>${state.operational.map(x=>`<tr><td><strong>${esc(x.objective)}</strong></td><td>${esc(x.kpi)}</td><td>${x.target}${esc(x.unit||'%')}</td><td>${x.actual}${esc(x.unit||'%')}</td><td>${esc(x.owner)}</td><td>${esc(x.due||'—')}</td><td>${statusPill(x.status)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function renderAutomations(){return roleHero()+pageHead('Workflow engine','Automations','Core controls that prevent unapproved data from entering official program quality results.')+`<div class="grid grid-2">${state.automations.map(a=>`<div class="card automation-card"><div class="automation-icon">${esc(a.icon)}</div><div><strong>${esc(a.name)}</strong><p>${esc(a.description)}</p></div><span class="tag blue">Active</span></div>`).join('')}</div>`}

  function renderSystemAdminDashboard(){
    const open=programDirectory.filter(p=>p.status==='Open').length;
    const activeUsers=userDirectory.filter(u=>u.active!==false).length;
    const hods=userDirectory.filter(u=>u.role==='Head of Department').length;
    const pingedAt=keepaliveStatus?.pinged_at?new Date(keepaliveStatus.pinged_at):null;
    const nextAt=pingedAt?new Date(pingedAt.getTime()+5*24*60*60*1000):null;
    const ageDays=pingedAt?(Date.now()-pingedAt.getTime())/(24*60*60*1000):null;
    const heartbeatHealthy=!!pingedAt&&ageDays<6;
    const heartbeatState=keepaliveStatus?.error?'Unavailable':heartbeatHealthy?'Healthy':pingedAt?'Overdue':'Waiting for first heartbeat';
    const heartbeatClass=heartbeatHealthy?'text-good':keepaliveStatus?.error||pingedAt?'text-warn':'';
    const heartbeatPanel=`<div class="section"><div class="section-title"><div><h2>Supabase project heartbeat</h2><p>A lightweight scheduled database heartbeat records one row approximately every five days. This table is isolated from Itqan business data and visible only to System Administrators.</p></div><span class="tag blue">Scheduled</span></div><div class="grid grid-3"><div class="card"><span class="eyebrow">Status</span><div class="big ${heartbeatClass}" style="margin:10px 0 4px">${esc(heartbeatState)}</div><div class="tiny">Cron checks daily and inserts only after five days have elapsed.</div></div><div class="card"><span class="eyebrow">Last heartbeat</span><div style="font-weight:760;margin:12px 0 5px">${pingedAt?esc(pingedAt.toLocaleString()):'—'}</div><div class="tiny">Source: ${esc(keepaliveStatus?.source||'—')}</div></div><div class="card"><span class="eyebrow">Next expected</span><div style="font-weight:760;margin:12px 0 5px">${nextAt?esc(nextAt.toLocaleString()):'—'}</div><div class="tiny">Approximately five days after the latest successful heartbeat.</div></div></div></div>`;
    return dashboardHead('Platform control','Itqan Administration','System-wide control for academic programs and authorized users.',backendEnabled?'<button class="btn btn-ghost" id="backupAllData">Backup Entire System (.xlsx)</button>':'')+`
      <div class="grid grid-4"><div class="card metric"><div class="label">Academic programs</div><div class="value">${programDirectory.length}</div><div class="sub">${open} currently open</div></div><div class="card metric"><div class="label">Authorized users</div><div class="value">${activeUsers}</div><div class="sub">Across all programs</div></div><div class="card metric"><div class="label">Heads of Department</div><div class="value">${hods}</div><div class="sub">Program leadership assignments</div></div><div class="card metric"><div class="label">System backup</div><div class="value">XLSX</div><div class="sub">All structured data; no generated DOCX stored</div></div></div>${heartbeatPanel}
      <div class="section"><div class="section-title"><div><h2>Academic programs</h2><p>Open and closed program workspaces managed by the System Administrator.</p></div><button class="btn btn-primary" data-go="setup">Manage programs</button></div>${programTableHtml()}</div>`;
  }
  function programTableHtml(){
    const rows=programDirectory.map(p=>`<tr><td><strong>${esc(p.code)}</strong><div class="tiny">${esc(p.name)}</div></td><td>${esc(p.department||'—')}</td><td>${esc(p.current_academic_year||'—')}</td><td>${statusPill(p.status)}</td><td>${esc(String(p.created_at||'').slice(0,10)||'—')}</td></tr>`).join('');
    return `<div class="table-card"><table class="data-table"><thead><tr><th>Program</th><th>Department</th><th>Academic year</th><th>Status</th><th>Created</th></tr></thead><tbody>${rows||'<tr><td colspan="5" class="empty">No academic programs have been created yet.</td></tr>'}</tbody></table></div>`;
  }
  function renderUsers(){
    const isAdmin=state.role==='System Administrator';
    const openPrograms=programDirectory.filter(p=>p.status==='Open');
    const departments=isAdmin?uniqueDepartments(openPrograms):[currentUser?.department||state.program.department].filter(Boolean);
    const departmentOptions=departments.map(department=>`<option value="${esc(department)}">${esc(department)}</option>`).join('');
    const roleOptions=isAdmin?'<option>APU</option><option>VDAA</option><option>HOD</option><option>Coordinator</option><option>Instructor</option>':'<option>Instructor</option><option>Coordinator</option>';
    const rows=userDirectory.map(u=>{
      const programs=(u.programIds||[]).map(id=>programDirectory.find(p=>p.id===id)).filter(Boolean);
      const supervisor=isSupervisorRole(u.role);
      const access=u.role==='System Administrator'?'Global':supervisor?'All programs · Read only':u.limitProgramAccess?`${programs.length} selected program${programs.length===1?'':'s'}`:`All ${u.department||''} programs`;
      const detail=supervisor?'System-wide supervision':u.limitProgramAccess&&programs.length?programs.map(programDirectoryLabel).join(', '):u.department||'System';
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
  function renderProgramsAdmin(){
    const departments=uniqueDepartments(programDirectory);
    const departmentSuggestions=departments.map(department=>`<option value="${esc(department)}"></option>`).join('');
    const programSuggestions=[...new Set(programDirectory.map(p=>String(p.name||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b)).map(name=>`<option value="${esc(name)}"></option>`).join('');
    const rows=programDirectory.map(p=>`<tr><td><strong>${esc(p.code)}</strong><div class="tiny">${esc(p.name)}</div></td><td><span class="tag blue">${esc(programTypeLabel(p))}</span></td><td>${esc(p.department||'—')}</td><td>${esc(p.institution||'—')}</td><td>${esc(p.college||'—')}</td><td>${statusPill(p.status)}</td><td><button class="btn btn-ghost" data-program-toggle="${p.id}" data-program-status="${p.status}">${p.status==='Open'?'Close':'Open'}</button></td></tr>`).join('');
    return roleHero()+pageHead('System administration','Academic Programs','Create each academic program once. Academic years are configured later by the HOD in Program Settings, so a program is never duplicated for a new year.')+`
      <div class="user-admin-grid"><div class="table-card"><table class="data-table"><thead><tr><th>Academic program</th><th>Type</th><th>Department</th><th>Institution</th><th>College</th><th>Status</th><th></th></tr></thead><tbody>${rows||'<tr><td colspan="7" class="empty">No academic programs yet.</td></tr>'}</tbody></table></div>
      <div class="card user-add-card"><h3>Add academic program</h3><p>Programs are permanent master records. Do not enter an academic year here.</p><div class="form-grid"><div class="field f12"><label>Department *</label><input id="apDepartment" list="apDepartmentList" placeholder="e.g. Health Information Management" autocomplete="off"><datalist id="apDepartmentList">${departmentSuggestions}</datalist></div><div class="field f8"><label>Academic program *</label><input id="apName" list="apProgramNameList" placeholder="e.g. Health Information Management" autocomplete="off"><datalist id="apProgramNameList">${programSuggestions}</datalist></div><div class="field f4"><label>Program type *</label><select id="apProgramType"><option value="">Select type</option>${PROGRAM_TYPES.map(type=>`<option value="${esc(type)}">${esc(type)}</option>`).join('')}</select></div><div class="field f4"><label>Program code *</label><input id="apCode" placeholder="BHIM" autocomplete="off"></div><div class="field f12"><label>Institution</label><input id="apInstitution" autocomplete="off"></div><div class="field f12"><label>College</label><input id="apCollege" autocomplete="off"></div><div class="field f12"><button class="btn btn-primary" id="createAcademicProgram" style="width:100%">Add academic program</button></div></div></div></div>`;
  }
  function renderSetup(){
    if(state.role==='System Administrator') return renderProgramsAdmin();
    const managed=programDirectory.filter(p=>accessibleProgramIds.includes(p.id));
    const identity=`<div class="card"><h3 style="margin-top:0">Program identity</h3><div class="form-grid"><div class="field f12"><label>Academic program</label><input value="${esc(state.program.name)}" disabled></div><div class="field f6"><label>Program type</label><input value="${esc(state.program.programType||'—')}" disabled></div><div class="field f6"><label>Department</label><input value="${esc(state.program.department)}" disabled></div><div class="field f6"><label>Institution</label><input value="${esc(state.program.institution||'—')}" disabled></div><div class="field f6"><label>College</label><input value="${esc(state.program.college||'—')}" disabled></div></div><p class="tiny">Program identity is controlled by the System Administrator. ${managed.length>1?'Use the Program selector in the top bar to configure another program.':''}</p></div>`;
    const settings=`<div class="card"><h3 style="margin-top:0">Academic year settings</h3><p class="tiny">Academic years belong to this program's settings and do not create another Academic Program record.</p><div class="form-grid"><div class="field f6"><label>Current academic year *</label><input id="spYear" value="${esc(state.program.academicYear)}" placeholder="2026–2027"></div><div class="field f6"><label>Available academic years *</label><input id="spYears" value="${esc(state.academicYears.join(', '))}" placeholder="2026–2027, 2027–2028"></div><div class="field f12"><button class="btn btn-primary" id="saveSetup">Save Program Settings</button></div></div></div>`;
    return roleHero()+pageHead('Administration','Program Settings','The HOD configures academic years separately for each assigned academic program. Program identity stays permanent.')+`<div class="grid grid-2">${identity}${settings}</div><div class="card" style="margin-top:14px"><h3 style="margin-top:0">PLO targets</h3>${state.plos.map((p,i)=>`<div class="setup-plo-row"><strong>${esc(p.code)}</strong><span>${esc(p.name)}</span><input type="number" min="0" max="100" value="${p.target}" data-plo-target="${i}"></div>`).join('')}<button class="btn btn-ghost" id="savePloTargets" style="margin-top:12px">Save targets</button></div>`;
  }




  function openReport(id){
    const r=state.reports.find(x=>x.id===id); if(!r)return; ensureSectionModel(r); currentReportId=id;
    $('drawerEyebrow').textContent = state.role==='Coordinator'&&r.status==='Awaiting Quality Approval'?'Quality approval review':'Course report';
    $('drawerTitle').textContent = `${r.courseCode} · ${periodLabel(r)}`;
    const editable=canEditReport(r), review=state.role==='Coordinator'&&r.status==='Awaiting Quality Approval';
    $('drawerBody').innerHTML=reportFormHtml(r,editable,review);
    const actions=[];
    actions.push(`<button class="btn btn-ghost" id="downloadReport">Generate DOCX</button>`);
    if(editable){actions.push(`<button class="btn btn-soft" id="saveReport">Save draft</button><button class="btn btn-primary" id="submitReport">Submit for Quality Approval</button>`);}
    if(review){actions.push(`<button class="btn btn-danger" id="returnReport">Return for Revision</button><button class="btn btn-primary" id="approveReport">Approve Course Report</button>`);}
    $('drawerFoot').innerHTML=actions.join(''); showDrawer(); bindReportEvents(r,editable,review);
  }

  function reportFormHtml(r,editable,review){
    const dis=editable?'':'disabled';
    return `<div class="review-banner"><strong>${esc(periodLabel(r))}</strong><span>${sectionLabel(r.sectionMode)} scope · ${esc(r.instructor)} · ${statusPill(r.status)}</span></div>
      ${review?'<div class="approval-gate-note"><strong>Quality approval gate</strong><span>You are reviewing the exact instructor-entered data. Fields are read-only. Approve to release CLOs to PLO/APR/HOD, or return with a revision reason.</span></div>':''}
      ${r.status==='Returned for Revision'&&r.revisionNote?`<div class="revision-note"><strong>Coordinator revision request</strong><span>${esc(r.revisionNote)}</span></div>`:''}
      <div class="form-grid"><div class="field f3"><label>Course code</label><input id="rfCode" value="${esc(r.courseCode)}" ${dis}></div><div class="field f9"><label>Course title</label><input id="rfName" value="${esc(r.courseName)}" ${dis}></div><div class="field f4"><label>Academic year</label><select id="rfYear" ${dis}>${state.academicYears.map(y=>`<option ${y===r.academicYear?'selected':''}>${esc(y)}</option>`).join('')}</select></div><div class="field f4"><label>Semester</label><select id="rfSemester" ${dis}>${TERMS.map(t=>`<option ${t===r.semester?'selected':''}>${t}</option>`).join('')}</select></div><div class="field f4"><label>Report date</label><input type="date" id="rfDate" value="${esc(r.reportDate||nowDate())}" ${dis}></div><div class="field f6"><label>Instructor</label><input id="rfInstructor" value="${esc(r.instructor)}" disabled></div><div class="field f6"><label>Coordinator</label><input id="rfCoordinator" value="${esc(r.coordinator||r.instructor)}" ${dis}></div></div>
      <div class="drawer-section"><div class="drawer-section-head"><h3>Section reporting scope</h3><span>${sectionPill(r.sectionMode)}</span></div>${editable?`<div class="scope-selector">${[['male','Male','Male section only'],['female','Female','Female section only'],['combined','Combined','Combined result only'],['all','All','Enter Male + Female together; Combined auto-calculates']].map(([k,l,d])=>`<div class="scope-option"><input type="radio" name="reportScope" id="scope_${k}" value="${k}" ${r.sectionMode===k?'checked':''}><label for="scope_${k}"><strong>${l}</strong><span>${d}</span></label></div>`).join('')}</div>`:`<p class="tiny">${esc(sectionLabel(r.sectionMode))} section reporting scope</p>`}${r.sectionMode==='all'?`<div class="auto-combine-banner"><div><strong>Combined is calculated automatically and cannot be edited</strong><span>Student counts and every grade/status count are added Male + Female. CLO actuals are weighted by completed students. Itqan verifies the arithmetic again before save, submission, approval, PLO calculation, and export.</span></div><span class="tag blue">Calculation locked</span></div>`:''}</div>
      <div class="drawer-section"><div class="drawer-section-head"><h3>Course Learning Outcomes</h3><span class="tiny">Mapping and assessment definition</span></div><div class="clo-master">${(r.clos||[]).map((c,i)=>`<div class="clo-master-row"><span class="cm-code">${esc(c.code)}</span><input data-clo-text="${i}" value="${esc(c.text)}" ${dis}><select data-clo-domain="${i}" ${dis}>${['K','S','V'].map(d=>`<option ${d===c.domain?'selected':''}>${d}</option>`).join('')}</select><input data-clo-method="${i}" value="${esc(c.method||'')}" placeholder="Assessment method" ${dis}><select data-clo-plo="${i}" ${dis}>${state.plos.map(p=>`<option value="${esc(p.code)}" ${p.code===c.plo?'selected':''}>${esc(p.code)}</option>`).join('')}</select><input data-clo-target="${i}" type="number" min="0" max="100" value="${esc(c.target)}" ${dis}></div>`).join('')}</div>${editable?'<button class="btn btn-ghost" id="addClo" style="margin-top:8px">＋ Add CLO</button>':''}</div>
      <div class="drawer-section"><div class="drawer-section-head"><h3>Section results</h3><span class="tiny">All sections can be entered on the same screen</span></div><div class="report-section-stack">${activeSectionKeys(r).map(k=>sectionEditorHtml(r,k,editable)).join('')}</div></div>
      <div class="drawer-section"><div class="drawer-section-head"><h3>Course Improvement Plan</h3><span class="tiny">Generated into report and portfolio</span></div><div id="improvementList">${(r.improvements||[]).map((x,i)=>improvementRowHtml(x,i,editable)).join('')}</div>${editable?'<button class="btn btn-ghost" id="addImprovement">＋ Add improvement action</button>':''}</div>
      <div class="drawer-section"><div class="drawer-section-head"><h3>Approval trail</h3></div><div class="activity">${(r.activity||[]).slice().reverse().map(a=>`<div class="activity-row"><div class="activity-icon">•</div><div><strong>${esc(a.text)}</strong></div><time>${esc(a.date)}</time></div>`).join('')}</div></div>`;
  }

  function sectionEditorHtml(r,key,editable){
    const sec=r.sectionData[key], combinedAuto=key==='combined'&&r.sectionMode==='all'; const dis=editable&&!combinedAuto?'':'disabled';
    const inflation=gradeInflationForSection(sec),inflationReason=inflation.inflated?inflation.reasons.join(' · '):`A+ ${formatPct(inflation.aPlusPct)} · A and above ${formatPct(inflation.aOrAbovePct)}`;
    const combinedInflated=r.sectionMode==='all'&&gradeInflationForSection(expectedCombinedSnapshot(r)).inflated;
    const narrativeRequired=!combinedAuto&&(inflation.inflated||combinedInflated);
    const reqReason=inflation.inflated?'grade inflation detected':'Combined grade inflation detected';
    const reqNote=narrativeRequired?`<span class="inflation-required-note">Required — ${reqReason}</span>`:'';
    const reqClass=narrativeRequired?'inflation-required-field':'';
    return `<div class="report-section-card ${key}"><div class="report-section-head"><div><h4>${esc(sectionLabel(key))} section</h4><p>${combinedAuto?'Calculated automatically from Male + Female':'Enter this section directly'}</p></div>${sectionPill(key)}</div><div class="report-section-body">
      <div class="section-summary-grid"><div class="field"><label>Students starting</label><input type="number" min="0" step="1" data-sec="${key}" data-field="studentsStart" value="${sec.studentsStart}" ${dis}></div><div class="field"><label>Students completed</label><input type="number" min="0" step="1" data-sec="${key}" data-field="studentsComplete" value="${sec.studentsComplete}" ${dis}></div><div class="field"><label>Grade total entered</label><input data-grade-total-sec="${key}" value="${Object.values(sec.grades).reduce((a,b)=>a+(Number(b)||0),0)}" disabled></div></div>${combinedAuto?'<div class="combined-math-note">Verified sum: Combined counts = Male + Female. Example: 20 A+ + 15 A+ = 35 A+.</div>':''}
      <div class="grade-grid">${gradeDefs.map(([label])=>`<label><span>${esc(label)}</span><input type="number" min="0" step="1" data-grade-sec="${key}" data-grade="${esc(label)}" value="${Number(sec.grades[label])||0}" ${dis}></label>`).join('')}</div>
      <div class="grade-inflation-banner ${inflation.inflated?'is-alert':''}" data-inflation-sec="${key}"><div><strong>${inflation.inflated?'Grade inflation detected':'Grade inflation check'}</strong><span>${esc(inflationReason)}${inflation.denominator?` · ${inflation.denominator} letter-graded students`:''}</span></div><span>${inflation.inflated?'Comment + recommendation required':'No inflation detected'}</span></div>
      <div class="section-comment-grid"><div class="field"><label>Comment on student grades <span data-inflation-required-note="${key}">${reqNote}</span></label><textarea data-sec="${key}" data-field="gradeComment" class="${reqClass}" ${dis}>${esc(sec.gradeComment)}</textarea></div><div class="field"><label>Recommendations on grades <span data-inflation-required-note2="${key}">${reqNote}</span></label><textarea data-sec="${key}" data-field="gradeRecommendation" class="${reqClass}" ${dis}>${esc(sec.gradeRecommendation)}</textarea></div><div class="field full"><label>Recommendations on CLOs</label><textarea data-sec="${key}" data-field="cloRecommendation" ${dis}>${esc(sec.cloRecommendation)}</textarea></div></div>
      <div class="section-title mini"><div><h2>CLO results</h2><p>Actual attainment and comment for this section</p></div></div><table class="clo-result-table"><thead><tr><th>CLO</th><th>PLO</th><th>Target</th><th>Actual</th><th>Comment</th></tr></thead><tbody>${(r.clos||[]).map(c=>{const cr=sec.cloResults[c.code]||{};return `<tr><td class="code-cell">${esc(c.code)}</td><td>${esc(c.plo)}</td><td>${esc(c.target)}%</td><td class="actual-cell"><input type="number" min="0" max="100" step="0.1" data-clo-result-sec="${key}" data-clo-code="${esc(c.code)}" data-result-field="actual" value="${esc(cr.actual)}" class="${combinedAuto?'combined-readonly':''}" ${dis}></td><td><input data-clo-result-sec="${key}" data-clo-code="${esc(c.code)}" data-result-field="comment" value="${esc(cr.comment||'')}" class="${combinedAuto?'combined-readonly':''}" ${dis}></td></tr>`}).join('')}</tbody></table>
    </div></div>`;
  }
  function improvementRowHtml(x,i,editable){const dis=editable?'':'disabled';return `<div class="improvement-row"><input data-imp-rec="${i}" placeholder="Recommendation" value="${esc(x.recommendation||'')}" ${dis}><input data-imp-action="${i}" placeholder="Action needed" value="${esc(x.action||'')}" ${dis}><input data-imp-support="${i}" placeholder="Support required" value="${esc(x.support||'')}" ${dis}></div>`}

  function collectReport(r){
    if(!$('rfCode'))return;
    if(canEditReport(r)){
      r.courseCode=$('rfCode').value.trim(); r.courseName=$('rfName').value.trim(); r.academicYear=$('rfYear').value; r.semester=$('rfSemester').value; r.reportDate=$('rfDate').value; r.coordinator=$('rfCoordinator').value.trim();
      const scope=document.querySelector('input[name="reportScope"]:checked'); if(scope)r.sectionMode=scope.value; if(r.sectionMode==='all')r.autoCombine=true;
      document.querySelectorAll('[data-clo-text]').forEach(el=>{const i=Number(el.dataset.cloText);r.clos[i].text=el.value});
      document.querySelectorAll('[data-clo-domain]').forEach(el=>r.clos[Number(el.dataset.cloDomain)].domain=el.value);
      document.querySelectorAll('[data-clo-method]').forEach(el=>r.clos[Number(el.dataset.cloMethod)].method=el.value);
      document.querySelectorAll('[data-clo-plo]').forEach(el=>r.clos[Number(el.dataset.cloPlo)].plo=el.value);
      document.querySelectorAll('[data-clo-target]').forEach(el=>r.clos[Number(el.dataset.cloTarget)].target=Number(el.value)||0);
      document.querySelectorAll('[data-sec][data-field]').forEach(el=>{if(r.sectionMode==='all'&&el.dataset.sec==='combined')return;const s=r.sectionData[el.dataset.sec];if(!s)return;const f=el.dataset.field;s[f]=(f==='studentsStart'||f==='studentsComplete')?Number(el.value)||0:el.value});
      document.querySelectorAll('[data-grade-sec]').forEach(el=>{if(r.sectionMode==='all'&&el.dataset.gradeSec==='combined')return;r.sectionData[el.dataset.gradeSec].grades[el.dataset.grade]=Number(el.value)||0});
      document.querySelectorAll('[data-clo-result-sec]').forEach(el=>{if(r.sectionMode==='all'&&el.dataset.cloResultSec==='combined')return;const sec=r.sectionData[el.dataset.cloResultSec],code=el.dataset.cloCode,field=el.dataset.resultField;if(!sec.cloResults[code])sec.cloResults[code]={actual:'',comment:''};sec.cloResults[code][field]=field==='actual'?(el.value===''?'':Number(el.value)):el.value});
      r.improvements=(r.improvements||[]).map((x,i)=>({recommendation:document.querySelector(`[data-imp-rec="${i}"]`)?.value||x.recommendation||'',action:document.querySelector(`[data-imp-action="${i}"]`)?.value||x.action||'',support:document.querySelector(`[data-imp-support="${i}"]`)?.value||x.support||''}));
      if(r.sectionMode==='all')enforceCombinedIntegrity(r,false); syncFlatFromEffective(r);
    }
  }

  function refreshGradeTotalsUI(r){
    if(!r.sectionData)return;
    ['male','female','combined'].forEach(key=>{const sec=r.sectionData[key];if(!sec)return;const el=document.querySelector(`[data-grade-total-sec="${key}"]`);if(el)el.value=gradeDefs.reduce((sum,[label])=>sum+(Number(sec.grades[label])||0),0);});
  }
  function refreshGradeInflationUI(r){
    if(!r.sectionData)return;
    activeSectionKeys(r).forEach(key=>{
      const sec=r.sectionData[key],info=gradeInflationForSection(sec),combinedAuto=key==='combined'&&r.sectionMode==='all';
      const banner=document.querySelector(`[data-inflation-sec="${key}"]`);
      if(banner){banner.classList.toggle('is-alert',info.inflated);const reason=info.inflated?info.reasons.join(' · '):`A+ ${formatPct(info.aPlusPct)} · A and above ${formatPct(info.aOrAbovePct)}`;banner.innerHTML=`<div><strong>${info.inflated?'Grade inflation detected':'Grade inflation check'}</strong><span>${esc(reason)}${info.denominator?` · ${info.denominator} letter-graded students`:''}</span></div><span>${info.inflated&&!combinedAuto?'Comment + recommendation required':info.inflated?'Derived from source sections':'No inflation detected'}</span>`;}
      const combinedInflated=r.sectionMode==='all'&&gradeInflationForSection(expectedCombinedSnapshot(r)).inflated;
      const required=!combinedAuto&&(info.inflated||combinedInflated);
      const reason=info.inflated?'grade inflation detected':'Combined grade inflation detected';
      const note=`${required?`<span class="inflation-required-note">Required — ${reason}</span>`:''}`;
      const n1=document.querySelector(`[data-inflation-required-note="${key}"]`),n2=document.querySelector(`[data-inflation-required-note2="${key}"]`);if(n1)n1.innerHTML=note;if(n2)n2.innerHTML=note;
      ['gradeComment','gradeRecommendation'].forEach(field=>{const el=document.querySelector(`[data-sec="${key}"][data-field="${field}"]`);if(el)el.classList.toggle('inflation-required-field',required);});
    });
  }

  function refreshCombinedUI(r){
    if(r.sectionMode!=='all')return;
    enforceCombinedIntegrity(r,false);
    const c=r.sectionData.combined;
    const setValue=(selector,value)=>{const el=document.querySelector(selector);if(el)el.value=value??'';};
    // Keep source-section totals visible while typing as well as the derived Combined total.
    refreshGradeTotalsUI(r);
    setValue('[data-sec="combined"][data-field="studentsStart"]',c.studentsStart);
    setValue('[data-sec="combined"][data-field="studentsComplete"]',c.studentsComplete);
    document.querySelectorAll('[data-grade-sec="combined"]').forEach(el=>{el.value=Number(c.grades[el.dataset.grade])||0;});
    document.querySelectorAll('[data-clo-result-sec="combined"]').forEach(el=>{const cr=c.cloResults[el.dataset.cloCode]||{};el.value=el.dataset.resultField==='actual'?(cr.actual??''):(cr.comment||'');});
    setValue('[data-sec="combined"][data-field="gradeComment"]',c.gradeComment);
    setValue('[data-sec="combined"][data-field="gradeRecommendation"]',c.gradeRecommendation);
    setValue('[data-sec="combined"][data-field="cloRecommendation"]',c.cloRecommendation);
    refreshGradeInflationUI(r);
  }

  function validateForSubmission(r){
    collectReport(r);
    return validateReport(r,{ploCodes:state.plos.map(p=>p.code)});
  }

  function bindReportEvents(r,editable,review){
    if(editable){
      document.querySelectorAll('input[name="reportScope"]').forEach(el=>el.addEventListener('change',()=>{collectReport(r);r.sectionMode=el.value;ensureSectionModel(r);saveState();openReport(r.id)}));
      document.querySelectorAll('[data-sec],[data-grade-sec],[data-clo-result-sec]').forEach(el=>el.addEventListener('input',()=>{collectReport(r);refreshGradeTotalsUI(r);if(r.sectionMode==='all')refreshCombinedUI(r);else refreshGradeInflationUI(r);}));
      if($('addClo'))$('addClo').addEventListener('click',()=>{collectReport(r);const idx=(r.clos||[]).length+1;r.clos.push({code:`2.${idx}`,domain:'S',text:'New course learning outcome',plo:state.plos[0]?.code||'',method:'',target:70});['male','female','combined'].forEach(k=>r.sectionData[k].cloResults[r.clos.at(-1).code]={actual:'',comment:''});saveState();openReport(r.id)});
      if($('addImprovement'))$('addImprovement').addEventListener('click',()=>{collectReport(r);r.improvements.push({recommendation:'',action:'',support:''});saveState();openReport(r.id)});
      if($('saveReport'))$('saveReport').addEventListener('click',async()=>{const btn=$('saveReport');if(btn){btn.disabled=true;btn.textContent='Saving…'}try{collectReport(r);if(r.sectionMode==='all')enforceCombinedIntegrity(r);await persistCourseReport(r);saveState();render();toast('Draft saved to Supabase. Combined arithmetic verified.');}catch(e){console.error(e);toast(e?.message||'Could not save the draft.');}finally{if(btn){btn.disabled=false;btn.textContent='Save draft'}}});
      if($('submitReport'))$('submitReport').addEventListener('click',async()=>{const errors=validateForSubmission(r);if(errors.length){toast(`Complete before submission: ${errors.slice(0,3).join(', ')}${errors.length>3?'…':''}`);return;}const btn=$('submitReport');if(btn){btn.disabled=true;btn.textContent='Submitting…'}try{if(r.sectionMode==='all')enforceCombinedIntegrity(r);syncFlatFromEffective(r);if(backendEnabled){await persistCourseReport(r);const updated=await Backend.rpc('submit_course_report',{p_report_id:r.id});Object.assign(r,reportFromDb(updated));}else{r.status='Awaiting Quality Approval';r.submittedAt=nowDate();r.revisionNote='';r.activity=r.activity||[];r.activity.push({text:'Submitted for Coordinator approval',date:nowDate()});state.audit.unshift({icon:'→',title:`${r.courseCode} submitted`,detail:`${periodLabel(r)} is awaiting Coordinator approval.`,time:'Now'});}saveState();hideDrawer();render();toast('Submitted. The report is locked and waiting for Coordinator approval.');}catch(e){toast(e?.message||'Could not submit the Course Report.');}finally{if(btn){btn.disabled=false;btn.textContent='Submit for Quality Approval'}}});
    }
    if(review){
      if($('approveReport'))$('approveReport').addEventListener('click',async()=>{ensureSectionModel(r);if(r.sectionMode==='all')enforceCombinedIntegrity(r);syncFlatFromEffective(r);const errors=validateForSubmission(r);if(errors.length){toast(`Cannot approve: ${errors.slice(0,3).join(', ')}${errors.length>3?'…':''}`);return;}const btn=$('approveReport');if(btn){btn.disabled=true;btn.textContent='Approving…'}try{if(backendEnabled){const updated=await Backend.rpc('review_course_report',{p_report_id:r.id,p_decision:'approve',p_reason:null});Object.assign(r,reportFromDb(updated));await hydrateSharedState();}else{r.status='Approved';r.approvedAt=nowDate();r.approvedBy=currentUserName();r.revisionNote='';r.activity=r.activity||[];r.activity.push({text:`Approved by ${currentUserName()}; released to PLO calculation, APR, generated portfolio, and HOD dashboard`,date:nowDate()});state.audit.unshift({icon:'✓',title:`${r.courseCode} approved`,detail:`${periodLabel(r)} official CLO results released to PLO/APR/HOD.`,time:'Now'});}saveState();hideDrawer();render();toast('Approved. This report now feeds the official PLO calculations and HOD dashboard.');}catch(e){toast(e?.message||'Could not approve the Course Report.');}finally{if(btn){btn.disabled=false;btn.textContent='Approve Course Report'}}});
      if($('returnReport'))$('returnReport').addEventListener('click',()=>openReturnModal(r));
    }
    if($('downloadReport'))$('downloadReport').addEventListener('click',async()=>{const btn=$('downloadReport');btn.disabled=true;btn.textContent='Generating…';try{await downloadCourseReportDocx(r);toast('Course Report generated.');}catch(e){console.error(e);toast(e?.message||'Could not generate the Course Report.');}finally{btn.disabled=false;btn.textContent='Generate DOCX';}});
  }

  function openReturnModal(r){
    $('modalTitle').textContent='Return Course Report for Revision';
    $('modalBody').innerHTML=`<div class="approval-return-box"><p><strong>${esc(r.courseCode)} · ${esc(periodLabel(r))}</strong></p><p>Enter a clear revision reason. The instructor will see this note and can edit/resubmit the report.</p><textarea id="returnReason" placeholder="Example: CLO 2.1 actual attainment does not match the entered assessment result. Please verify and resubmit."></textarea><button class="btn btn-danger" id="confirmReturn" style="width:100%">Return to Instructor</button></div>`;
    showModal();
    $('confirmReturn').addEventListener('click',async()=>{const reason=$('returnReason').value.trim();if(!reason){toast('Enter a revision reason.');return;}const btn=$('confirmReturn');btn.disabled=true;btn.textContent='Returning…';try{if(backendEnabled){const updated=await Backend.rpc('review_course_report',{p_report_id:r.id,p_decision:'return',p_reason:reason});Object.assign(r,reportFromDb(updated));await hydrateSharedState();}else{r.status='Returned for Revision';r.revisionNote=reason;r.activity=r.activity||[];r.activity.push({text:`Returned for revision: ${reason}`,date:nowDate()});state.audit.unshift({icon:'↩',title:`${r.courseCode} returned`,detail:`${periodLabel(r)} returned to instructor for revision.`,time:'Now'});}saveState();hideModal();hideDrawer();render();toast('Returned to the instructor for revision.');}catch(e){toast(e?.message||'Could not return the Course Report.');}finally{btn.disabled=false;btn.textContent='Return to Instructor'}});
  }

  function openNewReport(){
    if(!canCreateReport()){toast('Only the Instructor workspace creates Course Reports.');return;}
    const years=[...new Set([state.program.academicYear,...state.academicYears].filter(Boolean))];
    if(!years.length){toast('Academic year is not configured for this program. Ask the HOD to set it in Program Settings.');return;}
    $('modalTitle').textContent='New Course Report';
    $('modalBody').innerHTML=`<div class="create-report-intro"><strong>1. Select the reporting period first</strong><span>The report is permanently separated by Academic Year + Semester.</span></div><div class="form-grid"><div class="field f6"><label>Academic year *</label><select id="nrYear"><option value="">Select academic year</option>${years.map(y=>`<option ${y===state.program.academicYear?'selected':''}>${esc(y)}</option>`).join('')}</select></div><div class="field f6"><label>Semester *</label><select id="nrSemester"><option value="">Select semester</option><option>S1</option><option>S2</option><option>Summer</option></select></div><div class="field f4"><label>Course code *</label><input id="nrCode" placeholder="e.g. HIM401"></div><div class="field f8"><label>Course title *</label><input id="nrName" placeholder="Course title"></div><div class="field f8"><label>Instructor</label><input id="nrInstructor" value="${esc(currentUserName())}" readonly></div><div class="field f4"><label>Teaching sections</label><input type="number" id="nrSections" value="2" min="1"></div><div class="field f12"><label>Section reporting scope *</label><div class="scope-selector">${[['male','Male','Male section only'],['female','Female','Female section only'],['combined','Combined','Combined result only'],['all','All','Enter Male + Female at once; Combined is calculated automatically']].map(([k,l,d])=>`<div class="scope-option"><input type="radio" name="newSectionScope" id="new_${k}" value="${k}" ${k==='all'?'checked':''}><label for="new_${k}"><strong>${l}</strong><span>${d}</span></label></div>`).join('')}</div></div><div class="field f12"><button class="btn btn-primary" id="createReport" style="width:100%">Create Course Report</button></div></div>`;
    showModal();
    $('createReport').addEventListener('click',async()=>{
      const year=$('nrYear').value,semester=$('nrSemester').value,code=$('nrCode').value.trim(),name=$('nrName').value.trim(),ins=$('nrInstructor').value.trim();
      if(!year||!semester||!code||!name){toast('Academic year, semester, course code, and course title are required.');return;}
      const mode=document.querySelector('input[name="newSectionScope"]:checked')?.value||'all';
      const duplicate=state.reports.some(x=>x.courseCode.toLowerCase()===code.toLowerCase()&&x.academicYear===year&&x.semester===semester&&x.instructor===ins&&x.sectionMode===mode);
      if(duplicate){toast('A report for this course, period, instructor, and scope already exists.');return;}
      const sectionCount=Number($('nrSections').value);if(!Number.isInteger(sectionCount)||sectionCount<1){toast('Teaching sections must be a positive whole number.');return;}
      const r={id:uid(),courseCode:code,courseName:name,academicYear:year,semester,instructor:ins,instructorEmail:currentUser?.email||'',coordinator:ins,sections:sectionCount,sectionMode:mode,autoCombine:true,location:'main',status:'Draft',submittedAt:'',approvedAt:'',approvedBy:'',revisionNote:'',reportDate:nowDate(),clos:[{code:'1.1',domain:'K',text:'Course learning outcome',plo:state.plos[0]?.code||'',method:'',target:70}],improvements:[],activity:[{text:`Draft created for ${semester} ${year}`,date:nowDate()}]};
      r.instructorId=currentUser?.id||'';r.sectionData={male:blankSectionFor(r),female:blankSectionFor(r),combined:blankSectionFor(r)};ensureSectionModel(r);state.reports.push(r);if(!state.academicYears.includes(year))state.academicYears.push(year);try{await persistCourseReport(r);saveState();hideModal();render();openReport(r.id);}catch(e){state.reports=state.reports.filter(x=>x!==r);toast(e?.message||'Could not create the Course Report.');}
    });
  }

  async function loadPrograms(){
    if(!backendEnabled){programDirectory=[];return;}
    try{programDirectory=await Backend.select('academic_programs','select=*&order=created_at.asc')||[];}catch{programDirectory=[];}
  }
  async function loadUsers(){
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


  async function addAuthorizedUser(){
    const isAdmin=state.role==='System Administrator';
    const titlePrefix=normalizeTitlePrefix($('auPrefix')?.value),first=$('auFirst')?.value.trim(),last=$('auLast')?.value.trim(),role=$('auRole')?.value,email=$('auEmail')?.value.trim().toLowerCase();
    const globalSupervisor=isAdmin&&['APU','VDAA'].includes(role);
    const department=globalSupervisor?'System Supervision':isAdmin?$('auDepartment')?.value.trim():(currentUser?.department||state.program.department||'').trim();
    const limitProgramAccess=globalSupervisor?false:!!$('auLimitPrograms')?.checked;
    const programIds=globalSupervisor?[]:(limitProgramAccess?[...document.querySelectorAll('[data-au-program]:checked')].map(el=>el.value):[]);
    const departmentPrograms=globalSupervisor?[]:programDirectory.filter(p=>p.status==='Open'&&p.department===department);
    if(!titlePrefix||!first||!last||(!globalSupervisor&&!department)||!email){toast('Prefix, first name, last name, role, and email are required. Department is required for program roles.');return;}
    if(backendEnabled&&!globalSupervisor&&!departmentPrograms.length){toast('This department has no open academic programs. Add a program first.');return;}
    if(!globalSupervisor&&limitProgramAccess&&!programIds.length){toast('Select at least one academic program or turn off Limit program access.');return;}
    if(!$('auEmail')?.checkValidity()){toast('Enter a valid email address.');return;}
    const allowed=isAdmin?['APU','VDAA','HOD','Coordinator','Instructor']:['Instructor','Coordinator'];if(!allowed.includes(role)){toast('That role is not permitted here.');return;}
    const btn=$('addAuthorizedUser');if(btn){btn.disabled=true;btn.textContent='Adding…'}
    try{
      if(!backendEnabled){const users=loadLocalUsers();if(users.some(u=>String(u.email||'').toLowerCase()===email))throw new Error('This email is already authorized.');users.push({id:uid(),titlePrefix,firstName:first,lastName:last,department,role,email,limitProgramAccess,programIds,active:true,createdAt:nowDate()});saveLocalUsers(users);userDirectory=users;}
      else{await Backend.invoke('admin-create-user',{title_prefix:titlePrefix,first_name:first,last_name:last,department,role,email,limit_program_access:limitProgramAccess,program_ids:programIds});await loadUsers();}
      render();toast(globalSupervisor?'Read-only supervisor added with access to all academic programs.':limitProgramAccess?'User added with limited program access.':'User added with access to all department programs.');
    }catch(e){toast(e?.message||'Could not add user.');}finally{if(btn){btn.disabled=false;btn.textContent='Add / assign user'}}
  }
  async function setUserStatus(userId,active,programId){
    try{await Backend.invoke('admin-manage-user',{action:'status',user_id:userId,active,program_id:programId||activeProgramId});await loadUsers();render();toast(active?'User reactivated.':'User deactivated.');}catch(e){toast(e?.message||'Could not update user.');}
  }
  async function createAcademicProgram(){
    const code=$('apCode')?.value.trim().toUpperCase(),name=$('apName')?.value.trim(),programType=normalizeProgramType($('apProgramType')?.value),institution=$('apInstitution')?.value.trim()||'',college=$('apCollege')?.value.trim()||'',department=$('apDepartment')?.value.trim();
    if(!code||!name||!programType||!department){toast('Department, academic program, program type, and program code are required.');return;}
    if(programDirectory.some(p=>String(p.code||'').trim().toLowerCase()===code.toLowerCase())){toast('That program code already exists.');return;}
    if(programDirectory.some(p=>String(p.name||'').trim().toLowerCase()===name.toLowerCase()&&String(p.department||'').trim().toLowerCase()===department.toLowerCase())){toast('That academic program already exists in this department.');return;}
    const btn=$('createAcademicProgram');btn.disabled=true;btn.textContent='Adding…';
    try{await Backend.insert('academic_programs',{code,name,program_type:programType,institution,college,department,status:'Open',current_academic_year:null,data:{programType},created_by:currentUser.id});await loadPrograms();render();toast('Academic program added. The HOD can now configure its academic years in Program Settings.');}catch(e){toast(e?.message||'Could not create academic program.');}finally{if($('createAcademicProgram')){$('createAcademicProgram').disabled=false;$('createAcademicProgram').textContent='Add academic program';}}
  }
  async function toggleAcademicProgram(id,status){
    const next=status==='Open'?'Closed':'Open';try{await Backend.patch('academic_programs',`id=eq.${encodeURIComponent(id)}`,{status:next});await loadPrograms();render();toast(`Academic program ${next.toLowerCase()}.`);}catch(e){toast(e?.message||'Could not update program.');}
  }
  async function backupAllData(){
    if(!backendEnabled)return;
    const btn=$('backupAllData');if(btn){btn.disabled=true;btn.textContent='Preparing backup…'}
    try{const body=state.role==='System Administrator'?{}:{program_id:activeProgramId};const blob=await Backend.invoke('export-backup-xlsx',body,'blob');const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`Itqan_Backup_${nowDate()}.xlsx`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Excel backup downloaded.');}
    catch(e){toast(e?.message||'Could not export backup.');}
    finally{if(btn){btn.disabled=false;btn.textContent=state.role==='System Administrator'?'Backup Entire System (.xlsx)':'Backup Program (.xlsx)'}}
  }


  function bindViewEvents(){
    bindKpiEvents();
    if($('inflationOnlyCheck')){const applyInflationFilter=()=>{dashboardInflationOnly=$('inflationOnlyCheck').checked;document.querySelectorAll('[data-dashboard-course]').forEach(row=>{row.style.display=!dashboardInflationOnly||row.dataset.inflation==='1'?'':'none';});};$('inflationOnlyCheck').addEventListener('change',applyInflationFilter);applyInflationFilter();}
    document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.go)));
    document.querySelectorAll('[data-new="report"]').forEach(b=>b.addEventListener('click',openNewReport));
    document.querySelectorAll('[data-edit-report]').forEach(b=>b.addEventListener('click',()=>openReport(b.dataset.editReport)));
    document.querySelectorAll('[data-open-portfolio]').forEach(b=>b.addEventListener('click',()=>{currentPortfolioId=b.dataset.openPortfolio;currentView='course-portfolios';render();window.scrollTo({top:0,behavior:'smooth'});}));
    document.querySelectorAll('[data-plo]').forEach(c=>c.addEventListener('click',()=>{activePlo=c.dataset.plo;render();}));
    if($('reportSearch')||$('yearFilter')||$('semesterFilter')||$('statusFilter')){
      const filter=()=>{const q=($('reportSearch')?.value||'').toLowerCase(),y=$('yearFilter')?.value||'',s=$('semesterFilter')?.value||'',st=$('statusFilter')?.value||'';document.querySelectorAll('[data-report-row]').forEach(row=>{row.style.display=(!q||row.dataset.search.includes(q))&&(!y||row.dataset.year===y)&&(!s||row.dataset.semester===s)&&(!st||row.dataset.status===st)?'':'none';});};
      ['reportSearch','yearFilter','semesterFilter','statusFilter'].forEach(id=>$(id)?.addEventListener(id==='reportSearch'?'input':'change',filter));
    }
    if($('periodYear'))$('periodYear').addEventListener('change',()=>{ploYear=$('periodYear').value;activePlo=null;render();});
    if($('periodTerm'))$('periodTerm').addEventListener('change',()=>{ploTerm=$('periodTerm').value;activePlo=null;render();});
    for(const [id,key] of [['supervisorDepartment','department'],['supervisorProgram','program'],['supervisorYear','year'],['supervisorTerm','term'],['supervisorStatus','status'],['supervisorView','view']]){
      $(id)?.addEventListener('change',e=>{supervisorFilters[key]=e.target.value;if(key==='department')supervisorFilters.program='';render();});
    }
    $('supervisorReset')?.addEventListener('click',()=>{supervisorFilters={department:'',program:'',year:ploYear,term:'Annual',status:'',view:'all'};dashboardInflationOnly=false;render();});
    $('supervisorRefresh')?.addEventListener('click',async()=>{const pending=loadSupervisorData();render();await pending;render();});
    document.querySelectorAll('[data-supervisor-report]').forEach(b=>b.addEventListener('click',async()=>{
      if(!isSupervisorRole(state.role))return;
      if(backendEnabled&&b.dataset.program!==activeProgramId)await switchActiveProgram(b.dataset.program);
      if(!backendEnabled||activeProgramId===b.dataset.program)openReport(b.dataset.supervisorReport);
    }));
    document.querySelectorAll('[data-supervisor-workspace]').forEach(b=>b.addEventListener('click',async()=>{await switchActiveProgram(b.dataset.supervisorWorkspace);ploYear=supervisorFilters.year;render();}));
    if($('aprYear'))$('aprYear').addEventListener('change',()=>{ploYear=$('aprYear').value;render();});
    if($('portfolioBack'))$('portfolioBack').addEventListener('click',()=>{currentPortfolioId=null;render();});
    document.querySelectorAll('[data-portfolio-term]').forEach(b=>b.addEventListener('click',()=>{const g=portfolioGroupsForRole().find(x=>x.key===currentPortfolioId);if(!g)return;portfolioActiveTerms.set(g.key,b.dataset.portfolioTerm);render();}));
    document.querySelectorAll('input[data-portfolio-upload]').forEach(input=>input.addEventListener('change',()=>{const g=portfolioGroupsForRole().find(x=>x.key===currentPortfolioId);if(!g||!input.files?.length)return;addPortfolioFiles(g,input.dataset.portfolioUpload,Array.from(input.files));render();toast(`${input.files.length} file${input.files.length===1?'':'s'} added to this portfolio session.`);}));
    document.querySelectorAll('[data-portfolio-clear]').forEach(b=>b.addEventListener('click',()=>{const g=portfolioGroupsForRole().find(x=>x.key===currentPortfolioId);if(!g)return;clearPortfolioFiles(g,b.dataset.portfolioClear);render();toast('Selected files cleared from this portfolio section.');}));
    const runPortfolioDownload=async(btn)=>{const g=portfolioGroupsForRole().find(x=>x.key===currentPortfolioId);if(!g)return;const buttons=[$('downloadPortfolioZip'),$('downloadPortfolioZipBottom')].filter(Boolean);buttons.forEach(x=>{x.disabled=true;x.textContent='Generating…'});try{await downloadCoursePortfolioZip(g);toast('Course Portfolio downloaded. Selected files were placed into their required sections and were not saved by Itqan.');}catch(e){console.error(e);toast(e?.message||'Could not generate Course Portfolio.');}finally{buttons.forEach(x=>{x.disabled=false;x.textContent='Download portfolio ZIP'});}};
    if($('downloadPortfolioZip'))$('downloadPortfolioZip').addEventListener('click',()=>runPortfolioDownload($('downloadPortfolioZip')));
    if($('downloadPortfolioZipBottom'))$('downloadPortfolioZipBottom').addEventListener('click',()=>runPortfolioDownload($('downloadPortfolioZipBottom')));
    if($('exportAprCsv'))$('exportAprCsv').addEventListener('click',exportAprCsv);
    if($('saveSetup'))$('saveSetup').addEventListener('click',async()=>{const current=$('spYear').value.trim();const years=[...new Set($('spYears').value.split(',').map(x=>x.trim()).filter(Boolean))];if(!current){toast('Current academic year is required.');return;}if(!years.includes(current))years.unshift(current);state.program.academicYear=current;state.academicYears=years;ploYear=current;try{await persistProgramSetup();saveState();render();toast('Program Settings saved.');}catch(e){toast(e?.message||'Could not save Program Settings.');}});
    if($('savePloTargets'))$('savePloTargets').addEventListener('click',async()=>{document.querySelectorAll('[data-plo-target]').forEach(el=>state.plos[Number(el.dataset.ploTarget)].target=clamp(el.value));try{await persistPlos();saveState();render();toast('PLO targets saved.');}catch(e){toast(e?.message||'Could not save PLO targets.');}});
    if($('auLimitPrograms')&&$('auDepartment')&&$('auProgramLimitWrap')&&$('auProgramLimitList')){
      const refreshProgramLimitList=()=>{const department=$('auDepartment').value;const programs=programDirectory.filter(p=>p.status==='Open'&&p.department===department);$('auProgramLimitList').innerHTML=programs.map(p=>`<label class="program-access-option"><input type="checkbox" data-au-program value="${esc(p.id)}"><span><strong>${esc(programDirectoryLabel(p))}</strong><small>${esc(programTypeLabel(p))}</small></span></label>`).join('')||'<span class="tiny">No open academic programs in this department.</span>';};
      const syncProgramLimitVisibility=()=>{$('auProgramLimitWrap').classList.toggle('hidden',!$('auLimitPrograms').checked);if($('auLimitPrograms').checked)refreshProgramLimitList();};
      $('auLimitPrograms').addEventListener('change',syncProgramLimitVisibility);$('auDepartment').addEventListener('change',refreshProgramLimitList);refreshProgramLimitList();syncProgramLimitVisibility();
    }
    if($('addAuthorizedUser'))$('addAuthorizedUser').addEventListener('click',addAuthorizedUser);
    if($('backupAllData'))$('backupAllData').addEventListener('click',backupAllData);
    if($('createAcademicProgram'))$('createAcademicProgram').addEventListener('click',createAcademicProgram);
    document.querySelectorAll('[data-program-toggle]').forEach(b=>b.addEventListener('click',()=>toggleAcademicProgram(b.dataset.programToggle,b.dataset.programStatus)));
    document.querySelectorAll('[data-user-status]').forEach(b=>b.addEventListener('click',()=>setUserStatus(b.dataset.userStatus,b.dataset.userActive==='1',b.dataset.userProgram)));
  }

  async function go(view){if(!roleCanView(view)){toast('This page is not available for the current role.');return;}currentView=view;if(view!=='course-portfolios')currentPortfolioId=null;hideDrawer();hideModal();if(view==='users')await loadUsers();render();window.scrollTo({top:0,behavior:'smooth'});}
  function showDrawer(){$('drawer').classList.remove('hidden');$('drawerBackdrop').classList.remove('hidden');document.body.classList.add('no-scroll')}
  function hideDrawer(){$('drawer').classList.add('hidden');$('drawerBackdrop').classList.add('hidden');document.body.classList.remove('no-scroll');currentReportId=null}
  function showModal(){$('modal').classList.remove('hidden');$('modalBackdrop').classList.remove('hidden');document.body.classList.add('no-scroll')}
  function hideModal(){$('modal').classList.add('hidden');$('modalBackdrop').classList.add('hidden');document.body.classList.remove('no-scroll')}

  function toCsv(rows){return rows.map(row=>row.map(v=>`"${String(v??'').replace(/"/g,'""')}"`).join(',')).join('\r\n')}
  function downloadText(name,text,type='text/plain'){const blob=new Blob([text],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
  function exportAprCsv(){const rows=ploRollups(ploYear,'Annual');downloadText(`APR_${safeFileName(ploYear)}.csv`,toCsv([['Program',state.program.name],['Academic Year',ploYear],['Approved Reports',approvedReports(ploYear,'Annual').length],[],['PLO','Target','S1','S2','Summer','Annual','Sources'],...rows.map(p=>[p.code,p.target,...TERMS.map(t=>{const q=ploRollups(ploYear,t).find(x=>x.code===p.code);return q?.actual==null?'':Math.round(q.actual*10)/10}),p.actual==null?'':Math.round(p.actual*10)/10,p.rows.length])]),'text/csv')}

  function safePathComponent(s,fallback='item'){let v=String(s||'').replace(/[–—−]/g,'-').replace(/[\u0000-\u001f\u007f\\/:*?"<>|]+/g,'_').replace(/\s+/g,' ').trim().replace(/^\.+|\.+$/g,'');if(!v||/^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i.test(v))v=`_${v||fallback}`;return v.slice(0,140)}
  function safeFileName(s){return safePathComponent(s,'file').replace(/\s+/g,'_')}
  function addSampleAnswerFolders(zip,base){
    zip.folder(`${base}/Questions with answer key`);
    zip.folder(`${base}/Sample of students answer/Excellent`);
    zip.folder(`${base}/Sample of students answer/Average`);
    zip.folder(`${base}/Sample of students answer/Poor`);
  }
  function addAssessmentStructure(zip,semesterBase){
    const a=`${semesterBase}/Assessments`;
    addSampleAnswerFolders(zip,`${a}/Assignment`);
    ['Final Exam','Midterm Exam'].forEach(exam=>['Clinical','Practical','Theory'].forEach(type=>addSampleAnswerFolders(zip,`${a}/${exam}/${type}`)));
    zip.folder(`${a}/Others`);
  }
  function safeFolderName(s){return safePathComponent(s,'folder')}
  function coursePortfolioBasePath(g){return `${safeFolderName(g.courseCode)}`}
  function semesterPortfolioBase(courseBase,academicYear,term){return `${courseBase}/Year ${safeFolderName(academicYear)}/${semesterFolderName(term)}`}
  function ensureRequiredPortfolioTree(zip,g){
    const courseBase=coursePortfolioBasePath(g);
    zip.folder(`${courseBase}/Course Specification (CS)`);
    zip.folder(`${courseBase}/Teaching Materials (TM)`);
    const instructors=[...new Set(g.reports.map(r=>r.instructor).filter(Boolean))];
    if(instructors.length){instructors.forEach(name=>{const b=`${courseBase}/Instructors/${safeFolderName(name)}`;zip.folder(`${b}/Curriculum Vitae (CV)`);zip.folder(`${b}/Teaching Philosophy (TP)`);});}
    else{zip.folder(`${courseBase}/Instructors`);}
    TERMS.forEach(term=>{
      const semesterBase=semesterPortfolioBase(courseBase,g.academicYear,term);
      addAssessmentStructure(zip,semesterBase);
      zip.folder(`${semesterBase}/Course Report`);
      zip.folder(`${semesterBase}/Reports and Surveys/CLOs Assessment Report`);
      zip.folder(`${semesterBase}/Reports and Surveys/Course Evaluation Survey`);
      zip.folder(`${semesterBase}/Reports and Surveys/Informal feedback`);
    });
    return courseBase;
  }
  function safePortfolioUploadName(name){return safePathComponent(name,'file').slice(0,180)}
  function addPortfolioSessionFiles(zip,g,courseBase){
    const used=new Set();
    for(const [relativePath,files] of portfolioUploadStore(g).entries()){
      files.forEach(file=>{let name=safePortfolioUploadName(file.name),candidate=`${courseBase}/${relativePath}/${name}`,n=2;const dot=name.lastIndexOf('.'),stem=dot>0?name.slice(0,dot):name,ext=dot>0?name.slice(dot):'';while(used.has(candidate)||zip.file(candidate)){name=`${stem} (${n++})${ext}`;candidate=`${courseBase}/${relativePath}/${name}`}used.add(candidate);zip.file(candidate,file);});
    }
  }
  function zipApi(){
    if(!window.JSZip)throw new Error('Export component is missing. Upload vendor/jszip.min.js beside index.html, then refresh Itqan.');
    return window.JSZip;
  }

  async function downloadCoursePortfolioZip(g){
    const approved=portfolioApprovedReports(g);
    const zip=new (zipApi())(); const courseBase=ensureRequiredPortfolioTree(zip,g);addPortfolioSessionFiles(zip,g,courseBase);
    for(const r0 of approved){
      const r=JSON.parse(JSON.stringify(r0));ensureSectionModel(r);if(r.sectionMode==='all')enforceCombinedIntegrity(r);syncFlatFromEffective(r);
      const semesterBase=semesterPortfolioBase(courseBase,g.academicYear,r.semester),keys=activeSectionKeys(r);
      for(const key of keys){
        const v=reportVariant(r,key),bytes=await generateCourseReportBytes(v);
        const name=safeFileName(`${r.courseCode}_${r.semester}_${r.academicYear}_${sectionLabel(key)}_Course_Report`)+'.docx';
        zip.file(`${semesterBase}/Course Report/${name}`,bytes,{binary:true});
      }
      const cloRows=[['Section','CLO','Domain','CLO Description','PLO','Assessment Method','Target','Actual','Comment']];
      for(const key of keys){const v=reportVariant(r,key);(v.clos||[]).forEach(c=>cloRows.push([sectionLabel(key),c.code,c.domain,c.text,c.plo,c.method,c.target,c.actual,c.comment]));}
      const cloName=safeFileName(`${r.courseCode}_${r.semester}_${r.academicYear}_CLOs_Assessment_Report`)+'.csv';
      zip.file(`${semesterBase}/Reports and Surveys/CLOs Assessment Report/${cloName}`,toCsv(cloRows));
    }
    const root=safeFileName(`${g.courseCode}_${g.academicYear}_Course_Portfolio`);
    const blob=await zip.generateAsync({type:'blob',mimeType:'application/zip',compression:'DEFLATE',compressionOptions:{level:6}}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`${root}.zip`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1200);
  }

  function replacePlaceholdersInParagraph(paragraph,ctx){
    const nodes=Array.from(paragraph.getElementsByTagName('w:t'));if(!nodes.length)return;const texts=nodes.map(n=>n.textContent||'');let combined='';const starts=[];texts.forEach(t=>{starts.push(combined.length);combined+=t});const re=/\{\{\s*([A-Za-z0-9_]+)\s*\}\}/g;const matches=[];let m;while((m=re.exec(combined))!==null)matches.push({start:m.index,end:m.index+m[0].length,key:m[1]});for(let mi=matches.length-1;mi>=0;mi--){const match=matches[mi];let si=0,ei=nodes.length-1;for(let i=0;i<nodes.length;i++){const e=starts[i]+texts[i].length;if(match.start>=starts[i]&&match.start<=e){si=i;break}}for(let i=si;i<nodes.length;i++){const e=starts[i]+texts[i].length;if(match.end<=e){ei=i;break}}const sLocal=match.start-starts[si],eLocal=match.end-starts[ei];const prefix=(nodes[si].textContent||'').slice(0,sLocal),suffix=(nodes[ei].textContent||'').slice(eLocal),val=String(ctx[match.key]??'');if(si===ei)nodes[si].textContent=prefix+val+suffix;else{nodes[si].textContent=prefix+val;for(let j=si+1;j<ei;j++)nodes[j].textContent='';nodes[ei].textContent=suffix;}}
  }
  function fillDocumentXml(xml,ctx,location){const parser=new DOMParser();const doc=parser.parseFromString(String(xml).replace(/^\uFEFF/,''),'application/xml');const err=doc.getElementsByTagName('parsererror')[0];if(err)throw new Error('Could not parse Word template XML.');Array.from(doc.getElementsByTagName('w:p')).forEach(p=>replacePlaceholdersInParagraph(p,ctx));const boxes=Array.from(doc.getElementsByTagName('w14:checkbox'));boxes.slice(0,2).forEach((box,i)=>{const checked=(i===0&&location==='main')||(i===1&&location==='branch');const c=box.getElementsByTagName('w14:checked')[0];if(c)c.setAttribute('w14:val',checked?'1':'0');const sdt=box.parentNode?.parentNode,content=sdt?.getElementsByTagName('w:sdtContent')[0],t=content?.getElementsByTagName('w:t')[0];if(t)t.textContent=checked?'☒':'☐'});return new XMLSerializer().serializeToString(doc)}
  const COURSE_REPORT_TEMPLATE_URL = 'templates/Course_Report_Placeholder.docx';
  let templateBufferPromise = null;

  async function getTemplateBuffer() {
    if (!templateBufferPromise) {
      templateBufferPromise = fetch(COURSE_REPORT_TEMPLATE_URL, { cache: 'no-store' })
        .then((response) => {
          if (!response.ok) throw new Error(`Course Report template request failed (${response.status}).`);
          return response.arrayBuffer();
        })
        .catch((error) => {
          templateBufferPromise = null;
          const hint = location.protocol === 'file:'
            ? ' Open Itqan through a web host (for example Acadeloop.com); browsers block this binary template when the page is opened with file://.'
            : '';
          throw new Error(`Could not load ${COURSE_REPORT_TEMPLATE_URL}.${hint}`, { cause: error });
        });
    }
    return (await templateBufferPromise).slice(0);
  }
  function reportContext(r){
    const ctx={course_name:r.courseName,course_code:r.courseCode,department_name:state.program.department,program_name:state.program.name,college_name:state.program.college,institution_name:state.program.institution,academic_year:r.academicYear,semester:`${r.semester} · ${sectionLabel(r.sectionMode||'combined')}`,course_instructor:r.instructor,course_coordinator:r.coordinator||r.instructor,number_of_section:String(r.sections||1),number_of_students_s:String(r.studentsStart||0),number_of_students_w:String(r.studentsComplete||0),report_date:r.reportDate||nowDate(),comment_on_grades:r.gradeComment||'',recommendations_on_grades:r.gradeRecommendation||'',recommendations_on_clo:r.cloRecommendation||''};
    const denom=Number(r.studentsStart)||gradeTotal(r)||1;gradeDefs.forEach(([label,key,pkey])=>{const count=gradeCount(r,label);ctx[key]=String(count);ctx[pkey]=Math.round(count/denom*1000)/10+'%'});
    for(const d of ['k','s','v'])for(let i=1;i<=5;i++){ctx[`${d}${i}`]='';ctx[`plo_${d}${i}`]='';ctx[`assessment_method_${d}${i}`]='';ctx[`target_${d}${i}`]='';ctx[`${d}${i}_actual`]='';ctx[`comment_on_${d}${i}`]=''}
    const groups={K:[],S:[],V:[]};(r.clos||[]).forEach(c=>(groups[c.domain]||groups.K).push(c));for(const D of ['K','S','V'])groups[D].slice(0,5).forEach((c,i)=>{const d=D.toLowerCase(),n=i+1;ctx[`${d}${n}`]=c.text||'';ctx[`plo_${d}${n}`]=c.plo||'';ctx[`assessment_method_${d}${n}`]=c.method||'';ctx[`target_${d}${n}`]=c.target===''?'':`${c.target}%`;ctx[`${d}${n}_actual`]=c.actual===''?'':`${c.actual}%`;ctx[`comment_on_${d}${n}`]=c.comment||''});
    for(let i=1;i<=6;i++){const imp=(r.improvements||[])[i-1]||{};ctx[`improvement_${i}`]=imp.recommendation||'';ctx[`improvement_action_${i}`]=imp.action||'';ctx[`improvement_support_${i}`]=imp.support||''}return ctx;
  }
  async function generateCourseReportBytes(r){const tpl=await getTemplateBuffer(),zip=await zipApi().loadAsync(tpl),xml=await zip.file('word/document.xml').async('string'),filled=fillDocumentXml(xml,reportContext(r),r.location||'main');zip.file('word/document.xml',filled);return await zip.generateAsync({type:'uint8array',compression:'DEFLATE'})}
  async function downloadCourseReportDocx(r){
    ensureSectionModel(r);if(r.sectionMode==='all'){enforceCombinedIntegrity(r);syncFlatFromEffective(r);const zip=new (zipApi())();for(const key of ['male','female','combined']){const v=reportVariant(r,key),bytes=await generateCourseReportBytes(v);zip.file(safeFileName(`${r.courseCode}_${r.semester}_${r.academicYear}_${sectionLabel(key)}_Course_Report`)+'.docx',bytes,{binary:true});}const blob=await zip.generateAsync({type:'blob',mimeType:'application/zip'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=safeFileName(`${r.courseCode}_${r.semester}_${r.academicYear}_All_Section_Course_Reports`)+'.zip';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);return;}
    const v=reportVariant(r,effectiveSectionKey(r)),bytes=await generateCourseReportBytes(v),blob=new Blob([bytes],{type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=safeFileName(`${r.courseCode}_${r.semester}_${r.academicYear}_${sectionLabel(effectiveSectionKey(r))}_Course_Report`)+'.docx';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }

  function setAuthStatus(message,type=''){
    const el=$('authStatus');if(!el)return;el.textContent=message||'';el.className=`auth-status ${type}`.trim();
  }
  function showLoginStep(){
    $('authEmailStep')?.classList.remove('hidden');$('authCodeStep')?.classList.add('hidden');setAuthStatus('');
    if(!backendEnabled&&!Backend?.localTestMode)$('authEmailStep')?.classList.add('hidden');
  }
  function showCodeStep(email){
    $('authEmailStep')?.classList.add('hidden');$('authCodeStep')?.classList.remove('hidden');
    if($('otpEmailLabel'))$('otpEmailLabel').textContent=email;
    if($('loginCode'))$('loginCode').value='';
  }
  async function loadKeepaliveStatus(){
    if(!backendEnabled||currentUser?.role!=='System Administrator'){keepaliveStatus=null;return;}
    try{
      const rows=await Backend.select('project_keepalive','select=id,pinged_at,source&order=pinged_at.desc&limit=1');
      keepaliveStatus=rows?.[0]||null;
    }catch(e){
      console.warn('Could not load project keepalive status',e);
      keepaliveStatus={error:true};
    }
  }

  async function hydrateSharedState(){
    if(!backendEnabled){state=normalizeState(loadState());state.role=currentUser.role;ploYear=state.program.academicYear;ploTerm='Annual';return;}
    await loadPrograms();
    if(currentUser.role==='System Administrator'){
      accessibleProgramIds=[];activeProgramId=null;backendProgramSettingsId=null;const base=clone(seed);base.reports=[];base.operational=[];base.audit=[];state=normalizeState(base);state.role=currentUser.role;ploYear=state.program.academicYear;ploTerm='Annual';return;
    }
    if(isSupervisorRole(currentUser.role)){
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
    const base=clone(seed);base.reports=[];base.operational=[];base.audit=[];base.academicYears=[];base.program={...base.program,academicYear:''};backendProgramSettingsId=null;
    const pid=encodeURIComponent(activeProgramId);
    const [programRows,settingsRows,ploRows,operationalRows,reportRows,kpiDefinitions,kpiYears,kpiPriorities,kpiActions]=await Promise.all([
      Backend.select('academic_programs',`id=eq.${pid}&select=*`),
      Backend.select('program_settings',`program_id=eq.${pid}&is_active=eq.true&select=*&order=updated_at.desc&limit=1`),
      Backend.select('plos',`program_id=eq.${pid}&active=eq.true&select=*&order=code.asc`),
      Backend.select('operational_plans',`program_id=eq.${pid}&select=*&order=updated_at.desc&limit=1`),
      Backend.select('course_reports',`program_id=eq.${pid}&select=*&order=updated_at.desc`),
      ...['kpi_definitions','kpi_years','kpi_priorities','kpi_actions'].map(table=>Backend.select(table,`program_id=eq.${pid}&select=*`))
    ]);
    const pg=programRows?.[0];if(pg){base.program={...base.program,name:pg.name,programType:programTypeLabel(pg),department:pg.department,college:pg.college,institution:pg.institution,academicYear:''};base.academicYears=[];}
    if(settingsRows?.[0]){const row=settingsRows[0];backendProgramSettingsId=row.id;base.program={...base.program,academicYear:String(row.academic_year||row.data?.academicYear||'').trim()};base.academicYears=Array.isArray(row.data?.academicYears)?row.data.academicYears.filter(Boolean):(base.program.academicYear?[base.program.academicYear]:[]);}
    if(ploRows?.length)base.plos=ploRows.map(p=>({code:p.code,name:p.name,target:Number(p.target)}));
    if(operationalRows?.[0]?.data?.items)base.operational=operationalRows[0].data.items;
    Object.assign(base,{kpiDefinitions,kpiYears,kpiPriorities,kpiActions});
    base.reports=(reportRows||[]).map(reportFromDb);
    if(currentUser.role==='Head of Department'){try{const auditRows=await Backend.select('audit_log',`details->>program_id=eq.${pid}&select=*&order=created_at.desc&limit=50`);base.audit=(auditRows||[]).map(a=>({icon:'•',title:a.action,detail:`${a.entity_type}${a.entity_id?` · ${a.entity_id}`:''}`,time:String(a.created_at||'').slice(0,16).replace('T',' ')}));}catch{}}
    state=normalizeState(base);state.role=currentUser.role;ploYear=state.program.academicYear;ploTerm='Annual';
  }

  async function switchActiveProgram(programId){
    if(!backendEnabled||!accessibleProgramIds.includes(programId)||programId===activeProgramId)return;
    const previousProgramId=activeProgramId;
    activeProgramId=programId;currentReportId=null;currentPortfolioId=null;activePlo=null;
    try{await hydrateSharedState();render();toast(`Switched to ${state.program.name}.`);}catch(e){activeProgramId=previousProgramId;toast(e?.message||'Could not switch academic program.');}
  }

  async function onAuthenticated(user){
    const role=canonicalUiRole(user?.role);
    if(!role) throw new Error('Your Itqan account has an unsupported role. Contact the System Administrator.');
    if(role==='System Administrator'&&(!backendEnabled||normalizeLoginEmail(user.email)!==Backend.adminEmail))throw new Error('System Administrator requires verified login as '+Backend.adminEmail+'.');
    if(Backend?.adminOnly&&role!=='System Administrator')throw new Error('This account is not the System Administrator.');
    currentUser={...user,role};state.role=role;
    await hydrateSharedState();
    // Never let stale seed/browser state replace the authenticated Supabase role.
    state.role=role;
    if(['Head of Department','System Administrator'].includes(state.role))await loadUsers();
    if(state.role==='System Administrator')await loadKeepaliveStatus();
    supervisorFilters={department:'',program:'',year:ploYear,term:'Annual',status:'',view:'all'};
    await loadSupervisorData();
    currentView='dashboard';currentPortfolioId=null;activePlo=null;
    $('authScreen')?.classList.add('hidden');$('appShell')?.classList.remove('hidden');
    syncChrome();render();window.__ACADELOOP_READY__=true;
  }
  async function sendOtp(){
    const email=normalizeLoginEmail($('loginUser')?.value);
    if(!validLoginEmail(email)){setAuthStatus('Enter your complete authorized email address.','error');return;}
    const btn=$('signInBtn');btn.disabled=true;btn.textContent='Sending code…';setAuthStatus('');
    try{
      await Backend.requestOtp(email);
      sessionStorage.setItem('acadeloop_pending_email',email);
      showCodeStep(email);
      setAuthStatus('If this is an authorized Itqan account, a six-digit sign-in code has been sent.','ok');
    }
    catch(e){setAuthStatus('Unable to send a sign-in code. Check the email and try again.','error');}
    finally{btn.disabled=false;btn.textContent='Send one-time code';}
  }
  async function verifyLoginCode(){
    const requestedEmail=normalizeLoginEmail(sessionStorage.getItem('acadeloop_pending_email'));
    const code=String($('loginCode')?.value||'').trim();
    if(!validLoginEmail(requestedEmail)){await Backend.signOut();showLoginStep();setAuthStatus('Start a new sign-in with your full authorized email address.','error');return;}
    if(!/^\d{6}$/.test(code)){setAuthStatus('Enter the six-digit code from your email.','error');return;}
    const btn=$('verifyOtpBtn');btn.disabled=true;btn.textContent='Verifying…';
    try{
      const verified=await Backend.verifyOtp(requestedEmail,code);
      const authUser=await Backend.currentAuthUser();
      if(!authUser?.id||normalizeLoginEmail(authUser.email)!==requestedEmail||verified?.user?.id!==authUser.id)throw new Error('Verified identity mismatch.');
      const p=await Backend.profile();
      if(!p||p.active===false||p.id!==authUser.id||normalizeLoginEmail(p.email)!==requestedEmail)throw new Error('This account is not authorized for Itqan.');
      sessionStorage.removeItem('acadeloop_pending_email');
      await onAuthenticated({id:p.id,email:p.email,titlePrefix:normalizeTitlePrefix(p.title_prefix),firstName:p.first_name,lastName:p.last_name,department:p.department,role:dbRoleToUi(p.role),active:p.active,defaultProgramId:p.default_program_id||null,limitProgramAccess:!!p.limit_program_access});
    }
    catch(e){await Backend.signOut();sessionStorage.removeItem('acadeloop_pending_email');showLoginStep();setAuthStatus(e?.message||'The code is invalid or expired.','error');}
    finally{btn.disabled=false;btn.textContent='Verify & sign in';}
  }
  async function signIn(){
    if(backendEnabled)return;
    const login=$('loginUser')?.value.trim();if(!login){setAuthStatus('Enter a test username such as TestHOD, TestI, or TestQ.','error');return;}
    if($('testRolePassword')?.value!=='1313'){setAuthStatus('Incorrect password. Please try again.','error');$('testRolePassword')?.focus();return;}
    const btn=$('signInBtn');btn.disabled=true;btn.textContent='Signing in…';$('testSignInBtn').disabled=true;setAuthStatus('');
    try{const user=localUserByLogin(login);if(!user)throw new Error('Unknown test user. Use TestHOD, TestI, TestQ, TestI2, or an email added by the HOD.');setAuthToken('');$('testRolePassword').value='';await onAuthenticated(user);}
    catch(e){setAuthStatus(e.message||'Unable to sign in.','error');}
    finally{btn.disabled=false;btn.textContent='Sign in';$('testSignInBtn').disabled=false;}
  }
  async function signOut(){
    supervisorData=null;supervisorError='';
    portfolioUploadFiles.clear();portfolioActiveTerms.clear();hideDrawer();hideModal();
    if(Backend?.adminOnly){await Backend.signOut();setAuthToken('');location.assign(location.pathname);return;}
    if($('testRoleSelect'))$('testRoleSelect').value='';
    if($('testRolePassword'))$('testRolePassword').value='';
    $('testPasswordPanel')?.classList.toggle('hidden',!Backend?.localTestMode);
    if(backendEnabled)await Backend.signOut();else setAuthToken('');currentUser=null;userDirectory=[];$('appShell')?.classList.add('hidden');$('authScreen')?.classList.remove('hidden');showLoginStep();if($('loginUser'))$('loginUser').value='';
  }
  async function initAuth(){
    $('signOutBtn')?.addEventListener('click',signOut);
    $('backToRoles')?.addEventListener('click',()=>{Backend.discardSession?.();setAuthToken('');sessionStorage.removeItem('acadeloop_pending_email');location.assign(location.pathname);});
    $('workspaceProgramSelect')?.addEventListener('change',e=>switchActiveProgram(e.target.value));
    if(backendEnabled){
      $('authTestPanel')?.classList.add('hidden');$('authProductionNote')?.classList.remove('hidden');
      const emailInput=$('loginUser'),sendBtn=$('signInBtn'),verifyBtn=$('verifyOtpBtn');
      if(Backend.adminOnly){
        $('authTitle').textContent='System Administrator sign in';
        $('authMessage').textContent='Sign in as '+Backend.adminEmail+' using the one-time code sent to your email.';
        emailInput.value=Backend.adminEmail;emailInput.readOnly=true;
        $('authProductionNote').textContent='Verified System Administrator access. This workspace uses live Itqan data.';
        $('backToRoles')?.classList.remove('hidden');
      }
      if(emailInput)emailInput.disabled=true;if(sendBtn){sendBtn.disabled=true;sendBtn.textContent='Checking session…';}if(verifyBtn)verifyBtn.disabled=true;
      $('signInBtn')?.addEventListener('click',sendOtp);$('verifyOtpBtn')?.addEventListener('click',verifyLoginCode);$('backToEmail')?.addEventListener('click',()=>{sessionStorage.removeItem('acadeloop_pending_email');Backend.discardSession?.();showLoginStep();});
      $('loginUser')?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.currentTarget.disabled)sendOtp()});$('loginCode')?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.currentTarget.disabled)verifyLoginCode()});
      try{
        const p=await Backend.profile();
        if(p?.active){await onAuthenticated({id:p.id,email:p.email,titlePrefix:normalizeTitlePrefix(p.title_prefix),firstName:p.first_name,lastName:p.last_name,department:p.department,role:dbRoleToUi(p.role),active:p.active,defaultProgramId:p.default_program_id||null,limitProgramAccess:!!p.limit_program_access});return;}
        Backend.discardSession?.();
      }catch(e){console.warn('Session restore failed',e);Backend.discardSession?.();}
      sessionStorage.removeItem('acadeloop_pending_email');
      showLoginStep();if(emailInput)emailInput.disabled=false;if(sendBtn){sendBtn.disabled=false;sendBtn.textContent='Send one-time code';}if(verifyBtn)verifyBtn.disabled=false;
      setAuthStatus('Enter your complete authorized Itqan email address.','');return;
    }
    loadLocalUsers();$('authTestPanel')?.classList.remove('hidden');$('authProductionNote')?.classList.add('hidden');
    $('authEyebrow').textContent='Temporary testing access';
    $('authTitle').textContent='Choose a role to explore Itqan';
    $('authMessage').textContent='Select a role and enter its testing password. System Administrator requires verified email login.';
    $('testModeBadge')?.classList.remove('hidden');
    $('localTestControls')?.classList.toggle('hidden',!Backend?.localTestMode);
    $('loginUser').disabled=false;$('loginUser').type='text';$('signInBtn').disabled=false;$('signInBtn').textContent='Sign in';
    $('authEmailStep')?.classList.toggle('hidden',!Backend?.localTestMode);
    $('testPasswordPanel')?.classList.toggle('hidden',!Backend?.localTestMode);
    $('testRoleSelect')?.addEventListener('change',e=>{
      const select=e.currentTarget;
      $('testRolePassword').value='';setAuthStatus('');
      $('loginUser').value=select.value==='admin'?'':select.value;
      $('testPasswordPanel').classList.toggle('hidden',!select.value||select.value==='admin');
      if(select.value==='admin'){setAuthToken('');location.assign(location.pathname+'?login=admin');return;}
      if(select.value)$('testRolePassword').focus();
    });
    $('testSignInBtn')?.addEventListener('click',signIn);
    $('testRolePassword')?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!$('testSignInBtn').disabled){e.preventDefault();signIn();}});
    $('signInBtn')?.addEventListener('click',signIn);$('loginUser')?.addEventListener('keydown',e=>{if(e.key==='Enter')signIn()});
    document.querySelectorAll('[data-test-login]').forEach(btn=>btn.addEventListener('click',()=>{if($('loginUser'))$('loginUser').value=btn.dataset.testLogin||'';signIn();}));
    // Existing passwordless test sessions must not bypass the new entry gate.
    setAuthToken('');
    showLoginStep();setAuthStatus('Test changes stay in this browser. Live university data is not accessed.','ok');
  }

  function setSidebarOpen(open){$('sidebar')?.classList.toggle('open',open);$('sidebarScrim')?.classList.toggle('show',open);$('menuBtn')?.setAttribute('aria-expanded',String(open));}
  document.querySelectorAll('.nav-item[data-view]').forEach(b=>b.addEventListener('click',()=>{setSidebarOpen(false);go(b.dataset.view);}));
  $('quickAdd')?.addEventListener('click',openNewReport); $('drawerClose')?.addEventListener('click',hideDrawer); $('drawerBackdrop')?.addEventListener('click',hideDrawer); $('modalClose')?.addEventListener('click',hideModal); $('modalBackdrop')?.addEventListener('click',hideModal); $('menuBtn')?.addEventListener('click',()=>setSidebarOpen(!$('sidebar').classList.contains('open'))); $('sidebarScrim')?.addEventListener('click',()=>setSidebarOpen(false));
  window.addEventListener('keydown',e=>{if(e.key==='Escape'){hideDrawer();hideModal();}});
  if(!document.documentElement.classList.contains('public-home'))initAuth();
})();

  

