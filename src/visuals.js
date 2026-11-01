/*
  Acadeloop visual layer — decorative only.

  Ornaments are generated from the motifs of the college seal: concentric rings,
  a ring of dots, a laurel wreath and a crescent. They are SVG strings drawn in
  currentColor, marked aria-hidden, and never carry information.

  Motion: one entrance moment (the seal draws itself when the workspace opens),
  a short page change cue (a green signal line under the top bar and a content
  reveal), and a gentle pointer parallax on the dashboard ornament.
  Everything is skipped when the person prefers reduced motion.
*/
(() => {
  'use strict';

  const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const r2 = (n) => Math.round(n * 100) / 100;

  // Laurel branch: leaves set along an arc, alternating sides of the stem.
  function laurel(cx, cy, radius, startDeg, endDeg, leaves, mirror) {
    const parts = [];
    const toXY = (deg, r) => {
      const a = (deg - 90) * Math.PI / 180;
      return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
    };
    const [sx, sy] = toXY(startDeg, radius);
    const [ex, ey] = toXY(endDeg, radius);
    const sweep = endDeg > startDeg ? 1 : 0;
    parts.push(`<path d="M${r2(sx)} ${r2(sy)} A${radius} ${radius} 0 0 ${sweep} ${r2(ex)} ${r2(ey)}" />`);
    for (let i = 0; i < leaves; i++) {
      const t = (i + 0.5) / leaves;
      const deg = startDeg + (endDeg - startDeg) * t;
      const side = i % 2 ? 1 : -1;
      const [x, y] = toXY(deg, radius + side * 4.5);
      const rot = deg + (mirror ? -1 : 1) * side * 35;
      const size = 6.5 - t * 2.5;
      parts.push(`<ellipse cx="${r2(x)}" cy="${r2(y)}" rx="${r2(size * 0.42)}" ry="${r2(size)}" transform="rotate(${r2(rot)} ${r2(x)} ${r2(y)})" />`);
    }
    return parts.join('');
  }

  // A seal-like ornament on a 200x200 canvas.
  function ornament({ dots = 36, laurelLeaves = 11, crescent = true, rings = [96, 84, 62] } = {}) {
    const c = 100;
    const out = [];
    rings.forEach((r, i) => out.push(`<circle class="orn-ring orn-ring-${i}" cx="${c}" cy="${c}" r="${r}" pathLength="1" />`));
    const dotRing = (rings[0] + rings[1]) / 2;
    for (let i = 0; i < dots; i++) {
      const a = (i / dots) * Math.PI * 2;
      out.push(`<circle class="orn-dot" cx="${r2(c + dotRing * Math.cos(a))}" cy="${r2(c + dotRing * Math.sin(a))}" r="${i % 6 === 0 ? 1.9 : 1.1}" />`);
    }
    const lr = rings[2] - 10;
    out.push(`<g class="orn-laurel">${laurel(c, c, lr, 200, 330, laurelLeaves, false)}${laurel(c, c, lr, 160, 30, laurelLeaves, true)}</g>`);
    if (crescent) {
      out.push(`<path class="orn-crescent" d="M118 82a26 26 0 1 0 0 36a20 20 0 1 1 0-36Z" />`);
    }
    return `<svg class="ornament" viewBox="0 0 200 200" aria-hidden="true" focusable="false">${out.join('')}</svg>`;
  }

  // Dot lattice tile inspired by the seal's dotted ring, for empty states.
  function emptyMark() {
    return `<span class="empty-mark" aria-hidden="true">${ornament({ dots: 24, laurelLeaves: 7, rings: [96, 86, 66] })}</span>`;
  }

  /* ---------- placing ornaments ---------- */
  function decorate(root = document) {
    root.querySelectorAll('.dashboard-hero:not([data-orn])').forEach((hero) => {
      hero.dataset.orn = '1';
      hero.insertAdjacentHTML('beforeend', `<div class="hero-ornament" aria-hidden="true">${ornament()}</div>`);
    });
    root.querySelectorAll('.auth-brand:not([data-orn])').forEach((panel) => {
      panel.dataset.orn = '1';
      panel.insertAdjacentHTML('beforeend', `<div class="auth-ornament" aria-hidden="true">${ornament({ dots: 48, laurelLeaves: 13 })}</div>`);
    });
    root.querySelectorAll('.page-head:not([data-orn])').forEach((head) => {
      head.dataset.orn = '1';
      head.insertAdjacentHTML('afterbegin', `<span class="page-head-orn" aria-hidden="true">${ornament({ dots: 18, laurelLeaves: 5, crescent: false })}</span>`);
    });
    root.querySelectorAll('.portfolio-empty:not([data-orn]), div.empty:not([data-orn])').forEach((box) => {
      box.dataset.orn = '1';
      box.insertAdjacentHTML('afterbegin', emptyMark());
    });
  }

  /* ---------- motion ---------- */
  function pageChangeCue(content) {
    if (reduceMotion()) return;
    const bar = document.getElementById('routeSignal');
    if (bar) {
      bar.classList.remove('run');
      void bar.offsetWidth; // restart the animation
      bar.classList.add('run');
    }
    content.classList.remove('view-enter');
    void content.offsetWidth;
    content.classList.add('view-enter');
  }

  function playEntrance() {
    const splash = document.getElementById('entranceSplash');
    if (!splash || reduceMotion()) return;
    splash.classList.remove('hidden', 'leave');
    splash.classList.add('play');
    clearTimeout(playEntrance.t1); clearTimeout(playEntrance.t2);
    playEntrance.t1 = setTimeout(() => splash.classList.add('leave'), 1150);
    playEntrance.t2 = setTimeout(() => { splash.classList.add('hidden'); splash.classList.remove('play', 'leave'); }, 1650);
  }

  function parallax(e) {
    if (reduceMotion()) return;
    const orn = document.querySelector('.hero-ornament .ornament');
    if (!orn) return;
    const hero = orn.closest('.dashboard-hero');
    const box = hero.getBoundingClientRect();
    if (e.clientY < box.top || e.clientY > box.bottom) return;
    const dx = (e.clientX - box.left) / box.width - 0.5;
    const dy = (e.clientY - box.top) / box.height - 0.5;
    orn.style.transform = `rotate(${r2(dx * 14)}deg) translate(${r2(dx * -10)}px, ${r2(dy * -8)}px)`;
  }

  function init() {
    const splash = document.getElementById('entranceSplash');
    if (splash && !splash.querySelector('.ornament')) splash.querySelector('.splash-mark')?.insertAdjacentHTML('afterbegin', ornament({ dots: 40, laurelLeaves: 12 }));
    decorate();
    const content = document.getElementById('content');
    if (content) {
      new MutationObserver((list) => {
        if (list.some((m) => m.target === content && m.type === 'childList' && m.addedNodes.length)) pageChangeCue(content);
        decorate(content);
      }).observe(content, { childList: true, subtree: true });
    }
    const shell = document.getElementById('appShell');
    if (shell) {
      let wasHidden = shell.classList.contains('hidden');
      new MutationObserver(() => {
        const hidden = shell.classList.contains('hidden');
        if (wasHidden && !hidden) playEntrance();
        wasHidden = hidden;
      }).observe(shell, { attributes: true, attributeFilter: ['class'] });
    }
    window.addEventListener('pointermove', parallax, { passive: true });
  }

  window.AcadeloopVisuals = { ornament, decorate };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
