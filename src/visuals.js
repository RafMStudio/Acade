/*
  Itqan visual layer: decoration and motion only. Nothing here changes data.

  Generated artwork comes from the logo: the two pages of the open book (drawn
  with the logo's own paths from the inline sprite), and a lattice of the diamond
  dots of ت and ق that breathes outward from the spine.

  Motion
  - Entrance after sign-in: the two pages close in, the wordmark rises, the
    screen opens from the spine.
  - Page change: the content opens from the centre like a book, sections rise in
    sequence, the title slides up from behind a mask, the hero gets a hand-drawn
    check stroke, numbers count up, and the selection pill glides in the nav.
  - Scrolling: sections rise into view; the top bar slips away going down and
    returns going up.
  Everything is skipped under prefers-reduced-motion.

  DOM changes are made so the i18n layer keeps working: existing text nodes are
  moved, never re-created, so their English source stays attached to them.
*/
(() => {
  'use strict';
  if (document.documentElement.classList.contains('public-home')) return; // the public homepage animates itself

  const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const NS = 'http://www.w3.org/2000/svg';
  const PHOTO_DIR = 'assets/photos/';
  // One photo per workspace, so each role opens on a scene that matches its work.
  const HERO_PHOTO = {
    'Head of Department': 'hero-hod',
    'Coordinator': 'hero-coordinator',
    'Instructor': 'hero-instructor',
    'APU': 'hero-supervisor',
    'VDAA': 'hero-supervisor',
    'System Administrator': 'hero-supervisor'
  };

  /* ---------- generated artwork ---------- */
  function genArt(variant = 'a') {
    const cols = variant === 'b' ? 16 : 13, rows = variant === 'b' ? 11 : 15;
    const w = 400, h = variant === 'b' ? 280 : 460;
    const dots = [];
    const spineX = w * (variant === 'b' ? .62 : .5);
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = (c + .5) * (w / cols), y = (r + .5) * (h / rows);
        const dist = Math.hypot(x - spineX, (y - h * .62) * .8);
        const s = 4.2 + ((r * 7 + c * 3) % 5) * .35;
        dots.push(`<rect class="gd" x="${(x - s / 2).toFixed(1)}" y="${(y - s / 2).toFixed(1)}" width="${s.toFixed(1)}" height="${s.toFixed(1)}" rx="1.2" transform="rotate(45 ${x.toFixed(1)} ${y.toFixed(1)})" style="--d:${Math.round(dist * 9)}"/>`);
      }
    }
    const book = variant === 'b'
      ? `<svg x="150" y="40" width="300" height="234" viewBox="0 0 860 670" style="--lg-ink:#2E5562;--lg-sage:#8EAB9D" opacity=".55"><use href="#itqan-mark" width="860" height="670"/></svg>`
      : `<svg x="-40" y="190" width="480" height="374" viewBox="0 0 860 670" style="--lg-ink:#2E5562;--lg-sage:#8EAB9D" opacity=".5"><use href="#itqan-mark" width="860" height="670"/></svg>`;
    return `<svg class="gen-art${reduceMotion() ? '' : ' is-live'}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false" xmlns="${NS}">${book}<g>${dots.join('')}</g></svg>`;
  }

  // A real photo dropped into assets/photos/ takes over the slot; otherwise the artwork shows.
  const photoCache = new Map();
  function loadPhoto(name) {
    if (!photoCache.has(name)) {
      photoCache.set(name, new Promise((resolve) => {
        const tryExt = (exts) => {
          if (!exts.length) return resolve(null);
          const url = `${PHOTO_DIR}${name}.${exts[0]}`;
          const img = new Image();
          img.onload = () => resolve(url);
          img.onerror = () => tryExt(exts.slice(1));
          img.src = url;
        };
        tryExt(['webp', 'jpg']);
      }));
    }
    return photoCache.get(name);
  }
  function fillPhotoSlot(slot) {
    if (slot.dataset.filled) return;
    slot.dataset.filled = '1';
    slot.insertAdjacentHTML('afterbegin', genArt(slot.dataset.variant || 'a'));
    loadPhoto(slot.dataset.photo || 'campus').then((url) => {
      if (!url) return;
      slot.style.setProperty('--photo', `url("${url}")`);
      requestAnimationFrame(() => slot.classList.add('has-photo'));
    });
  }

  /* ---------- hero, titles, scribble ---------- */
  const SCRIBBLE = `<svg class="scribble" viewBox="0 0 320 34" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path pathLength="1" d="M6 21c38 5 92 7 150 5 46-2 86-6 112-8 10 0 18 3 22 9 3-6 9-14 24-24"/></svg>`;

  function maskTitle(h1) {
    if (!h1 || h1.querySelector('.mask-line')) return;
    const outer = document.createElement('span');
    outer.className = 'mask-line';
    const inner = document.createElement('span');
    outer.append(inner);
    while (h1.firstChild) inner.append(h1.firstChild); // move nodes; i18n keeps its source text
    h1.append(outer);
  }

  function decorate(root) {
    root.querySelectorAll('.dashboard-hero:not([data-deco])').forEach((hero) => {
      hero.dataset.deco = '1';
      const h1 = hero.querySelector('h1');
      maskTitle(h1);
      h1?.insertAdjacentHTML('beforeend', SCRIBBLE);
      requestAnimationFrame(() => h1?.querySelector('.scribble')?.classList.add('draw'));
      const photo = HERO_PHOTO[document.body.dataset.role] || 'hero-hod';
      hero.insertAdjacentHTML('beforeend', `<div class="hero-visual photo-slot" data-photo="${photo}" data-variant="b" aria-hidden="true"></div>`);
    });
    root.querySelectorAll('.page-head h1').forEach(maskTitle);
    root.querySelectorAll('.photo-slot').forEach(fillPhotoSlot);
  }

  /* ---------- numbers ---------- */
  function countUp(root) {
    if (reduceMotion()) return;
    root.querySelectorAll('.dashboard-page .metric .value, .quality-signal-card strong').forEach((el) => {
      const node = [...el.childNodes].find((n) => n.nodeType === Node.TEXT_NODE && /\d/.test(n.nodeValue));
      if (!node) return;
      const final = node.nodeValue;
      const m = final.match(/^(\s*)(\d+)(.*)$/s);
      if (!m) return;
      const target = Number(m[2]);
      if (!target) return;
      const start = performance.now(), dur = 1100;
      const tick = (t) => {
        if (!node.isConnected) return;
        const k = Math.min(1, (t - start) / dur);
        const eased = 1 - Math.pow(1 - k, 4);
        node.nodeValue = k < 1 ? `${m[1]}${Math.round(target * eased)}${m[3]}` : final;
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }

  /* ---------- scroll reveal ---------- */
  let io = null;
  function revealOnScroll(content) {
    if (reduceMotion() || !('IntersectionObserver' in window)) return;
    io ||= new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    }, { rootMargin: '0px 0px -8% 0px' });
    const fold = window.innerHeight;
    [...content.children].forEach((el) => {
      if (el.getBoundingClientRect().top > fold * .92) { el.classList.add('reveal'); io.observe(el); }
    });
  }

  /* ---------- page change ---------- */
  let lastView = '';
  function currentViewKey() {
    const active = document.querySelector('#nav .nav-item.active')?.dataset.view || '';
    return `${active}|${document.getElementById('pageTitle')?.textContent || ''}`;
  }
  function onContentRendered(content) {
    decorate(content);
    const key = currentViewKey();
    const changed = key !== lastView;
    lastView = key;
    if (!changed) return;
    if (!reduceMotion()) {
      content.classList.remove('page-open');
      void content.offsetWidth; // restart
      content.classList.add('page-open');
      clearTimeout(onContentRendered.t);
      onContentRendered.t = setTimeout(() => content.classList.remove('page-open'), 1200);
      const bar = document.getElementById('routeSignal');
      if (bar) { bar.classList.remove('run'); void bar.offsetWidth; bar.classList.add('run'); }
    }
    countUp(content);
    revealOnScroll(content);
  }

  /* ---------- entrance ---------- */
  function playEntrance() {
    const splash = document.getElementById('entranceSplash');
    if (!splash || reduceMotion()) return;
    splash.classList.remove('hidden', 'leave');
    void splash.offsetWidth;
    splash.classList.add('play');
    clearTimeout(playEntrance.t1); clearTimeout(playEntrance.t2);
    playEntrance.t1 = setTimeout(() => splash.classList.add('leave'), 1350);
    playEntrance.t2 = setTimeout(() => { splash.classList.add('hidden'); splash.classList.remove('play', 'leave'); }, 2050);
  }

  /* ---------- navigation pill ---------- */
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
      pill.style.insetInline = 'auto'; pill.style.left = '0px';
      pill.style.width = `${active.offsetWidth}px`; pill.style.height = `${active.offsetHeight}px`;
      pill.style.transform = `translate(${active.offsetLeft}px, ${active.offsetTop}px)`;
      active.scrollIntoView({ block: 'nearest', inline: 'center', behavior: reduceMotion() ? 'auto' : 'smooth' });
    } else {
      pill.style.left = ''; pill.style.width = ''; pill.style.insetInline = '';
      pill.style.height = `${active.offsetHeight}px`;
      pill.style.transform = `translateY(${active.offsetTop}px)`;
    }
    if (pill.style.transition === 'none') requestAnimationFrame(() => { pill.style.transition = ''; });
  }

  /* ---------- top bar ---------- */
  function topbarOnScroll() {
    const bar = document.querySelector('.topbar');
    if (!bar) return;
    let lastY = window.scrollY;
    window.addEventListener('scroll', () => {
      const y = window.scrollY;
      bar.classList.toggle('is-scrolled', y > 4);
      const drawerOpen = !document.getElementById('drawer')?.classList.contains('hidden');
      if (!drawerOpen && y > 140 && y > lastY + 6) bar.classList.add('is-hidden');
      else if (y < lastY - 6 || y < 140) bar.classList.remove('is-hidden');
      lastY = y;
    }, { passive: true });
  }

  function init() {
    document.querySelectorAll('.photo-slot').forEach(fillPhotoSlot);
    const content = document.getElementById('content');
    if (content) {
      new MutationObserver((list) => {
        if (list.some((m) => m.target === content && m.addedNodes.length)) onContentRendered(content);
      }).observe(content, { childList: true });
    }
    const shell = document.getElementById('appShell');
    if (shell) {
      let wasHidden = shell.classList.contains('hidden');
      new MutationObserver(() => {
        const hidden = shell.classList.contains('hidden');
        if (wasHidden && !hidden) { lastView = ''; playEntrance(); requestAnimationFrame(() => syncNavPill(false)); }
        wasHidden = hidden;
      }).observe(shell, { attributes: true, attributeFilter: ['class'] });
    }
    const nav = document.getElementById('nav');
    if (nav) {
      new MutationObserver(() => syncNavPill()).observe(nav, { subtree: true, attributes: true, attributeFilter: ['class'] });
      window.addEventListener('resize', () => syncNavPill(false));
      document.fonts?.ready?.then(() => syncNavPill(false));
      new MutationObserver(() => syncNavPill(false)).observe(document.documentElement, { attributes: true, attributeFilter: ['dir'] });
      syncNavPill(false);
    }
    topbarOnScroll();
  }

  window.ItqanVisuals = { genArt, decorate };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
