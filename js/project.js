// Shared by every project page in projects/<name>/: slide navigation (keys, swipe, dots, URL hash), the language switch
// and tab-like selectors. Same conventions as js/deck.js; the language choice is shared with the main deck ('deck-lang').
//
// Page title: <body data-page-title="…" data-de-data-page-title="…">.
// Selectors: <div data-select="tab" data-tab="1"> with buttons [data-tab="…"] and panels [data-for="…"] inside it;
// add data-hover to also select on hover (pointer devices only).
(() => {
  'use strict';

  document.documentElement.classList.add('js');
  const $ = (sel, root = document) => root.querySelector(sel);
  const slides = [...document.querySelectorAll('.slide')];
  if (!slides.length) return;

  const progress = $('#progress');
  const counter = $('#counter');
  const titleEl = $('#slideTitle');
  const announcer = $('#announcer');
  const prevBtn = $('#prev');
  const nextBtn = $('#next');
  const dots = $('#dots');
  let current = -1;

  // ---------- language ----------
  const LANGS = ['en', 'de'];
  const STRINGS = {
    de: { slide: (n, total, t) => `Folie ${n} von ${total}: ${t}`, goTo: (n, t) => `Zu Folie ${n}: ${t}` },
    en: { slide: (n, total, t) => `Slide ${n} of ${total}: ${t}`, goTo: (n, t) => `Go to slide ${n}: ${t}` },
  };
  const translatedAttrs = [...document.querySelectorAll('*')].flatMap(el =>
    [...el.attributes].filter(a => a.name.startsWith('data-de-')).map(a => {
      const name = a.name.slice('data-de-'.length);
      return { el, name, en: el.getAttribute(name), de: a.value };
    }));
  let lang = 'en';

  const dotButtons = slides.map((slide, i) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.addEventListener('click', () => go(i));
    dots.appendChild(b);
    return b;
  });

  function setLang(next, { remember = true } = {}) {
    if (!LANGS.includes(next)) return;
    lang = next;
    document.documentElement.lang = lang;
    translatedAttrs.forEach(({ el, name, de, en }) => el.setAttribute(name, lang === 'en' ? en : de));
    if (document.body.dataset.pageTitle) document.title = document.body.dataset.pageTitle;
    document.querySelectorAll('[data-set-lang]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.setLang === lang)));
    dotButtons.forEach((b, i) => b.setAttribute('aria-label', STRINGS[lang].goTo(i + 1, slides[i].dataset.title)));
    if (current >= 0) {
      titleEl.textContent = slides[current].dataset.title;
      announcer.textContent = STRINGS[lang].slide(current + 1, slides.length, slides[current].dataset.title);
    }
    if (!remember) return;
    try { localStorage.setItem('deck-lang', lang); } catch { /* storage blocked: choice lasts for this visit */ }
    const url = new URL(location.href);
    url.searchParams.set('lang', lang);
    try { history.replaceState(null, '', url); } catch { /* sandboxed preview */ }
  }
  document.querySelectorAll('[data-set-lang]').forEach(b => b.addEventListener('click', () => setLang(b.dataset.setLang)));

  // ---------- navigation ----------
  function slideFromHash() {
    const n = parseInt(location.hash.slice(1), 10);
    return Number.isFinite(n) ? n - 1 : 0;
  }

  function go(index, { updateHash = true } = {}) {
    const next = Math.max(0, Math.min(slides.length - 1, index));
    if (next === current) return;
    const focusWasInSlide = current >= 0 && slides[current].contains(document.activeElement);
    current = next;
    slides.forEach((s, j) => {
      s.classList.toggle('active', j === current);
      s.classList.toggle('past', j < current);
    });
    dotButtons.forEach((d, j) => {
      if (j === current) d.setAttribute('aria-current', 'step');
      else d.removeAttribute('aria-current');
    });
    const title = slides[current].dataset.title;
    progress.style.width = `${((current + 1) / slides.length) * 100}%`;
    counter.textContent = `${current + 1} / ${slides.length}`;
    titleEl.textContent = title;
    announcer.textContent = STRINGS[lang].slide(current + 1, slides.length, title);
    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === slides.length - 1;
    slides[current].scrollTop = 0;
    if (focusWasInSlide) slides[current].focus({ preventScroll: true });
    if (updateHash) {
      try { history.replaceState(null, '', `${location.search}#${current + 1}`); } catch { /* not allowed here */ }
    }
  }

  prevBtn.addEventListener('click', () => go(current - 1));
  nextBtn.addEventListener('click', () => go(current + 1));
  document.querySelectorAll('[data-go="next"]').forEach(b => b.addEventListener('click', () => go(current + 1)));
  window.addEventListener('hashchange', () => go(slideFromHash(), { updateHash: false }));

  const isInteractive = el => !!el.closest('a, button, input, select, textarea, summary, [contenteditable], dialog');
  document.addEventListener('keydown', e => {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    const onControl = isInteractive(e.target);
    let target = null;
    if (e.key === 'ArrowRight' || e.key === 'PageDown') target = current + 1;
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') target = current - 1;
    else if (!onControl && (e.key === ' ' || e.key === 'Enter')) target = e.shiftKey ? current - 1 : current + 1;
    else if (!onControl && e.key === 'Backspace') target = current - 1;
    else if (e.key === 'Home') target = 0;
    else if (e.key === 'End') target = slides.length - 1;
    if (target === null) return;
    e.preventDefault();
    go(target);
  });

  let touch = null;
  document.addEventListener('touchstart', e => {
    // horizontal swipes inside a scrollable table scroll the table, not the deck
    const inTable = e.target instanceof Element && e.target.closest('.scroll-x');
    touch = e.touches.length === 1 && !inTable ? { x: e.touches[0].clientX, y: e.touches[0].clientY } : null;
  }, { passive: true });
  document.addEventListener('touchend', e => {
    if (!touch) return;
    const dx = e.changedTouches[0].clientX - touch.x;
    const dy = e.changedTouches[0].clientY - touch.y;
    touch = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) go(current + (dx < 0 ? 1 : -1));
  }, { passive: true });

  // ---------- selectors: one pressed button picks the visible panel (tabs, diagram areas, steps) ----------
  document.querySelectorAll('[data-select]').forEach(container => {
    const attr = container.dataset.select;
    // selectors can nest (a diagram inside a tab): each one drives only its own buttons and its top-level panels
    const buttons = [...container.querySelectorAll(`button[data-${attr}]`)];
    const panels = [...container.querySelectorAll('[data-for]')].filter(p => !container.contains(p.parentElement.closest('[data-for]')));
    panels.forEach(p => p.classList.add('sel-panel'));
    const select = value => {
      container.dataset[attr] = value;
      buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset[attr] === value)));
      panels.forEach(p => p.classList.toggle('is-active', p.dataset.for === value));
    };
    buttons.forEach(b => {
      b.addEventListener('click', () => select(b.dataset[attr]));
      if ('hover' in container.dataset) b.addEventListener('mouseenter', () => { if (matchMedia('(hover: hover)').matches) select(b.dataset[attr]); });
    });
    select(container.dataset[attr] || buttons[0].dataset[attr]);
  });

  // ---------- decorative equalizer (beyerdynamic cover) ----------
  const wave = $('#wave');
  if (wave) {
    for (let i = 0; i < 40; i++) {
      const bar = document.createElement('i');
      // deterministic, music-like envelope: two overlapping sine curves
      const h = 18 + 62 * Math.abs(Math.sin(i * 0.37) * 0.7 + Math.sin(i * 0.11 + 1) * 0.3);
      bar.style.setProperty('--h', `${Math.round(h)}%`);
      bar.style.setProperty('--d', `${(i % 8) * 0.12}s`);
      wave.append(bar);
    }
  }

  setLang(LANGS.includes(document.documentElement.lang) ? document.documentElement.lang : 'en', { remember: false });
  go(slideFromHash(), { updateHash: location.hash !== '' });
})();
