const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const backend=fs.readFileSync('src/backend.js','utf8');
const app=fs.readFileSync('src/app.js','utf8');
const html=fs.readFileSync('index.source.html','utf8');

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
