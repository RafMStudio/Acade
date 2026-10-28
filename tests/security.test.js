const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const backend=fs.readFileSync('src/backend.js','utf8');
const app=fs.readFileSync('src/app.js','utf8');
const html=fs.readFileSync('index.source.html','utf8');
const vm=require('node:vm');

function hostedBackend(enabled){
  const stored=new Map();
  let requests=0;
  const context={window:{},location:{protocol:'https:',hostname:'acadeloop.com',hash:''},
    sessionStorage:{getItem:k=>stored.get(k)||null,setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)},
    localStorage:{removeItem(){}},fetch:async()=>{requests++;throw new Error('Unexpected network request');}};
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

