#!/usr/bin/env python3
"""Reproducible original-source PDF package for software copyright review.

This script does not make legal authorship claims. It intentionally excludes
bundled dependencies, generated assets, and non-software design files.
"""
from __future__ import annotations
import hashlib, json, os, pathlib, subprocess, textwrap, zipfile
from datetime import datetime, timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=pathlib.Path(__file__).resolve().parent.parent
OUTPUT=ROOT/'saip_export'
OUTPUT.mkdir(exist_ok=True)
paths = [
 'src/core.js','src/app.js','src/backend.js',
 'src/i18n-ar.js','src/i18n.js','src/seed.js','src/visuals.js',
 'scripts/build.js','scripts/check-project.js',
 'tests/core.test.js','tests/i18n.test.js','tests/security.test.js','tests/supervisor.test.js',
 'supabase/functions/admin-create-user/index.ts',
 'supabase/functions/admin-manage-user/index.ts',
]
missing=[p for p in paths if not (ROOT/p).is_file()]
if missing: raise RuntimeError('Missing custom source files: '+', '.join(missing))
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
font='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
fontBold='/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
if os.path.exists(font):
 pdfmetrics.registerFont(TTFont('Deja',font))
 codefont='Deja'
else: codefont='Courier'
if os.path.exists(fontBold):
 pdfmetrics.registerFont(TTFont('DejaBold',fontBold))
 titlefont='DejaBold'
else: titlefont='Courier-Bold'
W,H=A4
c=canvas.Canvas(str(OUTPUT/'EduItqan_Complete_Original_Source.pdf'),pagesize=A4,pageCompression=1)
c.setTitle('EduItqan - Complete Original Software Source Code - Review Copy')
c.setAuthor('EduItqan - authorship and ownership to be declared by applicant')
page=0; y=0; filelabel=''
def head(label):
 global page,y,filelabel
 page+=1;filelabel=label
 c.setFillColorRGB(.07,.24,.28);c.rect(0,H-55,W,55,stroke=0,fill=1)
 c.setFillColorRGB(1,1,1);c.setFont(titlefont,11)
 c.drawString(35,H-33,'EduItqan | Original software code')
 c.setFillColorRGB(.36,.41,.44);c.setFont(codefont,7)
 c.drawString(35,25,'Review copy | Source snapshot: '+commit[:16]+' | '+label[:55])
 c.drawRightString(W-35,25,f'Page {page}')
 y=H-72
def line(s='',size=7.15):
 global y
 if y<44: c.showPage();head(filelabel)
 c.setFillColorRGB(.12,.16,.18);c.setFont(codefont,size)
 c.drawString(37,y,s[:110]);y-=9.9
def wrap(s,width=106):
 # preserve tabs and whitespace as closely as possible; long source lines wrap visibly
 s=s.expandtabs(2)
 if not s:return ['']
 return [s[i:i+width] for i in range(0,len(s),width)]
head('INTRODUCTION')
line('SOFTWARE: EduItqan')
line('CATEGORY: Computer Software and Applications')
line('SNAPSHOT COMMIT: '+commit)
line('GENERATED UTC: '+datetime.now(timezone.utc).isoformat(timespec='seconds'))
line('NOTICE: Copyright owner/author names require applicant verification.')
line('SCOPE: Complete custom JavaScript/TypeScript software source files listed below.')
line('EXCLUDED: HTML/CSS, SQL/database migrations, third-party libraries, fonts,')
line('generated HTML/JS, binaries, and the document template.')
line('File SHA-256 digests identify the exact source bytes included in this copy.')
line('Lines marked [wrapped] are continuation segments of long source lines.')
line('')
manifest=[]
for path in paths:
 b=(ROOT/path).read_bytes()
 s=b.decode('utf-8-sig')
 digest=hashlib.sha256(b).hexdigest()
 lines=s.splitlines()
 entry={'path':path,'bytes':len(b),'lines':len(lines),'sha256':digest}
 manifest.append(entry)
 head(path)
 line('FILE: '+path);line('SHA256: '+digest);line('LINES: '+str(len(lines)))
 line('-'*75)
 for n,raw in enumerate(lines,1):
  pieces=wrap(raw,94)
  for i,p in enumerate(pieces):
   prefix=(f'{n:05d} | ' if i==0 else '      | ')
   line(prefix+p)
 c.showPage()
# Avoid leaving a blank trailing PDF page.
c.save()
(OUTPUT/'EduItqan_Source_Manifest.json').write_text(json.dumps({
 'name':'EduItqan','snapshot_commit':commit,'generated_utc':datetime.now(timezone.utc).isoformat(),
 'included_original_source_files':manifest,
 'excluded':['third-party dependencies','generated assets','HTML/CSS','SQL migrations','document templates'],
 'statement':'Technical snapshot only; not proof of personal authorship or legal ownership.'
},indent=2,ensure_ascii=False),encoding='utf-8')
with zipfile.ZipFile(OUTPUT/'EduItqan_Original_Source_Files.zip','w',zipfile.ZIP_DEFLATED) as z:
 for path in paths:z.write(ROOT/path,arcname=path)
 z.write(OUTPUT/'EduItqan_Source_Manifest.json','EduItqan_Source_Manifest.json')
print(json.dumps({'snapshot':commit,'files':len(manifest),'source_bytes':sum(x['bytes'] for x in manifest),'pdf_bytes':(OUTPUT/'EduItqan_Complete_Original_Source.pdf').stat().st_size,'pages':page}))
