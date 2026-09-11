from pathlib import Path
import json,re

app=Path('src/app.js')
s=app.read_text()

anchor="  const backendEnabled = !!Backend?.enabled;\n"
insert="""  const backendEnabled = !!Backend?.enabled;
  const normalizeLoginEmail = value => String(value||'').trim().toLowerCase();
  const validLoginEmail = value => { const email=normalizeLoginEmail(value); return email.length<=254 && /^[^\\s@]+@[^\\s@]+\\.[^\\s@]{2,}$/u.test(email); };
"""
assert anchor in s
s=s.replace(anchor,insert,1)

send_pattern=r"  async function sendOtp\(\)\{.*?\n  \}\n  async function verifyLoginCode\(\)\{"
send_repl="""  async function sendOtp(){
    const email=normalizeLoginEmail($('loginUser')?.value);
    if(!validLoginEmail(email)){setAuthStatus('Enter your complete authorized email address.','error');return;}
    const btn=$('signInBtn');btn.disabled=true;btn.textContent='Sending code…';setAuthStatus('');
    try{
      await Backend.requestOtp(email);
      sessionStorage.setItem('acadeloop_pending_email',email);
      showCodeStep(email);
      setAuthStatus('If this is an authorized Acadeloop account, a six-digit sign-in code has been sent.','ok');
    }
    catch(e){setAuthStatus('Unable to send a sign-in code. Check the email and try again.','error');}
    finally{btn.disabled=false;btn.textContent='Send one-time code';}
  }
  async function verifyLoginCode(){"""
s,n=re.subn(send_pattern,send_repl,s,count=1,flags=re.S);assert n==1,n

verify_pattern=r"  async function verifyLoginCode\(\)\{.*?\n  \}\n  async function signIn\(\)\{"
verify_repl="""  async function verifyLoginCode(){
    const requestedEmail=normalizeLoginEmail(sessionStorage.getItem('acadeloop_pending_email'));
    const code=String($('loginCode')?.value||'').trim();
    if(!validLoginEmail(requestedEmail)){await Backend.signOut();showLoginStep();setAuthStatus('Start a new sign-in with your full authorized email address.','error');return;}
    if(!/^\\d{6}$/.test(code)){setAuthStatus('Enter the six-digit code from your email.','error');return;}
    const btn=$('verifyOtpBtn');btn.disabled=true;btn.textContent='Verifying…';
    try{
      const verified=await Backend.verifyOtp(requestedEmail,code);
      const authUser=await Backend.currentAuthUser();
      if(!authUser?.id||normalizeLoginEmail(authUser.email)!==requestedEmail||verified?.user?.id!==authUser.id)throw new Error('Verified identity mismatch.');
      const p=await Backend.profile();
      if(!p||p.active===false||p.id!==authUser.id||normalizeLoginEmail(p.email)!==requestedEmail)throw new Error('This account is not authorized for Acadeloop.');
      sessionStorage.removeItem('acadeloop_pending_email');
      await onAuthenticated({id:p.id,email:p.email,titlePrefix:normalizeTitlePrefix(p.title_prefix),firstName:p.first_name,lastName:p.last_name,department:p.department,role:dbRoleToUi(p.role),active:p.active,defaultProgramId:p.default_program_id||null,limitProgramAccess:!!p.limit_program_access});
    }
    catch(e){await Backend.signOut();sessionStorage.removeItem('acadeloop_pending_email');showLoginStep();setAuthStatus(e?.message||'The code is invalid or expired.','error');}
    finally{btn.disabled=false;btn.textContent='Verify & sign in';}
  }
  async function signIn(){"""
s,n=re.subn(verify_pattern,verify_repl,s,count=1,flags=re.S);assert n==1,n

# Replace production portion of initAuth so the visible login form cannot race session restoration.
old="""    if(backendEnabled){
      $('authTestPanel')?.classList.add('hidden');$('authProductionNote')?.classList.remove('hidden');
      $('signInBtn')?.addEventListener('click',sendOtp);$('verifyOtpBtn')?.addEventListener('click',verifyLoginCode);$('backToEmail')?.addEventListener('click',showLoginStep);
      $('loginUser')?.addEventListener('keydown',e=>{if(e.key==='Enter')sendOtp()});$('loginCode')?.addEventListener('keydown',e=>{if(e.key==='Enter')verifyLoginCode()});
      try{const p=await Backend.profile();if(p?.active){await onAuthenticated({id:p.id,email:p.email,titlePrefix:normalizeTitlePrefix(p.title_prefix),firstName:p.first_name,lastName:p.last_name,department:p.department,role:dbRoleToUi(p.role),active:p.active,defaultProgramId:p.default_program_id||null,limitProgramAccess:!!p.limit_program_access});return;}}catch(e){console.warn('Session restore failed',e);}
      showLoginStep();setAuthStatus('Enter your authorized Acadeloop email address. You may receive a six-digit code or a secure sign-in link.','');return;
    }
"""
new="""    if(backendEnabled){
      $('authTestPanel')?.classList.add('hidden');$('authProductionNote')?.classList.remove('hidden');
      const emailInput=$('loginUser'),sendBtn=$('signInBtn'),verifyBtn=$('verifyOtpBtn');
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
      setAuthStatus('Enter your complete authorized Acadeloop email address.','');return;
    }
"""
assert old in s
s=s.replace(old,new,1)
app.write_text(s)

# Disable controls at first paint until production session restoration finishes.
html=Path('index.source.html')
h=html.read_text()
h,n=re.subn(r'(<input[^>]*id="loginUser"[^>]*)(>)',lambda m:m.group(1) if ' disabled' in m.group(1) else m.group(1)+' disabled'+m.group(2),h,count=1)
# Previous lambda needs complete tag if already disabled.
if n:
    # normalize if replacement omitted close due already disabled branch
    h=h.replace('id="loginUser" disabled\n','id="loginUser" disabled>\n') if 'id="loginUser" disabled\n' in h else h
# Safer direct attribute upgrades.
h=h.replace('id="loginUser" type="email"','id="loginUser" type="email" maxlength="254" autocomplete="email" autocapitalize="none" spellcheck="false"')
h=h.replace('id="signInBtn"','id="signInBtn" disabled',1) if 'id="signInBtn" disabled' not in h else h
html.write_text(h)

# Version + changelog.
p=Path('package.json');data=json.loads(p.read_text());data['version']='1.2.7';data['scripts']['test:security']='node --test tests/security.test.js';data['scripts']['test']='npm run build && npm run test:core && npm run test:security && npm run check && npm run test:browser';p.write_text(json.dumps(data,indent=2)+'\n')

Path('tests/security.test.js').write_text(r'''const test=require('node:test');
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
  for(const text of [backend,app,html]){
    assert.doesNotMatch(text,/SUPABASE_SERVICE_ROLE_KEY|sb_secret_|service_role/i);
  }
});
''')

ch=Path('CHANGELOG.md');c=ch.read_text();entry='''### 1.2.7 — Authentication and authorization hardening\n- Fixed login/session restoration race that could open a previously authenticated administrator session while the login form was visible.\n- Moved production Supabase credentials from persistent localStorage to tab-scoped sessionStorage and invalidated the legacy browser token store.\n- Added strict full-email and six-digit OTP validation plus exact Auth-user/profile/email binding.\n- Added a 12-hour client session ceiling and no-store requests for authenticated traffic.\n- Hardened database grants/RLS and removed legacy cross-program Operational Plan policies.\n- Moved privileged SECURITY DEFINER implementations out of the exposed public schema.\n- Added automated authentication security regression tests.\n\n'''
assert '# Changelog\n' in c
ch.write_text(c.replace('# Changelog\n','# Changelog\n\n'+entry,1))
