// Chooses the deck language before the first paint, so nobody sees the wrong language flash.
// Order: ?lang= in the URL > the visitor's own earlier choice > location > English.
// Location = the device's time zone: German for visitors in Germany, Austria, Switzerland or Liechtenstein
// (DACH), English everywhere else. It needs no network request and sends no visitor data anywhere.
(() => {
  'use strict';
  const LANGS = ['en', 'de'];
  const DACH_TIME_ZONES = ['Europe/Berlin', 'Europe/Busingen', 'Europe/Vienna', 'Europe/Zurich', 'Europe/Vaduz'];
  let lang = new URLSearchParams(location.search).get('lang');
  if (!LANGS.includes(lang)) {
    try { lang = localStorage.getItem('deck-lang'); } catch { lang = null; /* storage blocked */ }
  }
  if (!LANGS.includes(lang)) {
    let zone = '';
    try { zone = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch { /* very old browser: English */ }
    lang = DACH_TIME_ZONES.includes(zone) ? 'de' : 'en';
  }
  document.documentElement.lang = lang;
})();
