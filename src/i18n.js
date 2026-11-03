/*
  Acadeloop interface language (English / Arabic).

  The application renders English markup. This layer translates what is on screen
  without touching business data or calculations:
  - text nodes, plus placeholder / title / aria-label attributes, are looked up
    in the Arabic dictionary (exact phrase) and then in a short list of patterns
    for sentences that contain numbers or names;
  - the original English is remembered per node, so switching back is exact;
  - <option> elements without an explicit value keep their English value, so
    select.value never changes meaning when the label is translated;
  - <html lang dir> switches to rtl for Arabic.
  Course names, user names, codes and other data are not in the dictionary and
  stay as entered.
*/
(() => {
  'use strict';
  if(document.documentElement.classList.contains('public-home'))return;

  const STORAGE_KEY = 'acadeloop_lang';
  const ATTRS = ['placeholder', 'title', 'aria-label'];
  const SKIP = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'CODE', 'PRE', 'NOSCRIPT']);
  const AR = window.ACADELOOP_AR || { phrases: {}, patterns: [] };

  const phrases = new Map(Object.entries(AR.phrases || {}));
  // Lowercase index for headings/labels that only differ in letter case.
  const loose = new Map();
  for (const [en, ar] of phrases) loose.set(en.toLowerCase(), ar);
  const patterns = (AR.patterns || []).map(([source, out]) => [new RegExp(`^${source}$`, 'u'), out]);

  const textSource = new WeakMap(); // Text node -> { src, out }
  let lang = 'en';
  let observer = null;

  function readStoredLang() {
    try { return localStorage.getItem(STORAGE_KEY); } catch { return null; }
  }
  function storeLang(value) {
    try { localStorage.setItem(STORAGE_KEY, value); } catch { /* storage may be blocked; the choice still applies to this page */ }
  }

  // Academic years ("2026–2027") and ratios would be reordered inside right-to-left
  // text; a left-to-right isolate keeps them reading as written.
  const LRI = '\u2066', PDI = '\u2069';
  const isolateLtrRuns = (text) => text.replace(/(?<!\u2066)\d{4}–\d{4}(?!\u2069)/g, (m) => LRI + m + PDI);

  function translatePhrase(text) {
    if (lang !== 'ar') return text;
    const trimmed = text.trim();
    if (!trimmed) return text;
    if (!/[A-Za-z]/.test(trimmed)) return isolateLtrRuns(text);
    const hit = phrases.get(trimmed) ?? loose.get(trimmed.toLowerCase()) ?? matchPattern(trimmed);
    if (hit == null) return isolateLtrRuns(text);
    const lead = text.slice(0, text.indexOf(trimmed));
    const tail = text.slice(text.indexOf(trimmed) + trimmed.length);
    return isolateLtrRuns(lead + hit + tail);
  }
  function matchPattern(text) {
    for (const [re, out] of patterns) {
      const m = text.match(re);
      if (m) return out.replace(/\$(\d)/g, (_, i) => translateInner(m[Number(i)] ?? ''));
    }
    return null;
  }
  // Captured fragments (a role name, a term) may themselves be translatable.
  function translateInner(fragment) {
    const t = fragment.trim();
    return phrases.get(t) ?? loose.get(t.toLowerCase()) ?? fragment;
  }

  function translateTextNode(node) {
    let record = textSource.get(node);
    // The app replaced the text since we last translated it: treat it as new English.
    if (!record || node.nodeValue !== record.out) {
      record = { src: node.nodeValue, out: node.nodeValue };
      textSource.set(node, record);
    }
    const next = lang === 'ar' ? translatePhrase(record.src) : record.src;
    if (node.nodeValue !== next) node.nodeValue = next;
    record.out = next;
  }

  function translateElement(el) {
    if (el.tagName === 'OPTION' && !el.hasAttribute('value')) el.setAttribute('value', el.textContent);
    for (const attr of ATTRS) {
      if (!el.hasAttribute(attr)) continue;
      const key = `data-i18n-${attr}`;
      const current = el.getAttribute(attr);
      const stored = el.getAttribute(key);
      const storedOut = el.getAttribute(`${key}-out`);
      const src = stored != null && current === storedOut ? stored : current;
      const next = lang === 'ar' ? translatePhrase(src) : src;
      el.setAttribute(key, src);
      el.setAttribute(`${key}-out`, next);
      if (current !== next) el.setAttribute(attr, next);
    }
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === Node.TEXT_NODE) { if (!skipped(root.parentElement)) translateTextNode(root); return; }
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;
    if (root.nodeType === Node.ELEMENT_NODE) {
      if (skipped(root)) return;
      translateElement(root);
    }
    const tw = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (node.nodeType === Node.ELEMENT_NODE) return SKIP.has(node.tagName) || node.hasAttribute('data-no-i18n') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    let node = tw.nextNode();
    while (node) {
      if (node.nodeType === Node.TEXT_NODE) translateTextNode(node); else translateElement(node);
      node = tw.nextNode();
    }
  }
  function skipped(el) {
    for (let n = el; n; n = n.parentElement) if (SKIP.has(n.tagName) || n.hasAttribute?.('data-no-i18n')) return true;
    return false;
  }

  function withObserverPaused(fn) {
    observer?.disconnect();
    try { fn(); } finally { observe(); }
  }
  function observe() {
    if (!observer || !document.body) return;
    observer.observe(document.body, { childList: true, characterData: true, subtree: true, attributes: true, attributeFilter: ATTRS });
  }

  function syncToggles() {
    document.querySelectorAll('[data-lang-toggle]').forEach((btn) => {
      btn.textContent = lang === 'ar' ? 'English' : 'العربية';
      btn.setAttribute('lang', lang === 'ar' ? 'en' : 'ar');
      btn.setAttribute('aria-label', lang === 'ar' ? 'Switch to English' : 'التبديل إلى العربية');
      btn.setAttribute('data-no-i18n', '');
    });
  }

  function apply() {
    const html = document.documentElement;
    html.lang = lang;
    html.dir = lang === 'ar' ? 'rtl' : 'ltr';
    withObserverPaused(() => {
      syncToggles();
      walk(document.body);
      document.title = lang === 'ar' ? (AR.title || document.title) : (apply.title ||= document.title);
    });
  }

  function setLang(next) {
    lang = next === 'ar' ? 'ar' : 'en';
    storeLang(lang);
    apply();
  }

  function init() {
    apply.title = document.title;
    const stored = readStoredLang();
    lang = stored === 'ar' || stored === 'en' ? stored : (String(navigator.language || '').toLowerCase().startsWith('ar') ? 'ar' : 'en');
    observer = new MutationObserver((mutations) => {
      if (lang !== 'ar') return;
      withObserverPaused(() => {
        for (const m of mutations) {
          if (m.type === 'characterData') { if (!skipped(m.target.parentElement)) translateTextNode(m.target); }
          else if (m.type === 'attributes') { if (!skipped(m.target)) translateElement(m.target); }
          else m.addedNodes.forEach(walk);
        }
      });
    });
    document.addEventListener('click', (e) => {
      const btn = e.target.closest?.('[data-lang-toggle]');
      if (btn) setLang(lang === 'ar' ? 'en' : 'ar');
    });
    apply();
  }

  window.AcadeloopI18n = { t: (text) => translatePhrase(String(text ?? '')), setLang, get lang() { return lang; } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
