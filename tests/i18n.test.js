'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const context = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/i18n-ar.js'), 'utf8'), context);
const AR = context.window.EDUITQAN_AR;

test('Arabic dictionary loads with translated values', () => {
  assert.ok(Object.keys(AR.phrases).length > 500);
  for (const [en, ar] of Object.entries(AR.phrases)) {
    assert.equal(typeof ar, 'string', `${en} has no Arabic text`);
    assert.ok(ar.trim().length > 0, `${en} has empty Arabic text`);
  }
});

test('every pattern compiles and only references captured groups', () => {
  for (const [source, out] of AR.patterns) {
    const re = new RegExp(`^${source}$`, 'u');
    const groups = new RegExp(`${source}|`).exec('').length - 1;
    for (const ref of out.matchAll(/\$(\d)/g)) assert.ok(Number(ref[1]) <= groups, `${source} uses $${ref[1]} but has ${groups} groups`);
    assert.ok(re instanceof RegExp);
  }
});

test('codes that double as data identifiers are not translated', () => {
  for (const code of ['S1', 'S2', 'K1', 'HIM301']) assert.equal(AR.phrases[code], undefined, `${code} must stay as written`);
});
