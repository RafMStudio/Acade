from pathlib import Path

root=Path('.')
app_path=root/'src/app.js'
app=app_path.read_text()

old="""  let currentUser = null;\n  let userDirectory = [];\n"""
new="""  let currentUser = null;\n  let userDirectory = [];\n  let keepaliveStatus = null;\n"""
assert old in app
app=app.replace(old,new,1)

marker="""  async function hydrateSharedState(){\n"""
insert="""  async function loadKeepaliveStatus(){\n    if(!backendEnabled||currentUser?.role!=='System Administrator'){keepaliveStatus=null;return;}\n    try{\n      const rows=await Backend.select('project_keepalive','select=id,pinged_at,source&order=pinged_at.desc&limit=1');\n      keepaliveStatus=rows?.[0]||null;\n    }catch(e){\n      console.warn('Could not load project keepalive status',e);\n      keepaliveStatus={error:true};\n    }\n  }\n\n"""
assert marker in app
app=app.replace(marker,insert+marker,1)

old="""    if(['Head of Department','System Administrator'].includes(state.role))await loadUsers();\n    currentView='dashboard';currentPortfolioId=null;activePlo=null;\n"""
new="""    if(['Head of Department','System Administrator'].includes(state.role))await loadUsers();\n    if(state.role==='System Administrator')await loadKeepaliveStatus();\n    currentView='dashboard';currentPortfolioId=null;activePlo=null;\n"""
assert old in app
app=app.replace(old,new,1)

start=app.index('  function renderSystemAdminDashboard(){')
end=app.index('\n  function renderUsers(){',start)
block=app[start:end]
old_return="""    return roleHero()+pageHead('Platform control','Acadeloop Administration','System-wide control for academic programs and authorized users.',backendEnabled?'<button class=\"btn btn-ghost\" id=\"backupAllData\">Backup Entire System (.xlsx)</button>':'')+`\n      <div class=\"grid grid-4\"><div class=\"card metric\"><div class=\"label\">Academic programs</div><div class=\"value\">${programDirectory.length}</div><div class=\"sub\">${open} currently open</div></div><div class=\"card metric\"><div class=\"label\">Authorized users</div><div class=\"value\">${activeUsers}</div><div class=\"sub\">Across all programs</div></div><div class=\"card metric\"><div class=\"label\">Heads of Department</div><div class=\"value\">${hods}</div><div class=\"sub\">Program leadership assignments</div></div><div class=\"card metric\"><div class=\"label\">System backup</div><div class=\"value\">XLSX</div><div class=\"sub\">All structured data; no generated DOCX stored</div></div></div>"""
assert old_return in block
new_return="""    const pingedAt=keepaliveStatus?.pinged_at?new Date(keepaliveStatus.pinged_at):null;\n    const nextAt=pingedAt?new Date(pingedAt.getTime()+5*24*60*60*1000):null;\n    const ageDays=pingedAt?(Date.now()-pingedAt.getTime())/(24*60*60*1000):null;\n    const heartbeatHealthy=!!pingedAt&&ageDays<6;\n    const heartbeatState=keepaliveStatus?.error?'Unavailable':heartbeatHealthy?'Healthy':pingedAt?'Overdue':'Waiting for first heartbeat';\n    const heartbeatClass=heartbeatHealthy?'text-good':keepaliveStatus?.error||pingedAt?'text-warn':'';\n    const heartbeatPanel=`<div class=\"section\"><div class=\"section-title\"><div><h2>Supabase project heartbeat</h2><p>A lightweight scheduled database heartbeat records one row approximately every five days. This table is isolated from Acadeloop business data and visible only to System Administrators.</p></div><span class=\"tag blue\">Scheduled</span></div><div class=\"grid grid-3\"><div class=\"card\"><span class=\"eyebrow\">Status</span><div class=\"big ${heartbeatClass}\" style=\"margin:10px 0 4px\">${esc(heartbeatState)}</div><div class=\"tiny\">Cron checks daily and inserts only after five days have elapsed.</div></div><div class=\"card\"><span class=\"eyebrow\">Last heartbeat</span><div style=\"font-weight:760;margin:12px 0 5px\">${pingedAt?esc(pingedAt.toLocaleString()):'—'}</div><div class=\"tiny\">Source: ${esc(keepaliveStatus?.source||'—')}</div></div><div class=\"card\"><span class=\"eyebrow\">Next expected</span><div style=\"font-weight:760;margin:12px 0 5px\">${nextAt?esc(nextAt.toLocaleString()):'—'}</div><div class=\"tiny\">Approximately five days after the latest successful heartbeat.</div></div></div></div>`;\n    return roleHero()+pageHead('Platform control','Acadeloop Administration','System-wide control for academic programs and authorized users.',backendEnabled?'<button class=\"btn btn-ghost\" id=\"backupAllData\">Backup Entire System (.xlsx)</button>':'')+`\n      <div class=\"grid grid-4\"><div class=\"card metric\"><div class=\"label\">Academic programs</div><div class=\"value\">${programDirectory.length}</div><div class=\"sub\">${open} currently open</div></div><div class=\"card metric\"><div class=\"label\">Authorized users</div><div class=\"value\">${activeUsers}</div><div class=\"sub\">Across all programs</div></div><div class=\"card metric\"><div class=\"label\">Heads of Department</div><div class=\"value\">${hods}</div><div class=\"sub\">Program leadership assignments</div></div><div class=\"card metric\"><div class=\"label\">System backup</div><div class=\"value\">XLSX</div><div class=\"sub\">All structured data; no generated DOCX stored</div></div></div>${heartbeatPanel}"""
block=block.replace(old_return,new_return,1)
app=app[:start]+block+app[end:]
app_path.write_text(app)

pkg=root/'package.json'
text=pkg.read_text().replace('"version": "1.2.5"','"version": "1.2.6"',1)
pkg.write_text(text)

ch=root/'CHANGELOG.md'
ct=ch.read_text()
entry="""### 1.2.6 — Supabase project heartbeat\n- Added an isolated `project_keepalive` table and scheduled Supabase Cron heartbeat.\n- Cron checks daily and inserts a row only when at least five days have elapsed since the previous heartbeat.\n- Added a System Administrator dashboard panel showing heartbeat status, last run, source, and next expected run.\n- Heartbeat records are read-only to authenticated users and visible through RLS only to System Administrators.\n\n\n"""
ct=ct.replace('# Changelog\n\n','# Changelog\n\n'+entry,1)
ch.write_text(ct)

check=root/'scripts/check-project.js'
cs=check.read_text()
needle="assert.ok(app.includes(\"export-backup-xlsx\"), 'Excel backup integration is missing');"
assert needle in cs
cs=cs.replace(needle, needle+"\nassert.ok(app.includes(\"project_keepalive\"), 'System Administrator keepalive status integration is missing');\nassert.ok(app.includes(\"Supabase project heartbeat\"), 'Keepalive dashboard panel is missing');",1)
check.write_text(cs)
print('Applied Acadeloop v1.2.6 keepalive status UI')