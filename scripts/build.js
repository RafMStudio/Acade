'use strict';

const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '..');
const dist = path.join(root, 'dist');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const escapeScript = (text) => text.replace(/<\/script/gi, '<\\/script');

function buildHtml() {
  let html = read('index.source.html');
  html = html.replace(
    '<link href="src/styles.css" rel="stylesheet"/>',
    `<style id="acadeloop-styles">\n${read('src/styles.css')}\n</style>`
  );
  html = html.replace(
    '<script src="src/vendor/jszip.min.js"></script>',
    '<script src="vendor/jszip.min.js"></script>'
  );
  for (const file of ['src/core.js', 'src/seed.js', 'src/backend.js', 'src/app.js']) {
    html = html.replace(
      `<script src="${file}"></script>`,
      `<script data-source="${file}">\n${escapeScript(read(file))}\n</script>`
    );
  }
  const banner = `<!--\n  Acadeloop deployment bundle.\n  Editable source: index.source.html + src/*.js + src/styles.css\n  The DOCX template remains a normal binary file under templates/.\n  No Base64 Word template is embedded here.\n-->\n`;
  return html.replace('<!DOCTYPE html>\n', `<!DOCTYPE html>\n${banner}`);
}

const html = buildHtml();
fs.writeFileSync(path.join(root, 'index.html'), html);
fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(dist, { recursive: true });
fs.writeFileSync(path.join(dist, 'index.html'), html);

const copy = (from, to = from) => {
  const source = path.join(root, from);
  const target = path.join(dist, to);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
};

copy('robots.txt');
copy('vendor/jszip.min.js');
copy('templates/Course_Report_Placeholder.docx');

console.log('Built resilient deployment: dist/index.html has inline Acadeloop CSS/app code; vendor + DOCX stay separate.');
