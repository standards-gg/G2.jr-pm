
// Project presentation: slide navigation (keys, swipe, dots, URL hash), language switch, the selectors
// (pillars, EDA steps, hypotheses, segment explorer) and the charts, all computed from the hypothetical dataset below.
// Same conventions as js/deck.js; the language choice is shared with the main deck (localStorage 'deck-lang').
(() => {
  'use strict';

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

  // ---------- data: HYPOTHETICAL campaign dataset (32 activation-level rows, 8 weeks) ----------
  // week, game, activation, format, platform, impressions, reach, engagements, clicks, conversions
  const RAW = `
1|VALORANT|Matchday Activation|Player Video|YouTube|185000|142000|6120|3820|96
1|LoL|Team Content|Short Video|Instagram|164000|121000|4780|2460|61
1|CS2|Launch Content|Creator Video|Twitch|132000|91000|5120|2980|74
1|R6|Partner Content|Static Social|X|78000|59000|1710|920|21
2|VALORANT|Matchday Activation|Creator Stream|Twitch|241000|176000|10480|6120|168
2|LoL|Team Content|Player Video|YouTube|193000|145000|6810|3510|88
2|CS2|Product Integration|Short Video|Instagram|151000|112000|4310|2180|52
2|Fortnite|Giveaway|Static Social|Instagram|126000|97000|5890|3110|79
3|VALORANT|Playoff Activation|Player Video|YouTube|318000|229000|15420|10480|312
3|LoL|Matchday Activation|Creator Video|Twitch|276000|201000|12840|7320|201
3|CS2|Team Content|Short Video|Instagram|172000|129000|5360|2710|67
3|R6|Product Integration|Player Video|YouTube|143000|104000|5290|2840|71
4|VALORANT|Playoff Activation|Creator Stream|Twitch|382000|271000|19640|14120|438
4|LoL|Team Content|Static Social|Instagram|181000|134000|4920|2480|59
4|CS2|Matchday Activation|Player Video|YouTube|207000|151000|7820|4210|109
4|Rocket League|Partner Content|Short Video|TikTok|118000|91000|5170|2640|63
5|VALORANT|Playoff Activation|Creator Video|YouTube|426000|301000|24480|17240|561
5|LoL|Playoff Activation|Player Video|YouTube|349000|252000|17120|10180|286
5|CS2|Team Content|Creator Video|Twitch|228000|165000|10140|6230|159
5|R6|Matchday Activation|Short Video|Instagram|162000|121000|6410|3310|82
6|VALORANT|Finals Activation|Creator Stream|Twitch|511000|357000|32400|23840|812
6|LoL|Finals Activation|Player Video|YouTube|463000|329000|24810|16120|527
6|CS2|Matchday Activation|Creator Video|Twitch|294000|211000|13760|8640|221
6|Fortnite|Giveaway|Short Video|Instagram|174000|132000|8210|4380|113
7|VALORANT|Finals Activation|Creator Video|YouTube|468000|334000|28920|21140|734
7|LoL|Team Content|Creator Stream|Twitch|321000|232000|15780|9340|248
7|CS2|Product Integration|Player Video|YouTube|239000|175000|9460|5270|136
7|R6|Team Content|Short Video|Instagram|151000|113000|5740|2970|72
8|VALORANT|Post-Finals|Creator Video|YouTube|297000|214000|18620|13180|451
8|LoL|Post-Finals|Player Video|YouTube|251000|183000|11340|6840|176
8|CS2|Partner Content|Creator Video|Twitch|214000|155000|10920|6820|173
8|Rocket League|Partner Content|Short Video|TikTok|109000|83000|4380|2260|54`;
  const MOMENTS = { Matchday: 'matchday', Playoff: 'playoff', Finals: 'finals', 'Post-Finals': 'post' };
  const SOURCES = { 'Creator Stream': 'creator', 'Creator Video': 'creator', 'Player Video': 'player', 'Short Video': 'team', 'Static Social': 'team' };
  const rows = RAW.trim().split('\n').map(line => {
    const [week, game, activation, format, platform, ...n] = line.split('|');
    const [impressions, reach, engagements, clicks, conversions] = n.map(Number);
    const moment = MOMENTS[activation.split(' ')[0]] || 'always';
    return { week: +week, game, activation, format, platform, impressions, reach, engagements, clicks, conversions, moment, source: SOURCES[format] };
  });
  // approvals: assets that met the 48 h client SLA, 4 assets per week (HYPOTHETICAL)
  const SLA_MET = [2, 2, 3, 3, 3, 2, 4, 4];

  const sum = (list, key) => list.reduce((s, r) => s + r[key], 0);
  function aggregate(list) {
    const imp = sum(list, 'impressions'), clk = sum(list, 'clicks'), conv = sum(list, 'conversions');
    return { n: list.length, imp, clk, conv, ctr: clk / imp * 100, cvr: conv / clk * 100, per1k: conv / imp * 1000 };
  }
  const weeks = [1, 2, 3, 4, 5, 6, 7, 8].map(w => aggregate(rows.filter(r => r.week === w)));

  // ---------- language ----------
  const LANGS = ['en', 'de'];
  const STRINGS = {
    de: {
      title: 'G2 × ExpressVPN · Partnership Operations',
      slide: (n, total, t) => `Folie ${n} von ${total}: ${t}`,
      goTo: (n, t) => `Zu Folie ${n}: ${t}`,
      seg: {
        always: 'Normale Wochen', matchday: 'Matchday', playoff: 'Playoff', finals: 'Finale', post: 'Nach dem Finale',
        creator: 'Creator', player: 'Spieler', team: 'G2-Team-Posts',
      },
      notes: {
        moment: '<b>Finals-Wochen: 1,44 Abschlüsse pro 1.000 Aufrufe</b>, normale Wochen: 0,55. Also rund 2,6-mal so viele. Das gilt auch, wenn man nur LoL betrachtet. Es zeigt einen Zusammenhang, noch keinen Beweis.',
        game: '<b>Vorsicht:</b> VALORANT wirkt stärker, lief aber nur in großen Matchwochen. Vergleicht man nur gleiche Matchdays, liegen alle drei Spiele gleichauf: rund 3 von 100 Klicks werden ein Abschluss.',
        source: '<b>Creator führen auch in normalen Wochen</b>: 2,8 % der Aufrufe führen zu einem Klick, bei Team-Posts 1,8 %. Aber Creator laufen fast nur auf Twitch und YouTube, das kann das Ergebnis mit erklären.',
        platform: '<b>YouTube und Twitch</b> bringen rund 8 von 10 Aufrufen und 9 von 10 Abschlüssen. Instagram, TikTok und X bringen Reichweite, aber kaum Abschlüsse.',
      },
      convShort: 'Abschl.',
      axisX: 'Klickrate', axisY: 'Abschlussrate %',
      dot: (w, what, c, v) => `Woche ${w} · ${what}: Klickrate ${c}, Abschlussrate ${v}`,
    },
    en: {
      title: 'G2 × ExpressVPN · Partnership operations',
      slide: (n, total, t) => `Slide ${n} of ${total}: ${t}`,
      goTo: (n, t) => `Go to slide ${n}: ${t}`,
      seg: {
        always: 'Normal weeks', matchday: 'Match day', playoff: 'Playoff', finals: 'Finals', post: 'After the finals',
        creator: 'Creator', player: 'Player', team: 'G2 team posts',
      },
      notes: {
        moment: '<b>Finals weeks: 1.44 sign-ups per 1,000 views</b>, normal weeks: 0.55. That is about 2.6 times as many. It also holds when you look at LoL alone. It shows a link, not yet proof.',
        game: '<b>Careful:</b> VALORANT looks stronger, but it only ran in big match weeks. Compare the same match days and all three games are level: about 3 in 100 clicks become a sign-up.',
        source: '<b>Creators lead even in normal weeks</b>: 2.8% of views lead to a click, against 1.8% for team posts. But creators run almost only on Twitch and YouTube, which may explain part of it.',
        platform: '<b>YouTube and Twitch</b> bring about 8 in 10 views and 9 in 10 sign-ups. Instagram, TikTok and X add reach, but few sign-ups.',
      },
      convShort: 'sign-ups',
      axisX: 'Click rate', axisY: 'Sign-up rate %',
      dot: (w, what, c, v) => `Week ${w} · ${what}: click rate ${c}, sign-up rate ${v}`,
    },
  };
  const translatedAttrs = [...document.querySelectorAll('*')].flatMap(el =>
    [...el.attributes].filter(a => a.name.startsWith('data-de-')).map(a => {
      const name = a.name.slice('data-de-'.length);
      return { el, name, en: el.getAttribute(name), de: a.value };
    }));
  let lang = 'en';
  const fmt = (v, digits = 0) => v.toLocaleString(lang === 'de' ? 'de-DE' : 'en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const compact = v => (v >= 1e6 ? `${fmt(v / 1e6, 1)}${lang === 'de' ? '\u00a0Mio.' : 'M'}` : v >= 1e3 ? `${fmt(v / 1e3, 0)}${lang === 'de' ? '\u00a0Tsd.' : 'K'}` : fmt(v));
  const pct = (v, digits = 1) => `${fmt(v, digits)}${lang === 'de' ? '\u00a0%' : '%'}`;

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
    document.title = STRINGS[lang].title;
    document.querySelectorAll('[data-set-lang]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.setLang === lang)));
    dotButtons.forEach((b, i) => b.setAttribute('aria-label', STRINGS[lang].goTo(i + 1, slides[i].dataset.title)));
    if (current >= 0) {
      titleEl.textContent = slides[current].dataset.title;
      announcer.textContent = STRINGS[lang].slide(current + 1, slides.length, slides[current].dataset.title);
    }
    renderCharts();
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
    touch = e.touches.length === 1 ? { x: e.touches[0].clientX, y: e.touches[0].clientY } : null;
  }, { passive: true });
  document.addEventListener('touchend', e => {
    if (!touch) return;
    const dx = e.changedTouches[0].clientX - touch.x;
    const dy = e.changedTouches[0].clientY - touch.y;
    touch = null;
    // horizontal swipes inside a scrollable table stay with the table
    if (e.target.closest('.report-wrap')) return;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) go(current + (dx < 0 ? 1 : -1));
  }, { passive: true });

  // ---------- selectors: one pressed button selects the visible detail ----------
  function selector(container, attr, onSelect) {
    const buttons = [...container.querySelectorAll(`button[data-${attr}]`)];
    const select = value => {
      container.dataset[attr] = value;
      buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset[attr] === value)));
      if (onSelect) onSelect(value);
    };
    buttons.forEach(b => b.addEventListener('click', () => select(b.dataset[attr])));
  }
  selector($('#pillars'), 'pillar');
  selector($('#eda'), 'step');
  selector($('#hyp'), 'h');
  selector($('#explorer'), 'view', () => renderExplorer());

  // ---------- charts: small inline SVGs (CSP allows SVG attributes, not inline style attributes) ----------
  const NS = 'http://www.w3.org/2000/svg';
  function el(name, attrs = {}, text) {
    const node = document.createElementNS(NS, name);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // vertical bars, one per week; `label` formats the value above each bar, `below` adds an optional second line under the week
  function barChart(host, values, { label, below, hot, target, max, height = 150 } = {}) {
    const W = 320, H = height, top = 16, bottom = below ? 32 : 18, left = 4, right = 4;
    const plotH = H - top - bottom;
    const top1 = max || Math.max(...values) * 1.08;
    const step = (W - left - right) / values.length;
    const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, 'aria-hidden': 'true' });
    svg.append(el('line', { class: 'gl', x1: left, x2: W - right, y1: top + plotH, y2: top + plotH }));
    values.forEach((v, i) => {
      const h = Math.max(1, (v / top1) * plotH);
      const x = left + i * step + step * 0.18, w = step * 0.64;
      svg.append(el('rect', { class: `bar${hot(v, i) ? ' hot' : ''}`, x, y: top + plotH - h, width: w, height: h, rx: 1 }));
      svg.append(el('text', { class: 'v', x: x + w / 2, y: top + plotH - h - 4, 'text-anchor': 'middle' }, label(v)));
      svg.append(el('text', { x: x + w / 2, y: top + plotH + 12, 'text-anchor': 'middle' }, `W${i + 1}`));
      if (below) svg.append(el('text', { class: 'rate', x: x + w / 2, y: top + plotH + 25, 'text-anchor': 'middle' }, below(i)));
    });
    if (target !== undefined) {
      const y = top + plotH - (target / top1) * plotH;
      svg.append(el('line', { class: 'tgt', x1: left, x2: W - right, y1: y, y2: y }));
      svg.append(el('text', { class: 'tgt-l', x: left, y: y - 4, 'text-anchor': 'start' }, pct(target, 0)));
    }
    host.replaceChildren(svg);
  }

  function scatter(host) {
    const W = 360, H = 250, l = 46, r = 10, t = 10, b = 30;
    const x0 = 1, x1 = 5, y0 = 2.2, y1 = 3.6;
    const sx = v => l + (v - x0) / (x1 - x0) * (W - l - r);
    const sy = v => t + (1 - (v - y0) / (y1 - y0)) * (H - t - b);
    const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, 'aria-hidden': 'true' });
    [1, 2, 3, 4, 5].forEach(v => {
      svg.append(el('line', { class: 'gl', x1: sx(v), x2: sx(v), y1: t, y2: H - b }));
      svg.append(el('text', { x: sx(v), y: H - b + 13, 'text-anchor': 'middle' }, pct(v, 0)));
    });
    [2.4, 2.8, 3.2, 3.6].forEach(v => {
      svg.append(el('line', { class: 'gl', x1: l, x2: W - r, y1: sy(v), y2: sy(v) }));
      svg.append(el('text', { x: l - 5, y: sy(v) + 3, 'text-anchor': 'end' }, fmt(v, 1)));
    });
    svg.append(el('text', { class: 'axis-t', x: (l + W - r) / 2, y: H - 3, 'text-anchor': 'middle' }, STRINGS[lang].axisX));
    svg.append(el('text', { class: 'axis-t', x: 8, y: t + (H - t - b) / 2, 'text-anchor': 'middle', transform: `rotate(-90 8 ${t + (H - t - b) / 2})` }, STRINGS[lang].axisY));
    // always-on first, so the competitive points sit on top
    [...rows].sort((a, c) => (a.moment === 'always') - (c.moment === 'always')).reverse().forEach(row => {
      const ctr = row.clicks / row.impressions * 100, cvr = row.conversions / row.clicks * 100;
      const dot = el('circle', { class: `pt ${row.moment === 'always' ? 'on' : 'comp'}`, cx: sx(ctr), cy: sy(cvr), r: 3 + Math.sqrt(row.impressions / 1e5) * 1.3 });
      dot.append(el('title', {}, STRINGS[lang].dot(row.week, `${row.game} · ${row.activation} · ${row.format}`, pct(ctr), pct(cvr))));
      svg.append(dot);
    });
    host.replaceChildren(svg);
  }

  // ---------- segment explorer ----------
  const VIEWS = {
    moment: { key: 'moment', order: ['always', 'matchday', 'playoff', 'finals', 'post'], name: k => STRINGS[lang].seg[k] },
    game: { key: 'game', order: ['VALORANT', 'LoL', 'CS2', 'R6', 'Fortnite', 'Rocket League'], name: k => k },
    source: { key: 'source', order: ['creator', 'player', 'team'], name: k => STRINGS[lang].seg[k] },
    platform: { key: 'platform', order: ['YouTube', 'Twitch', 'Instagram', 'TikTok', 'X'], name: k => k },
  };
  function renderExplorer() {
    const box = $('#explorer');
    const view = VIEWS[box.dataset.view] || VIEWS.moment;
    const segs = view.order.map(k => ({ k, ...aggregate(rows.filter(r => r[view.key] === k)) }));
    const best = Math.max(...segs.map(s => s.per1k));
    const body = $('#segBody');
    body.replaceChildren(...segs.map(s => {
      const tr = document.createElement('tr');
      if (s.per1k === best) tr.className = 'top';
      const th = document.createElement('th');
      th.scope = 'row';
      th.textContent = view.name(s.k);
      const cells = [String(s.n), compact(s.imp), pct(s.ctr), pct(s.cvr)].map(text => {
        const td = document.createElement('td');
        td.className = 'r';
        td.textContent = text;
        return td;
      });
      const barTd = document.createElement('td');
      const bar = document.createElement('span');
      bar.className = 'seg-bar';
      const i = document.createElement('i');
      i.style.setProperty('--w', `${(s.per1k / best) * 78}%`);
      const b = document.createElement('b');
      b.textContent = fmt(s.per1k, 2);
      bar.append(i, b);
      barTd.append(bar);
      tr.append(th, ...cells, barTd);
      return tr;
    }));
    $('#segNote').innerHTML = STRINGS[lang].notes[box.dataset.view]; // fixed strings from this file only
  }

  function renderCharts() {
    const maxImp = Math.max(...weeks.map(w => w.imp));
    const maxConv = Math.max(...weeks.map(w => w.conv));
    // in thousands (unit in the caption) so eight labels never collide, in either language
    barChart($('#chartImp'), weeks.map(w => w.imp), { label: v => fmt(v / 1e3), hot: v => v === maxImp, height: 180 });
    barChart($('#chartConv'), weeks.map(w => w.conv), {
      label: v => fmt(v), hot: v => v === maxConv, below: i => pct(weeks[i].cvr, 1), height: 194,
    });
    barChart($('#chartSla'), SLA_MET.map(n => n / 4 * 100), {
      label: v => pct(v, 0), hot: v => v < 80, target: 80, max: 112, height: 120,
    });
    scatter($('#chartScatter'));
    renderExplorer();
  }

  // ---------- cover: conversions per week (decorative, same data) ----------
  const coverBars = $('#coverBars');
  const maxConv = Math.max(...weeks.map(w => w.conv));
  weeks.forEach((w, i) => {
    const bar = document.createElement('span');
    bar.className = `b${w.conv === maxConv ? ' hot' : ''}`;
    bar.style.setProperty('--h', `${Math.round(w.conv / maxConv * 88)}%`);
    bar.style.setProperty('--d', `${0.15 + i * 0.07}s`);
    const wk = document.createElement('small');
    wk.textContent = `W${i + 1}`;
    bar.append(wk);
    if (w.conv === maxConv) {
      const v = document.createElement('em');
      v.textContent = String(w.conv);
      bar.append(v);
    }
    coverBars.append(bar);
  });

  // ---------- funnel: bar widths on a log scale, so 7.7M impressions and 6.8k conversions both stay visible ----------
  const funnelItems = [...document.querySelectorAll('#funnel li')];
  const top = Math.log10(+funnelItems[0].dataset.v);
  funnelItems.forEach(li => li.style.setProperty('--w', `${(Math.log10(+li.dataset.v) / top) * 100}%`));

  setLang(LANGS.includes(document.documentElement.lang) ? document.documentElement.lang : 'en', { remember: false });
  go(slideFromHash(), { updateHash: location.hash !== '' });
})();
