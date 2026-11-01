/* Run in a browser after the built application loads (isolated sample workspace). */
(async()=>{
 const results=[], $=id=>document.getElementById(id),sleep=ms=>new Promise(r=>setTimeout(r,ms));
 const assert=(v,m)=>{if(!v)throw new Error(m);results.push(m);};
 const wait=async f=>{for(let i=0;i<100;i++){if(f())return;await Promise.resolve();}throw new Error('Timed out waiting for UI');};
 const change=(id,v)=>{$(id).value=v;$(id).dispatchEvent(new Event('change',{bubbles:true}));};
 const submit=async()=>{$('kpiForm').requestSubmit();await wait(()=>!$('saveKpi')||!$('saveKpi').disabled);if($('kpiError')?.textContent)throw new Error($('kpiError').textContent);};
 const open=()=>document.querySelector('[data-view="kpis"]').click();
 const login=async role=>{change('testRoleSelect',role);await wait(()=>!$('appShell').classList.contains('hidden'));open();};
 try{
 await wait(()=>$('testRoleSelect')&&!$('testRoleSelect').disabled);
 await login('TestHOD');assert(!!$('newKpi'),'HOD can create KPIs');
 $('newKpi').click();await wait(()=>$('kOwner'));
 $('kCode').value='KPI-TEST';$('kName').value='Student success';change('kCategory','Quality');change('kOwner','test-q');await submit();
 assert(document.querySelector('.kpi-card').textContent.includes('Quality'),'KPI owner category displayed');
 const editYear=()=>document.querySelector('[data-kpi-year]').click();
 editYear();$('kb_actual').value='85';$('kb_target').value='80';$('kb_external').value='82';$('kb_new_target').value='90';$('kStrengths').value='Strong outcomes';$('kWeaknesses').value='Uneven results';$('kComparisons').value='Above external benchmark';await submit();
 change('kpiYear','2025–2026');editYear();$('kb_actual').value='0';await submit();
 change('kpiYear','2024–2025');editYear();$('kb_actual').value='70';await submit();
 change('kpiYear','2026–2027');editYear();assert($('kb_internal').readOnly&&$('kb_internal').value==='0','Previous actual zero automatically becomes read-only internal benchmark');await submit();
 const bars=[...document.querySelectorAll('.kpi-bar-column>strong')].map(n=>n.textContent);
 assert(bars.join(',')==='70,0,85','Chart displays only actual values for three consecutive years');
 document.querySelector('[data-kpi-priority-new]').click();$('kPriority').value='Improve student support';await submit();
 assert(!document.querySelector('[data-kpi-action]'),'HOD cannot edit another owner’s action plan');
 $('signOutBtn').click();await wait(()=>!$('authScreen').classList.contains('hidden'));await login('TestQ');
 assert(!$('newKpi')&&!document.querySelector('[data-kpi-year]'),'Coordinator cannot edit KPI definitions or benchmarks');
 document.querySelector('[data-kpi-action]').click();assert($('kActionTarget').value==='90','Owner receives suggested KPI new target');
 $('kActions').value='Run support workshops';$('kResponsible').value='Academic committee';$('kStart').value='2026-11-01';$('kEnd').value='2026-12-01';$('kActionTarget').value='92';await submit();
 assert(document.querySelector('.kpi-table-wrap').textContent.includes('Run support workshops'),'Owner action plan saved in linked priorities table');
 $('signOutBtn').click();await wait(()=>!$('authScreen').classList.contains('hidden'));await login('TestI');
 assert(!document.querySelector('[data-kpi-action]'),'Unassigned instructor cannot edit owner action plan');
 $('signOutBtn').click();await wait(()=>!$('authScreen').classList.contains('hidden'));await login('TestAPU');
 assert(!$('newKpi')&&!document.querySelector('[data-kpi-action]'),'APU sees read-only KPI and action plan');
 const out=document.createElement('pre');out.id='kpi-test-result';out.textContent=JSON.stringify({passed:true,results});document.body.append(out);
 }catch(error){const out=document.createElement('pre');out.id='kpi-test-result';out.textContent=JSON.stringify({passed:false,error:error.stack,results});document.body.append(out);}
})();
