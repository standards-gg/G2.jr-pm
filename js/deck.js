// Slide deck controller: navigation (keys, swipe, dots, URL hash), image lightbox and link previews.
(() => {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const slides = [...document.querySelectorAll('.slide')];
  if (!slides.length) return;

  const progress = $('#progress');
  const counter = $('#counter');
  const counterCur = $('.cur', counter);
  const counterTot = $('.tot', counter);
  const titleEl = $('#slideTitle');
  const announcer = $('#announcer');
  const prevBtn = $('#prev');
  const nextBtn = $('#next');
  const dots = $('#dots');
  const preview = $('#sitePreview');
  const previewImg = Object.assign(document.createElement('img'), { alt: '', decoding: 'async' });
  const previewUrl = $('.bar span', preview);
  const previewCount = $('.bar b', preview);
  const lightbox = $('#lightbox');
  const lightboxImg = Object.assign(document.createElement('img'), { alt: '' });
  $('.frame', preview).append(previewImg);
  lightbox.append(lightboxImg);

  let current = -1;

  // ---------- language (English markup; texts exist as lang="en" / lang="de" pairs; js/lang.js picks the start language) ----------
  const LANGS = ['en', 'de'];
  const STRINGS = {
    de: {
      title: 'Christian Balan · Bewerbung G2 Esports',
      slide: (n, total, t) => `Folie ${n} von ${total}: ${t}`,
      goTo: (n, t) => `Zu Folie ${n}: ${t}`,
    },
    en: {
      title: 'Christian Balan · G2 Esports application',
      slide: (n, total, t) => `Slide ${n} of ${total}: ${t}`,
      goTo: (n, t) => `Go to slide ${n}: ${t}`,
    },
  };
  const STORAGE_KEY = 'deck-lang';
  // attributes with a German twin: aria-label + data-de-aria-label, alt + data-de-alt, ...
  const translatedAttrs = [...document.querySelectorAll('*')].flatMap(el =>
    [...el.attributes].filter(a => a.name.startsWith('data-de-')).map(a => {
      const name = a.name.slice('data-de-'.length);
      return { el, name, en: el.getAttribute(name), de: a.value };
    }));
  let lang = 'en';

  // js/lang.js has already set <html lang> (URL > saved choice > location); fall back to English without it
  const initialLang = () => (LANGS.includes(document.documentElement.lang) ? document.documentElement.lang : 'en');

  // ---------- navigation ----------
  const dotButtons = slides.map((slide, i) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.addEventListener('click', () => go(i));
    dots.appendChild(b);
    return b;
  });

  function labelDots() {
    dotButtons.forEach((b, i) => b.setAttribute('aria-label', STRINGS[lang].goTo(i + 1, slides[i].dataset.title)));
  }

  function setLang(next, { remember = true } = {}) {
    if (!LANGS.includes(next)) return;
    lang = next;
    document.documentElement.lang = lang;
    translatedAttrs.forEach(({ el, name, de, en }) => el.setAttribute(name, lang === 'en' ? en : de));
    document.title = STRINGS[lang].title;
    document.querySelectorAll('[data-set-lang]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.setLang === lang)));
    labelDots();
    hidePreview();
    if (current >= 0) {
      const title = slides[current].dataset.title;
      titleEl.textContent = title;
      announcer.textContent = STRINGS[lang].slide(current + 1, slides.length, title);
    }
    if (!remember) return;
    try { localStorage.setItem(STORAGE_KEY, lang); } catch { /* storage blocked: choice lasts for this visit */ }
    // an explicit choice is shareable: the link opens in the chosen language wherever it is opened
    const url = new URL(location.href);
    url.searchParams.set('lang', lang);
    try { history.replaceState(null, '', url); } catch { /* sandboxed preview */ }
  }
  document.querySelectorAll('[data-set-lang]').forEach(b => b.addEventListener('click', () => setLang(b.dataset.setLang)));

  function slideFromHash() {
    const n = parseInt(location.hash.slice(1), 10);
    return Number.isFinite(n) ? n - 1 : 0;
  }

  function go(index, { updateHash = true } = {}) {
    const next = Math.max(0, Math.min(slides.length - 1, index));
    if (next === current) return;
    const focusWasInSlide = current >= 0 && slides[current].contains(document.activeElement);
    current = next;
    hidePreview();

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
    counterCur.textContent = current + 1;
    counterTot.textContent = slides.length;
    titleEl.textContent = title;
    announcer.textContent = STRINGS[lang].slide(current + 1, slides.length, title);
    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === slides.length - 1;
    slides[current].scrollTop = 0;

    // Keyboard users whose focus sat on the old (now hidden) slide continue on the new one.
    if (focusWasInSlide) slides[current].focus({ preventScroll: true });

    if (updateHash) {
      // Sandboxed previews (e.g. iframes with srcdoc) forbid history changes; navigation still works.
      try { history.replaceState(null, '', `${location.search}#${current + 1}`); } catch { /* not allowed here */ }
    }
  }

  prevBtn.addEventListener('click', () => go(current - 1));
  nextBtn.addEventListener('click', () => go(current + 1));
  // green dot above ‹ jumps to the first slide, gold dot above › to the golden conclusion slide (the bonus slide comes after it)
  const conclusion = slides.findIndex(s => s.classList.contains('conclusion'));
  $('#first').addEventListener('click', () => go(0));
  $('#last').addEventListener('click', () => go(conclusion >= 0 ? conclusion : slides.length - 1));
  window.addEventListener('hashchange', () => go(slideFromHash(), { updateHash: false }));

  const isInteractive = el => !!el.closest('a, button, input, select, textarea, summary, [contenteditable], dialog');

  document.addEventListener('keydown', e => {
    if (document.querySelector('dialog[open]') || e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === 'Escape') { hidePreview(); return; }
    // Enter / Space / Backspace belong to the focused control (links, buttons) — never hijack them.
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
    touch = e.touches.length === 1 && !lightbox.open ? { x: e.touches[0].clientX, y: e.touches[0].clientY } : null;
  }, { passive: true });
  document.addEventListener('touchend', e => {
    if (!touch) return;
    const dx = e.changedTouches[0].clientX - touch.x;
    const dy = e.changedTouches[0].clientY - touch.y;
    touch = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) go(current + (dx < 0 ? 1 : -1));
  }, { passive: true });

  // ---------- images ----------
  // Streamer avatars fall back to their initials if an image cannot be loaded.
  document.querySelectorAll('.avatar img').forEach(img => {
    const drop = () => img.remove();
    if (img.complete && img.naturalWidth === 0) drop();
    else img.addEventListener('error', drop, { once: true });
  });

  // Lightbox: elements with data-full open the full image (or the slideshow frame on screen); closes via ×, backdrop click or Esc.
  document.querySelectorAll('[data-full]').forEach(trigger => trigger.addEventListener('click', () => {
    const src = trigger === previewLink && shots.length > 1 ? shots[shotIndex] : trigger.dataset.full;
    hidePreview();
    lightboxImg.src = src;
    lightboxImg.alt = trigger.dataset.alt || '';
    lightbox.showModal();
  }));
  $('.icon-btn', lightbox).addEventListener('click', () => lightbox.close());
  lightbox.addEventListener('click', e => { if (e.target === lightbox) lightbox.close(); });

  // ---------- intro menus (references, demos): open on hover (CSS) or tap / click / keyboard ----------
  const menus = [...document.querySelectorAll('[data-menu]')];
  const setMenu = (menu, open) => {
    menu.classList.toggle('open', open);
    $('.menu-btn', menu).setAttribute('aria-expanded', String(open));
  };
  menus.forEach(menu => {
    $('.menu-btn', menu).addEventListener('click', () => {
      const open = !menu.classList.contains('open');
      menus.forEach(m => setMenu(m, false));
      setMenu(menu, open);
    });
    menu.querySelectorAll('.menu-item').forEach(item => item.addEventListener('click', () => setMenu(menu, false)));
    menu.addEventListener('focusout', e => { if (!menu.contains(e.relatedTarget)) setMenu(menu, false); });
    menu.addEventListener('keydown', e => {
      if (e.key === 'Escape' && menu.classList.contains('open')) { setMenu(menu, false); $('.menu-btn', menu).focus(); }
    });
  });
  document.addEventListener('click', e => menus.forEach(m => { if (!m.contains(e.target)) setMenu(m, false); }));

  // ---------- CV & reference viewer: PDF in a dialog where the browser can show PDFs inline; otherwise the link opens it ----------
  const cvViewer = $('#cvViewer');
  const cvFrame = $('.cv-frame', cvViewer);
  const cvName = $('.cv-name', cvViewer);
  const cvNameDefault = cvName.innerHTML;
  const cvDownload = $('.cv-download', cvViewer);
  const cvDownloadDefault = cvDownload.getAttribute('download');
  const canShowPdfInline = () => navigator.pdfViewerEnabled !== false && matchMedia('(min-width: 861px) and (hover: hover)').matches;
  document.querySelectorAll('[data-cv-open]').forEach(link => link.addEventListener('click', e => {
    if (!canShowPdfInline()) return; // phones & tablets: follow the link (new tab / native viewer)
    e.preventDefault();
    hidePreview();
    // one viewer for the CV and the references: show the clicked PDF, its name and a matching download
    if (cvFrame.getAttribute('src') !== link.getAttribute('href')) cvFrame.src = link.getAttribute('href');
    const label = link.querySelector('.pdf-label');
    cvName.innerHTML = label ? label.innerHTML : cvNameDefault;
    cvDownload.href = link.getAttribute('href');
    cvDownload.download = link.dataset.download || cvDownloadDefault;
    cvViewer.showModal();
  }));
  $('.cv-close', cvViewer).addEventListener('click', () => cvViewer.close());
  cvViewer.addEventListener('click', e => { if (e.target === cvViewer) cvViewer.close(); });

  // ---------- link previews: screenshot(s) of the target next to the link (pointer + keyboard) ----------
  // data-shot holds one image path, or several separated by spaces to play as a crossfading slideshow.
  const SHOT_INTERVAL = 2200;
  let previewLink = null;
  let shots = [];
  let shotIndex = 0;
  let shotTimer = null;

  function showShot(i) {
    shotIndex = i;
    previewCount.textContent = shots.length > 1 ? `${i + 1} / ${shots.length}` : '';
    if (previewImg.getAttribute('src') === shots[i]) { previewImg.classList.remove('fading'); return; }
    previewImg.src = shots[i];
  }
  function nextShot() {
    previewImg.classList.add('fading');
    // swap once faded out; the load handler fades the new frame back in
    setTimeout(() => { if (previewLink) showShot((shotIndex + 1) % shots.length); }, 250);
  }
  function placePreview() {
    if (!previewLink) return;
    const r = previewLink.getBoundingClientRect();
    const w = preview.offsetWidth, h = preview.offsetHeight;
    let top = r.top - h - 10 > 8 ? r.top - h - 10 : r.bottom + 10;
    top = Math.max(8, Math.min(top, innerHeight - h - 8));
    const left = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), innerWidth - w - 8);
    preview.style.top = `${top}px`;
    preview.style.left = `${left}px`;
  }
  function showPreview(link) {
    // mouse click = hover + focus: don't restart a preview (or its slideshow) that is already showing
    if (previewLink === link && preview.classList.contains('show')) return;
    previewLink = link;
    clearInterval(shotTimer);
    shots = link.dataset.shot.trim().split(/\s+/);
    shots.slice(1).forEach(src => { new Image().src = src; }); // warm the cache for the slideshow
    showShot(0);
    if (shots.length > 1) shotTimer = setInterval(nextShot, SHOT_INTERVAL);
    previewUrl.textContent = link.dataset.preview.replace(/^https?:\/\//, '');
    preview.classList.toggle('tall', 'tall' in link.dataset);
    placePreview();
    preview.classList.add('show');
  }
  function hidePreview() {
    clearInterval(shotTimer);
    previewLink = null;
    preview.classList.remove('show');
  }
  // A tall screenshot changes the card's height once decoded: place it again.
  previewImg.addEventListener('load', () => { previewImg.classList.remove('fading'); placePreview(); });
  document.querySelectorAll('[data-preview]').forEach(link => {
    link.addEventListener('mouseenter', () => showPreview(link));
    link.addEventListener('focus', () => showPreview(link));
    link.addEventListener('mouseleave', hidePreview);
    link.addEventListener('blur', hidePreview);
  });
  slides.forEach(s => s.addEventListener('scroll', hidePreview, { passive: true }));
  window.addEventListener('resize', hidePreview);

  setLang(initialLang(), { remember: false });
  go(slideFromHash(), { updateHash: location.hash !== '' });
})();
