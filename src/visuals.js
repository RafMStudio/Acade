/* EduItqan decorative loops and optional reduced-motion-aware transitions. */
(() => {
  'use strict';
  if(document.documentElement.classList.contains('public-home'))return;

  const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  // Abstract overlapping loops for EduItqan, unrelated to institutional emblems.
  function ornament() {
    return '<svg class="ornament" viewBox="0 0 200 200" aria-hidden="true" focusable="false"><ellipse class="orn-ring orn-ring-0" cx="80" cy="100" rx="50" ry="75" transform="rotate(-30 80 100)" pathLength="1"/><ellipse class="orn-ring orn-ring-1" cx="120" cy="100" rx="50" ry="75" transform="rotate(30 120 100)" pathLength="1"/></svg>';
  }
  function emptyMark() {
    return `<span class="empty-mark" aria-hidden="true">${ornament()}</span>`;
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

  /* ---------- liquid navigation pill ---------- */
  // One pill slides and stretches between nav items, so the selection reads as
  // a single object moving rather than a highlight jumping.
  function syncNavPill(animate = true) {
    const nav = document.getElementById('nav');
    if (!nav) return;
    let pill = nav.querySelector('.nav-liquid');
    if (!pill) { pill = document.createElement('span'); pill.className = 'nav-liquid'; pill.setAttribute('aria-hidden', 'true'); nav.prepend(pill); }
    const active = nav.querySelector('.nav-item.active:not(.role-hidden)');
    if (!active || !active.offsetParent) { pill.style.opacity = '0'; return; }
    const horizontal = getComputedStyle(nav).display === 'flex';
    if (!animate || reduceMotion()) pill.style.transition = 'none';
    pill.style.opacity = '1';
    if (horizontal) {
      pill.style.insetInline = 'auto';
      pill.style.left = '0px';
      pill.style.width = `${active.offsetWidth}px`;
      pill.style.height = `${active.offsetHeight}px`;
      pill.style.transform = `translate(${active.offsetLeft}px, ${active.offsetTop}px)`;
    } else {
      pill.style.left = ''; pill.style.width = ''; pill.style.insetInline = '';
      pill.style.height = `${active.offsetHeight}px`;
      pill.style.transform = `translateY(${active.offsetTop}px)`;
    }
    if (pill.style.transition === 'none') requestAnimationFrame(() => { pill.style.transition = ''; });
    if (horizontal) active.scrollIntoView({ block: 'nearest', inline: 'center', behavior: reduceMotion() ? 'auto' : 'smooth' });
  }

  /* ---------- specular light on glass ---------- */
  function specular(e) {
    const el = e.target.closest?.('.sidebar, .topbar, .auth-card, .dashboard-page .metric');
    if (!el) return;
    const box = el.getBoundingClientRect();
    el.style.setProperty('--mx', `${Math.round(e.clientX - box.left)}px`);
    el.style.setProperty('--my', `${Math.round(e.clientY - box.top)}px`);
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
        if (wasHidden && !hidden) { playEntrance(); requestAnimationFrame(() => syncNavPill(false)); }
        wasHidden = hidden;
      }).observe(shell, { attributes: true, attributeFilter: ['class'] });
    }
    window.addEventListener('pointermove', parallax, { passive: true });
    window.addEventListener('pointermove', specular, { passive: true });
    const nav = document.getElementById('nav');
    if (nav) {
      new MutationObserver(() => syncNavPill()).observe(nav, { subtree: true, attributes: true, attributeFilter: ['class'] });
      window.addEventListener('resize', () => syncNavPill(false));
      document.fonts?.ready?.then(() => syncNavPill(false));
      new MutationObserver(() => syncNavPill(false)).observe(document.documentElement, { attributes: true, attributeFilter: ['dir'] });
      syncNavPill(false);
    }
  }

  window.EduItqanVisuals = { ornament, decorate };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
