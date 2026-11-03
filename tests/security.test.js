const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const backend=fs.readFileSync('src/backend.js','utf8');
const app=fs.readFileSync('src/app.js','utf8');
const html=fs.readFileSync('index.source.html','utf8');
const vm=require('node:vm');

function hostedBackend(enabled, search='', response){
  const stored=new Map();
  let requests=0;
  const context={window:{},URLSearchParams,location:{protocol:'https:',hostname:'acadeloop.com',hash:'',search},
    sessionStorage:{getItem:k=>stored.get(k)||null,setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)},
    localStorage:{removeItem(){}},fetch:async()=>{requests++;if(response)return response();throw new Error('Unexpected network request');}};
  vm.runInNewContext(backend.replace('const TEMPORARY_ROLE_LOGIN = true;',`const TEMPORARY_ROLE_LOGIN = ${enabled};`),context);
  return {api:context.window.AcadeloopBackend,stored,requests:()=>requests};
}

test('hosted role testing cannot use an existing live session or send backend requests',async()=>{
  const {api,stored,requests}=hostedBackend(true);
  stored.set('acadeloop_supabase_session_v2',JSON.stringify({access_token:'existing-token',refresh_token:'existing-refresh',client_started_at:Date.now(),expires_at:Math.floor(Date.now()/1000)+3600}));
  assert.equal(api.enabled,false);
  assert.equal(api.localTestMode,false);
  assert.equal(await api.accessToken(),'');
  await assert.rejects(api.select('profiles'),/session has expired/);
  await assert.rejects(api.invoke('admin-create-user',{}),/session has expired/);
  await assert.rejects(api.requestOtp('test@example.edu'),/sample data only/);
  assert.equal(requests(),0);
});
test('turning off temporary role login restores hosted Supabase authentication',()=>{
  const {api}=hostedBackend(false);
  assert.equal(api.enabled,true);
  assert.equal(api.testMode,false);
  assert.equal(api.temporaryRoleLogin,false);
});

test('production auth tokens are session-only and legacy persistent token is cleared',()=>{
  assert.match(backend,/sessionStorage\.setItem\(SESSION_KEY/);
  assert.doesNotMatch(backend,/localStorage\.setItem\(SESSION_KEY/);
  assert.match(backend,/localStorage\.removeItem\(key\)/);
});
test('OTP does not create users and exact identity is verified',()=>{
  assert.match(backend,/create_user:\s*false/);
  assert.match(backend,/sessionEmail !== email/);
  assert.match(app,/normalizeLoginEmail\(authUser\.email\)!==requestedEmail/);
  assert.match(app,/p\.id!==authUser\.id/);
});
test('login validates complete email and six digit OTP',()=>{
  assert.match(app,/validLoginEmail\(email\)/);
  assert.match(app,/\\d\{6\}/);
  assert.match(html,/id="loginUser"[^>]*disabled/);
});
test('production cannot silently enter preset test mode from an empty hostname',()=>{
  assert.doesNotMatch(backend,/TEST_HOSTS\s*=\s*new Set\(\[''/);
  assert.match(backend,/window\.__ACADELOOP_TEST_MODE__/);
});
test('frontend contains no Supabase service role or secret key',()=>{
  for(const text of [backend,app,html]) assert.doesNotMatch(text,/SUPABASE_SERVICE_ROLE_KEY|sb_secret_|service_role/i);
});


test('administrator route enables real authentication and rejects other email addresses',async()=>{
  const {api,requests}=hostedBackend(true,'?login=admin');
  assert.equal(api.enabled,true);
  assert.equal(api.adminOnly,true);
  assert.equal(api.adminEmail,'rafedmoha@gmail.com');
  await assert.rejects(api.requestOtp('other@example.edu'),/restricted/);
  await assert.rejects(api.verifyOtp('other@example.edu','123456'),/restricted/);
  assert.equal(requests(),0);
  await assert.rejects(api.requestOtp('rafedmoha@gmail.com'),/Unexpected network request/);
  assert.equal(requests(),1);
});
test('administrator presets are removed and saved test administrator roles are rejected',()=>{
  assert.doesNotMatch(app,/username:'TestSA'/);
  assert.match(app,/canonicalUiRole\(u.role\)!=='System Administrator'/);
  assert.match(app,/role==='System Administrator'&&\(!backendEnabled/);
  assert.match(html,/<option value="admin">System Administrator/);
});

test('administrator session requires the matching active SystemAdmin profile',async()=>{
  for(const [email,role,active,allowed] of [
    ['rafedmoha@gmail.com','SystemAdmin',true,true],
    ['other@example.edu','SystemAdmin',true,false],
    ['rafedmoha@gmail.com','Instructor',true,false],
    ['rafedmoha@gmail.com','SystemAdmin',false,false]
  ]){
    let call=0;
    const {api,stored}=hostedBackend(true,'?login=admin',()=>({ok:true,status:200,text:async()=>JSON.stringify(call++===0?{id:'verified-user',email}:[{id:'verified-user',email,role,active}])}));
    stored.set('acadeloop_supabase_session_v2',JSON.stringify({access_token:'test-token',client_started_at:Date.now(),expires_at:Math.floor(Date.now()/1000)+3600}));
    assert.equal(!!(await api.profile()),allowed,`${email} ${role} ${active}`);
    if(!allowed)assert.equal(api.session(),null);
  }
});

test('every sample role requires the shared password before authentication', async () => {
  const source = app;
  const signInSource=source.slice(source.indexOf('  async function signIn(){'),source.indexOf('  async function signOut(){'));
  for(const login of ['TestHOD','TestQ','TestI','TestAPU','TestVDAA']){
    const elements={loginUser:{value:login},testRolePassword:{value:'',focus(){}},signInBtn:{},testSignInBtn:{}};
    let authenticated=0,status='';
    const context={backendEnabled:false,$:id=>elements[id],setAuthStatus:msg=>{status=msg;},localUserByLogin:value=>({username:value}),setAuthToken:()=>{},onAuthenticated:async()=>{authenticated++;}};
    vm.createContext(context);vm.runInContext(signInSource+'\nthis.runSignIn=signIn;',context);
    await context.runSignIn();assert.equal(authenticated,0);
    elements.testRolePassword.value='wrong';await context.runSignIn();assert.equal(authenticated,0);assert.match(status,/Incorrect password/);
    elements.testRolePassword.value='1313';await context.runSignIn();assert.equal(authenticated,1);assert.equal(elements.testRolePassword.value,'');
  }
  assert.ok(!source.includes('const savedLogin=authToken()'),'Legacy passwordless session must not restore automatically');
});

function supervisorHarness(role='APU',enabled=false){
  const c={supervisorData:null,supervisorError:'',currentUser:{role},backendEnabled:enabled,
    state:{program:{name:'Sample',department:'Health'},reports:[{id:'r'}],plos:[],academicYears:['2026–2027']},
    isSupervisorRole:r=>['APU','VDAA'].includes(r),programDirectory:[{id:'p'}],accessibleProgramIds:['p'],reportFromDb:r=>r,
    Backend:{select:async()=>{throw Error('No sample network calls allowed');}}};
  const start=app.indexOf('  async function loadSupervisorData()');
  vm.runInNewContext(app.slice(start,app.indexOf('  function renderSupervisorDashboard()',start)),c);
  return c;
}
test('APU and VDAA sample dashboards stay isolated from the backend',async()=>{
  for(const role of ['APU','VDAA']){const c=supervisorHarness(role);await c.loadSupervisorData();assert.equal(c.supervisorData.programs.length,1);assert.equal(c.supervisorData.reports[0].programId,'sample-program');}
  const c=supervisorHarness('Instructor');await c.loadSupervisorData();assert.equal(c.supervisorData,null);
});
test('supervisor loader paginates and does not present partial totals on failure',async()=>{
  const c=supervisorHarness('APU',true),calls=[];
  c.Backend.select=async(table,query)=>{calls.push([table,query]);const offset=Number(new URLSearchParams(query).get('offset'));return offset===0?[{id:'one',program_id:'p',academic_year:'2026–2027'}]:[];};
  await c.loadSupervisorData();assert.equal(c.supervisorData.reports.length,1);assert.equal(calls.length,6);
  assert.ok(calls.every(([,q])=>q.includes('order=id.asc&limit=500')));
  c.Backend.select=async()=>{throw Error('Unavailable');};await c.loadSupervisorData();assert.equal(c.supervisorData,null);assert.match(c.supervisorError,/incomplete totals/);
});
test('supervisor dashboard renders filters, empty results and chosen sections for both roles',()=>{
  for(const role of ['APU','VDAA']){
    const c=supervisorHarness(role);Object.assign(c,{Core:require('../src/core.js'),TERMS:['S1','S2','Summer'],ploYear:'2026–2027',activeProgramId:null,
      supervisorFilters:{department:'',program:'',year:'2026–2027',term:'Annual',status:'',view:'reports'},
      supervisorData:{programs:[{id:'p',name:'Health',code:'H',department:'Health'}],reports:[],plos:[],years:['2026–2027']},
      esc:v=>String(v??''),uniqueDepartments:ps=>[...new Set(ps.map(p=>p.department))],programDirectoryLabel:p=>p.name,
      dashboardQualitySection:()=>{throw Error('Hidden performance section rendered');},dashboardKpis:()=>'',periodPill:()=>'',statusPill:()=>''});
    c.state.role=role;
    const start=app.indexOf('  function renderSupervisorDashboard()');vm.runInNewContext(app.slice(start,app.indexOf('  function renderDashboard()',start)),c);
    const html=c.renderSupervisorDashboard();assert.match(html,/All departments/);assert.match(html,/All programs/);assert.match(html,/supervisorStatus/);assert.match(html,/No reports match these filters/);assert.doesNotMatch(html,/<h2>Program overview/);
  }
});

test('public homepage and login routes remain separate without changing authentication',()=>{
  const route=html.match(/<script>(if\(!new URLSearchParams[\s\S]*?)<\/script>/)[1];
  for(const [search,expected] of [['',true],['?login=1',false],['?login=admin',false],['?campaign=demo',true]]){
    const classes=new Set();const root={classList:{add:c=>classes.add(c)}};
    vm.runInNewContext(route,{URLSearchParams,location:{search,protocol:'https:',hostname:'acadeloop.com'},document:{documentElement:root}});
    assert.equal(classes.has('public-home'),expected);
    if(expected){assert.equal(root.lang,'ar');assert.equal(root.dir,'rtl');}
  }
  const home=fs.readFileSync('src/home.html','utf8');
  assert.match(home,/href="\?login=1"/);assert.match(home,/mailto:acadeloop@gmail.com/);
  assert.match(home,/تصور توضيحي/);assert.match(home,/ليست جهة اعتماد/);
});
