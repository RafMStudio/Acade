'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const backend=fs.readFileSync('src/backend.js','utf8');
const app=fs.readFileSync('src/app.js','utf8');
const html=fs.readFileSync('index.source.html','utf8');
function boot(search=''){
 const stored=new Map(),requests=[];
 const context={window:{},URLSearchParams,location:{protocol:'https:',hostname:'eduitqan.com',hash:'',search},sessionStorage:{getItem:k=>stored.get(k)||null,setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)},localStorage:{removeItem(){}},fetch:async(url,options)=>{requests.push({url,options});throw Error('Network unavailable in test');}};
 vm.runInNewContext(backend,context);
 return {api:context.window.EduItqanBackend,requests};
}
test('hosted login always uses the production backend',async()=>{
 for(const path of ['', '?login=1', '?login=admin']){
  const {api,requests}=boot(path);
  assert.equal(api.enabled,true);assert.equal(api.testMode,false);assert.equal(api.localTestMode,false);
  assert.equal(await api.accessToken(),'');await assert.rejects(api.select('profiles'),/session has expired/);
  assert.equal(requests.length,0);
 }
});
test('OTP uses authorized existing accounts without signing in sample identities',async()=>{
 const {api,requests}=boot();
 await assert.rejects(api.requestOtp('invalid'),/valid email/);
 await assert.rejects(api.verifyOtp('user@example.org','invalid'),/six-digit/);
 await assert.rejects(api.requestOtp('user@example.org'),/Network unavailable/);
 assert.equal(JSON.parse(requests[0].options.body).create_user,false);
});
test('sample role password and frontend test accounts are absent',()=>{
 assert.doesNotMatch(backend,/TEMPORARY_ROLE_LOGIN|__EDUITQAN_TEST_MODE__/);
 assert.doesNotMatch(app,/testRolePassword|defaultTestUsers|TestHOD|TestI2|TestAPU|TestVDAA/);
 assert.doesNotMatch(html,/testSignInBtn|testRolePassword|testRoleSelect|TestHOD/);
 for(const source of [backend,app,html])assert.doesNotMatch(source,/1(?:3)1(?:3)/);
});
test('verified matching identity and authorized profile are required',()=>{
 assert.match(backend,/normalizeEmail\(profile.email\) !== normalizeEmail\(user.email\)/);
 assert.match(app,/p\.id!==authUser\.id/);
 assert.match(app,/p\.active===false/);
 for(const source of [backend,app,html])assert.doesNotMatch(source,/sb_secret_|SUPABASE_SERVICE_ROLE_KEY/);
});
test('source branding is consistent',()=>{
 for(const source of [backend,app,html])assert.doesNotMatch(source,/acade.?loop|أكاديلوب/i);
 assert.match(html,/EduItqan/);
});
