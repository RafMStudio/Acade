(async()=>{
 const $=id=>document.getElementById(id),results=[];
 const check=(v,m)=>{if(!v)throw Error(m);results.push(m);};
 const settle=async()=>{for(let i=0;i<30;i++)await Promise.resolve();};
 const select=role=>{$('testRoleSelect').value=role;$('testRoleSelect').dispatchEvent(new Event('change',{bubbles:true}));};
 try{
 for(const role of ['TestHOD','TestQ','TestI','TestAPU','TestVDAA']){
  select(role);check($('appShell').classList.contains('hidden'),role+': selection alone does not log in');
  $('testSignInBtn').click();await settle();check($('appShell').classList.contains('hidden'),role+': blank password denied');
  $('testRolePassword').value='wrong';$('testSignInBtn').click();await settle();check($('appShell').classList.contains('hidden')&&$('authStatus').textContent.includes('Incorrect password'),role+': incorrect password denied');
  $('testRolePassword').value='1313';$('testSignInBtn').click();await settle();check(!$('appShell').classList.contains('hidden'),role+': correct password accepted');
  check($('testRolePassword').value==='',role+': password cleared after login');
  $('signOutBtn').click();await settle();check(!$('authScreen').classList.contains('hidden')&&$('testRolePassword').value==='',role+': sign out resets login');
 }
 select('TestHOD');$('testRolePassword').value='1313';select('TestQ');check($('testRolePassword').value==='','Changing roles clears the password');
 const out=document.createElement('pre');out.id='password-test-result';out.textContent=JSON.stringify({passed:true,checks:results.length});document.body.append(out);
 }catch(e){const out=document.createElement('pre');out.id='password-test-result';out.textContent=JSON.stringify({passed:false,error:e.stack,results});document.body.append(out);}
})();
