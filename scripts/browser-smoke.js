'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawn, spawnSync } = require('node:child_process');

const root = path.join(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const inlineScript = (file) => read(file).replace(/<\/script/gi, '<\\/script');

let html = read('dist/index.html');
const bootHtml = html.replace('<script src="vendor/jszip.min.js"></script>', '');
html = html.replace('<script src="vendor/jszip.min.js"></script>', `<script>${inlineScript('src/vendor/jszip.min.js')}</script>`);

// Browser CI is sandboxed from localhost in this environment. Mock only the external
// binary template request in-memory; production still fetches the real DOCX file.
const templateBase64 = fs.readFileSync(path.join(root, 'templates/Course_Report_Placeholder.docx')).toString('base64');
const templateFetchMock = `<script>
(() => {
  const originalFetch = window.fetch.bind(window);
  const templateBase64 = '${templateBase64}';
  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    if (String(url).endsWith('templates/Course_Report_Placeholder.docx')) {
      const binary = atob(templateBase64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
      return new Response(bytes, { status: 200, headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' } });
    }
    return originalFetch(input, init);
  };
})();
</script>`;
html = html.replace('<script data-source="src/app.js">', `${templateFetchMock}<script data-source="src/app.js">`);

function findBrowser() {
  const candidates = [
    process.env.CHROMIUM_BIN,
    'chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable', 'chrome'
  ].filter(Boolean);
  return candidates.find((candidate) => spawnSync(candidate, ['--version'], { stdio: 'ignore' }).status === 0) || null;
}

const browser = findBrowser();
if (!browser) {
  console.log('Browser smoke test skipped: Chromium/Chrome not found.');
  process.exit(0);
}

const port = 9341;
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'acadeloop-chrome-'));
const chrome = spawn(browser, [
  '--headless=new', '--no-sandbox', '--disable-gpu',
  `--remote-debugging-port=${port}`, '--remote-allow-origins=*',
  `--user-data-dir=${profile}`, 'about:blank'
], { stdio: 'ignore' });
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function findPage() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const pages = await fetch(`http://127.0.0.1:${port}/json`).then((response) => response.json());
      const page = pages.find((item) => item.type === 'page');
      if (page) return page;
    } catch {}
    await sleep(50);
  }
  throw new Error('Chromium DevTools did not start');
}

class Cdp {
  constructor(url) {
    this.id = 0;
    this.pending = new Map();
    this.events = [];
    this.ws = new WebSocket(url);
  }
  async open() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', reject, { once: true });
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  listen() {
    this.ws.addEventListener('message', (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(message.error.message)); else resolve(message);
      } else {
        this.events.push(message);
      }
    });
  }
}

async function main() {
  const page = await findPage();
  const cdp = new Cdp(page.webSocketDebuggerUrl);
  await cdp.open();
  cdp.listen();
  await cdp.send('Runtime.enable');
  await cdp.send('Page.enable');
  const frameTree = await cdp.send('Page.getFrameTree');
  const evaluate = async (expression) => {
    const result = await cdp.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    const value = result.result.result;
    if (value.subtype === 'error') throw new Error(value.description);
    return value.value;
  };
  const expect = async (label, expression, expected) => {
    const actual = await evaluate(expression);
    if (actual !== expected) throw new Error(`${label}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  };
  // Regression for the raw/un-styled screenshot: the deployment index must boot
  // with its own CSS and Acadeloop code even when auxiliary files are unavailable.
  await cdp.send('Page.setDocumentContent', { frameId: frameTree.result.frameTree.frame.id, html: bootHtml });
  await sleep(300);
  await expect('deployment CSS is inline', "getComputedStyle(document.getElementById('authScreen')).display", 'grid');
  await expect('hidden app shell stays hidden before sign in', "getComputedStyle(document.getElementById('appShell')).display", 'none');
  await expect('Acadeloop app code is inline', "typeof window.AcadeloopCore==='object' && typeof window.ACADELOOP_SEED==='object'", true);
  await evaluate("document.querySelector('[data-test-login=TestI]').click()");
  await sleep(120);
  await expect('inline app works without vendor library', "document.getElementById('currentUserRole').textContent", 'Instructor');

  // Reload with JSZip + template mock for the full export workflow.
  await cdp.send('Page.setDocumentContent', { frameId: frameTree.result.frameTree.frame.id, html });
  await sleep(400);

  const waitForDownload = async () => {
    for (let i = 0; i < 100; i += 1) {
      if (await evaluate('window.__downloadCapture!==null')) {
        await evaluate('window.__downloadCapturePromise');
        return;
      }
      await sleep(50);
    }
    throw new Error('Timed out waiting for generated download');
  };

  await expect('Acadeloop branding', "document.title.startsWith('Acadeloop')", true);
  await expect('preset test users', "document.querySelectorAll('[data-test-login]').length", 4);
  await expect('template fetch mock works', "fetch('templates/Course_Report_Placeholder.docx').then(r=>r.ok)", true);

  // Regression: the database stores the global administrator role as `SystemAdmin`.
  // Even if that raw value reaches the UI, it must never fall back to Instructor.
  await evaluate(`(()=>{document.getElementById('loginUser').value='TestSA';document.getElementById('signInBtn').click();return true})()`);
  await sleep(200);
  await expect('SystemAdmin role canonicalized', "document.getElementById('currentUserRole').textContent", 'System Administrator');
  await expect('SystemAdmin workspace selected', "document.getElementById('roleContext').innerText.includes('System administration')", true);
  await expect('SystemAdmin cannot see instructor report creation nav', "document.querySelector('[data-view=course-reports]').classList.contains('role-hidden')", true);
  await evaluate("document.querySelector('[data-view=users]').click()");
  await sleep(100);
  await expect('SystemAdmin department is a dropdown', "document.getElementById('auDepartment').tagName", 'SELECT');
  await expect('SystemAdmin academic program is a dropdown', "document.getElementById('auProgram').tagName", 'SELECT');
  await expect('Ms prefix available', "[...document.getElementById('auPrefix').options].some(o=>o.value==='Ms.')", true);
  await evaluate("document.getElementById('signOutBtn').click()");
  await sleep(100);

  await evaluate(`(()=>{window.__downloadCapture=null;window.__downloadCapturePromise=Promise.resolve();HTMLAnchorElement.prototype.click=function(){const href=this.href,name=this.download;window.__downloadCapturePromise=(async()=>{const buf=await fetch(href).then(r=>r.arrayBuffer());const result={name,size:buf.byteLength,entries:[],docxPlaceholders:[]};if(name.endsWith('.zip')){const z=await JSZip.loadAsync(buf);result.entries=Object.keys(z.files);for(const entry of result.entries.filter(x=>x.endsWith('.docx'))){const file=z.file(entry);if(!file)continue;const inner=await JSZip.loadAsync(await file.async('arraybuffer'));const xml=await inner.file('word/document.xml').async('string');result.docxPlaceholders.push({entry,unreplaced:xml.includes('{{')});}}else if(name.endsWith('.docx')){const inner=await JSZip.loadAsync(buf);const xml=await inner.file('word/document.xml').async('string');result.docxPlaceholders.push({entry:name,unreplaced:xml.includes('{{')});}window.__downloadCapture=result;return result;})().catch(error=>{window.__downloadCapture={name,error:String(error)};return window.__downloadCapture});};return true})()`);

  await evaluate("document.querySelector('[data-test-login=TestI]').click()");
  await sleep(200);
  await expect('Instructor role', "document.getElementById('currentUserRole').textContent", 'Instructor');
  await expect('Instructor cannot see PLO nav', "document.querySelector('[data-view=plo]').classList.contains('role-hidden')", true);
  await evaluate("document.querySelector('[data-view=course-reports]').click();document.querySelector('[data-edit-report=\"r4\"]').click()");
  await sleep(150);

  const combined = await evaluate(`(()=>{const fire=(el,v)=>{el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}))};fire(document.querySelector('[data-sec=male][data-field=studentsStart]'),20);fire(document.querySelector('[data-sec=male][data-field=studentsComplete]'),20);fire(document.querySelector('[data-sec=female][data-field=studentsStart]'),15);fire(document.querySelector('[data-sec=female][data-field=studentsComplete]'),15);for(const el of document.querySelectorAll('[data-grade-sec=male],[data-grade-sec=female]'))fire(el,0);fire(document.querySelector('[data-grade-sec=male][data-grade="A+"]'),20);fire(document.querySelector('[data-grade-sec=female][data-grade="A+"]'),15);return document.querySelector('[data-grade-sec=combined][data-grade="A+"]').value;})()`);
  if (combined !== '35') throw new Error(`Combined A+ smoke check failed: ${combined}`);
  await expect('inflation becomes required live', "document.querySelector('[data-sec=male][data-field=gradeComment]').classList.contains('inflation-required-field')", true);

  await evaluate(`(()=>{const fire=(el,v)=>{el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}))};fire(document.querySelector('[data-sec=male][data-field=studentsStart]'),12);fire(document.querySelector('[data-sec=male][data-field=studentsComplete]'),12);fire(document.querySelector('[data-sec=female][data-field=studentsStart]'),14);fire(document.querySelector('[data-sec=female][data-field=studentsComplete]'),13);for(const el of document.querySelectorAll('[data-grade-sec=male],[data-grade-sec=female]'))fire(el,0);fire(document.querySelector('[data-grade-sec=male][data-grade="B"]'),12);fire(document.querySelector('[data-grade-sec=female][data-grade="B"]'),13);fire(document.querySelector('[data-grade-sec=female][data-grade="Withdrawn"]'),1);for(const el of document.querySelectorAll('[data-clo-result-sec=male][data-result-field=actual]'))fire(el,80);for(const el of document.querySelectorAll('[data-clo-result-sec=female][data-result-field=actual]'))fire(el,85);document.getElementById('submitReport').click();return true;})()`);
  await sleep(200);
  await expect('r4 submitted', "[...document.querySelectorAll('[data-report-row]')].find(r=>r.innerText.includes('HIM474')).innerText.includes('Awaiting Quality Approval')", true);

  await evaluate("document.getElementById('signOutBtn').click();document.querySelector('[data-test-login=TestQ]').click()");
  await sleep(250);
  await expect('Coordinator role', "document.getElementById('currentUserRole').textContent", 'Coordinator');
  await expect('quality dashboard', "document.body.innerText.includes('Course quality monitor')", true);
  await expect('seeded inflation visible', "[...document.querySelectorAll('[data-dashboard-course]')].some(r=>r.innerText.includes('HIM352')&&r.dataset.inflation==='1')", true);
  await evaluate("const c=document.getElementById('inflationOnlyCheck');c.checked=true;c.dispatchEvent(new Event('change',{bubbles:true}))");
  await expect('inflation filter hides non-inflated rows', "[...document.querySelectorAll('[data-dashboard-course]')].filter(r=>r.style.display!=='none').every(r=>r.dataset.inflation==='1')", true);
  await evaluate("document.querySelector('[data-view=course-reports]').click();document.querySelector('[data-edit-report=\"r4\"]').click()");
  await sleep(150);
  await expect('approval action available', "!!document.getElementById('approveReport')", true);
  await evaluate("document.getElementById('approveReport').click()");
  await sleep(200);
  await expect('r4 approved by coordinator', "[...document.querySelectorAll('[data-report-row]')].find(r=>r.innerText.includes('HIM474')).innerText.includes('Approved')", true);
  await evaluate("window.__downloadCapture=null;document.querySelector('[data-edit-report=\"r4\"]').click();document.getElementById('downloadReport').click()");
  await waitForDownload();
  await expect('all-section report export contains three DOCX files', "window.__downloadCapture.entries.filter(e=>e.endsWith('.docx')).length", 3);
  await expect('generated report placeholders fully replaced', "window.__downloadCapture.docxPlaceholders.every(x=>!x.unreplaced)", true);
  await evaluate("document.getElementById('drawerClose').click()");

  await evaluate("document.querySelector('[data-view=course-portfolios]').click()");
  await sleep(150);
  await expect('hidden folder-tree UI', "document.body.innerText.includes('Required Course Portfolio structure')", false);
  await evaluate("[...document.querySelectorAll('[data-open-portfolio]')].find(b=>b.closest('tr')?.innerText.includes('HIM474')).click()");
  await sleep(100);
  await expect('portfolio upload builder present', "document.querySelectorAll('input[data-portfolio-upload]').length>5", true);
  await evaluate(`(()=>{const input=document.querySelector('input[data-portfolio-upload="Course Specification (CS)"]');const dt=new DataTransfer();dt.items.add(new File(['test specification'],'Course Specification.pdf',{type:'application/pdf'}));input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}));return true})()`);
  await sleep(100);
  await evaluate("window.__downloadCapture=null;document.getElementById('downloadPortfolioZip').click()");
  await waitForDownload();
  await expect('portfolio ZIP starts at course code', "window.__downloadCapture.entries.some(e=>e.startsWith('HIM474/'))", true);
  await expect('portfolio ZIP has no obsolete list/program root', "window.__downloadCapture.entries.some(e=>e.startsWith('Program/')||e.includes('List of Courses'))", false);
  await expect('portfolio upload mapped to course specification', "window.__downloadCapture.entries.includes('HIM474/Course Specification (CS)/Course Specification.pdf')", true);
  await expect('portfolio includes generated approved course reports', "window.__downloadCapture.entries.some(e=>e.includes('/Course Report/')&&e.endsWith('.docx'))", true);
  await expect('portfolio generated DOCX placeholders fully replaced', "window.__downloadCapture.docxPlaceholders.every(x=>!x.unreplaced)", true);

  await evaluate("document.getElementById('signOutBtn').click();document.querySelector('[data-test-login=TestHOD]').click()");
  await sleep(250);
  await expect('HOD role', "document.getElementById('currentUserRole').textContent", 'Head of Department');
  await expect('HOD sees newly approved report', "document.body.innerText.includes('HIM474')", true);
  await expect('HOD hides unapproved r3', "document.body.innerText.includes('HIM403')", false);
  await expect('HOD sees CLO below-target signal', "document.body.innerText.includes('68% < 70%')", true);
  await expect('HOD users page access', "!document.querySelector('[data-view=users]').classList.contains('role-hidden')", true);
  await evaluate("document.querySelector('[data-view=users]').click()");
  await sleep(100);
  await evaluate(`(()=>{document.getElementById('auPrefix').value='Dr.';document.getElementById('auFirst').value='QA';document.getElementById('auLast').value='Tester';document.getElementById('auDepartment').value='Health Information Management';document.getElementById('auRole').value='Instructor';document.getElementById('auEmail').value='qa.tester@example.edu';document.getElementById('addAuthorizedUser').click();return true})()`);
  await sleep(150);
  await expect('HOD-added user rendered safely', "document.body.innerText.includes('Dr. QA Tester')&&document.body.innerText.includes('qa.tester@example.edu')", true);
  await evaluate("document.getElementById('signOutBtn').click();document.getElementById('loginUser').value='qa.tester@example.edu';document.getElementById('signInBtn').click()");
  await sleep(200);
  await expect('HOD-added user can sign in', "document.getElementById('currentUserRole').textContent", 'Instructor');

  const exceptions = cdp.events.filter((event) => event.method === 'Runtime.exceptionThrown');
  if (exceptions.length) throw new Error(`Browser runtime exceptions: ${exceptions.length}`);
  console.log('Browser workflow smoke checks passed.');
  cdp.ws.close();
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
}).finally(async () => {
  if (chrome.exitCode === null) {
    const exited = new Promise((resolve) => chrome.once('exit', resolve));
    chrome.kill();
    await Promise.race([exited, sleep(1000)]);
  }
  await sleep(300);
  try { fs.rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 150 }); } catch {}
});
