/*
  Itqan public homepage motion.
  - Headings rise word by word from behind a mask (the homepage is Arabic-only,
    so words can be split without involving the interface translation layer).
  - Blocks spring up as they enter the viewport, in a short stagger.
  - The hand-drawn loop around the hero result draws itself.
  - The chart bars grow when the preview is in view.
  - Photos drift with the scroll; the header slips away going down.
  All of it is skipped under prefers-reduced-motion.
*/
(() => {
  'use strict';
  const root = document.documentElement;
  if (!root.classList.contains('public-home')) return;
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

  function splitWords(el) {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) if (walker.currentNode.nodeValue.trim() && !walker.currentNode.parentElement.closest('svg')) nodes.push(walker.currentNode);
    let i = 0;
    for (const node of nodes) {
      const frag = document.createDocumentFragment();
      for (const part of node.nodeValue.split(/(\s+)/)) {
        if (!part) continue;
        if (/^\s+$/.test(part)) { frag.append(part); continue; }
        const wrap = document.createElement('span'); wrap.className = 'hw';
        const word = document.createElement('span'); word.className = 'hw-i'; word.textContent = part;
        word.style.transitionDelay = `${Math.min(i++ * 55, 900)}ms`;
        wrap.append(word); frag.append(wrap);
      }
      node.replaceWith(frag);
    }
  }

  function init() {
    const home = document.getElementById('publicHome');
    if (!home) return;
    home.classList.add('is-ready');
    if (reduce) { home.classList.add('no-motion'); return; }

    home.querySelectorAll('h1, h2').forEach((h) => { splitWords(h); h.classList.add('hw-line'); });
    const blocks = home.querySelectorAll('.home-eyebrow, .home-lead, .home-actions, .home-small, .home-preview, .home-feature-grid > article, .home-accreditation-list > div, .home-contact .home-button, .home-email, .hg, .home-value p, .home-section-heading > p:not(.home-eyebrow)');
    blocks.forEach((el) => el.classList.add('hr'));
    home.querySelectorAll('.home-feature-grid > article, .hg, .home-accreditation-list > div').forEach((el, i, all) => {
      const siblings = [...el.parentElement.children];
      el.style.transitionDelay = `${siblings.indexOf(el) * 90}ms`;
    });

    const io = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.12 });
    home.querySelectorAll('.hw-line, .hr, .home-chart, .home-mark').forEach((el) => io.observe(el));

    // Photos drift slightly against the scroll
    const photos = [...home.querySelectorAll('.hg img')];
    const header = home.querySelector('.home-nav');
    let lastY = scrollY, ticking = false;
    const onScroll = () => {
      const y = scrollY;
      for (const img of photos) {
        const r = img.parentElement.getBoundingClientRect();
        if (r.bottom < 0 || r.top > innerHeight) continue;
        const k = (r.top + r.height / 2 - innerHeight / 2) / innerHeight;
        img.style.transform = `translateY(${(k * -28).toFixed(1)}px) scale(1.12)`;
      }
      if (header) {
        header.classList.toggle('is-scrolled', y > 8);
        if (y > 200 && y > lastY + 4) header.classList.add('is-hidden');
        else if (y < lastY - 4 || y < 200) header.classList.remove('is-hidden');
      }
      lastY = y; ticking = false;
    };
    addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
    onScroll();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
